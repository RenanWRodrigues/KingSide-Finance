"""
Finance — Daily Financial Data Ingestion Pipeline

Schedule: 18:30 BRT (21:30 UTC) on business days
Sources: yfinance, BCB SGS, FRED
Target: PostgreSQL raw schema
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup


DEFAULT_ARGS = {
    "owner": "finance-data-eng",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
}

TICKERS_B3 = [
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA",
    "WEGE3.SA", "RENT3.SA", "MGLU3.SA", "LREN3.SA", "SUZB3.SA",
    "JBSS3.SA", "BEEF3.SA", "GGBR4.SA", "USIM5.SA", "CSNA3.SA",
]

# BCB SGS series IDs
_BCB_SERIES = {
    "selic":  11,   # Taxa Selic
    "ipca":   433,  # IPCA (variação mensal)
    "cdi":    12,   # CDI diário
}

# FRED series for USD/BRL
_FRED_SERIES = {
    "usd_brl": "DEXBZUS",
}


def ingest_prices_task(ticker: str, **context) -> None:
    import os
    import yfinance as yf
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL_SYNC"])
    t = yf.Ticker(ticker)
    df = t.history(period="5d", auto_adjust=True)

    if df.empty:
        return

    with conn.cursor() as cur:
        for ts, row in df.iterrows():
            cur.execute(
                """
                INSERT INTO raw.cotacoes_raw
                    (ticker, date, open, high, low, close, adj_close, volume, loaded_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (ticker, date) DO UPDATE SET
                    open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                    close=EXCLUDED.close, adj_close=EXCLUDED.adj_close,
                    volume=EXCLUDED.volume, loaded_at=NOW()
                """,
                (
                    ticker.replace(".SA", ""),
                    ts.date(),
                    float(row.get("Open", 0)),
                    float(row.get("High", 0)),
                    float(row.get("Low", 0)),
                    float(row.get("Close", 0)),
                    float(row.get("Close", 0)),
                    int(row.get("Volume", 0)),
                ),
            )
    conn.commit()
    conn.close()


def _upsert_macro(conn, indicador: str, data_ref, valor: float, fonte: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO raw.macro_raw (indicador, data, valor, fonte, loaded_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (indicador, data) DO UPDATE SET
                valor=EXCLUDED.valor, loaded_at=NOW()
            """,
            (indicador, data_ref, valor, fonte),
        )


def ingest_bcb_series(indicador: str, serie_id: int, **context) -> None:
    import os
    from datetime import datetime as dt
    import requests
    import psycopg2

    url = (
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie_id}"
        "/dados?formato=json&ultimos=10"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    conn = psycopg2.connect(os.environ["DATABASE_URL_SYNC"])
    for item in resp.json():
        data_ref = dt.strptime(item["data"], "%d/%m/%Y").date()
        _upsert_macro(conn, indicador, data_ref, float(item["valor"]), "BCB/SGS")
    conn.commit()
    conn.close()


def ingest_fred_usd_brl(**context) -> None:
    import os
    import requests
    import psycopg2

    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        raise EnvironmentError("FRED_API_KEY not set — skipping USD/BRL ingestion")

    url = (
        "https://api.stlouisfed.org/fred/series/observations"
        f"?series_id=DEXBZUS&api_key={api_key}&file_type=json"
        "&sort_order=desc&limit=10"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    observations = resp.json().get("observations", [])

    conn = psycopg2.connect(os.environ["DATABASE_URL_SYNC"])
    for obs in observations:
        if obs["value"] == ".":
            continue
        from datetime import date
        data_ref = date.fromisoformat(obs["date"])
        _upsert_macro(conn, "usd_brl", data_ref, float(obs["value"]), "FRED")
    conn.commit()
    conn.close()


def invalidate_ticker_cache(ticker: str, **context) -> None:
    """Remove stale Redis entries for *ticker* after a successful price ingest.

    Uses synchronous redis-py (Airflow tasks are synchronous) and mirrors the
    prefix list from app/core/cache.py so the API serves fresh data immediately.
    """
    import os
    import redis as redis_lib

    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    r = redis_lib.from_url(url, decode_responses=True)

    prefixes = (
        "yf_ticker_info", "yf_history", "yf_dividends", "yf_financials",
        "yf_quarterly_financials", "yf_balance_sheet", "yf_valuation", "brapi_history",
    )
    count = 0
    clean_ticker = ticker.replace(".SA", "")
    for prefix in prefixes:
        for key in r.scan_iter(match=f"{prefix}:{clean_ticker}:*", count=100):
            r.delete(key)
            count += 1

    print(f"[{clean_ticker}] Cache invalidated: {count} keys removed")


def run_dbt_transformations(**context) -> None:
    import subprocess
    result = subprocess.run(
        ["dbt", "run", "--project-dir", "/opt/airflow/dbt", "--profiles-dir", "/opt/airflow/dbt"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"dbt run failed:\n{result.stderr}")


def run_dbt_tests(**context) -> None:
    import subprocess
    result = subprocess.run(
        ["dbt", "test", "--project-dir", "/opt/airflow/dbt", "--profiles-dir", "/opt/airflow/dbt"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"dbt test failed:\n{result.stderr}")


with DAG(
    dag_id="finance_daily_ingestion",
    description="Daily financial data ingestion and ELT pipeline",
    default_args=DEFAULT_ARGS,
    schedule_interval="30 21 * * 1-5",  # 18:30 BRT on business days
    catchup=False,
    max_active_runs=1,
    tags=["finance", "ingestion", "daily", "elt"],
    doc_md=__doc__,
) as dag:

    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    with TaskGroup("ingest_prices") as ingest_prices_group:
        price_tasks = [
            PythonOperator(
                task_id=f"ingest_{ticker.replace('.', '_').replace('-', '_')}",
                python_callable=ingest_prices_task,
                op_kwargs={"ticker": ticker},
            )
            for ticker in TICKERS_B3
        ]

    with TaskGroup("invalidate_cache") as invalidate_cache_group:
        cache_tasks = [
            PythonOperator(
                task_id=f"cache_{ticker.replace('.', '_').replace('-', '_')}",
                python_callable=invalidate_ticker_cache,
                op_kwargs={"ticker": ticker},
                trigger_rule="all_done",  # run even if ingest had partial failures
            )
            for ticker in TICKERS_B3
        ]

    with TaskGroup("ingest_macro") as ingest_macro_group:
        macro_tasks = [
            PythonOperator(
                task_id=f"ingest_{indicador}",
                python_callable=ingest_bcb_series,
                op_kwargs={"indicador": indicador, "serie_id": serie_id},
            )
            for indicador, serie_id in _BCB_SERIES.items()
        ]
        t_usd_brl = PythonOperator(
            task_id="ingest_usd_brl",
            python_callable=ingest_fred_usd_brl,
        )

    with TaskGroup("dbt_pipeline") as dbt_group:
        t_dbt_run = PythonOperator(
            task_id="dbt_run",
            python_callable=run_dbt_transformations,
        )
        t_dbt_test = PythonOperator(
            task_id="dbt_test",
            python_callable=run_dbt_tests,
        )
        t_dbt_run >> t_dbt_test

    start >> [ingest_prices_group, ingest_macro_group]
    ingest_prices_group >> invalidate_cache_group >> dbt_group
    ingest_macro_group >> dbt_group
    dbt_group >> end
