"""Direct data providers — used when FastAPI backend is unavailable.

Sources:
  - Stock OHLCV   : yfinance (B3 tickers with .SA suffix)
  - SELIC         : FRED series IRSTCI01BRM156N (Brazil interbank rate)
  - IPCA 12m      : IBGE API (agregado 1737, variável 2265)
  - USD/BRL       : yfinance BRL=X (monthly mean)
  - IGP-M         : BCB SGS série 189 (FGV/IGP-M, variação mensal %)
  - Rankings      : yfinance 1-year returns
  - Compare       : yfinance OHLCV + computed risk metrics
  - Forecast      : linear trend fit on last 6 months
"""
from __future__ import annotations

import logging
import math
import threading
import time as _time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, TypeVar

import pandas as pd
import requests
import yfinance as yf

# Limit concurrent yfinance calls to avoid Yahoo Finance rate limiting.
# Sequential or near-sequential calls work; many simultaneous calls trigger 429.
_YF_SEMAPHORE = threading.Semaphore(2)

_YF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# Import ticker universe from the single source of truth in config.
# Both _SECTOR and _RANK_TICKERS were previously defined inline here,
# creating a divergence risk whenever config.py was updated.
from config import SECTORS as _SECTOR, RANK_TICKERS as _RANK_TICKERS

_logger = logging.getLogger(__name__)

_F = TypeVar("_F", bound=Callable[..., Any])


# ─────────────────────────────────────────────────────────────────────────────
# Simple TTL cache — only stores non-None results so transient failures
# (rate-limits, network blips) never get frozen for 15 minutes.
# Thread-safe for CPython (GIL makes dict writes atomic).
# ─────────────────────────────────────────────────────────────────────────────

def _ttl_cache(ttl: int = 900) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        _store: dict[tuple, tuple[float, Any]] = {}

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = args + tuple(sorted(kwargs.items()))
            entry = _store.get(key)
            if entry is not None and _time.time() - entry[0] < ttl:
                return entry[1]
            result = func(*args, **kwargs)
            if result:  # don't cache None or empty containers ({}, [])
                _store[key] = (_time.time(), result)
            return result

        return wrapper  # type: ignore[return-value]
    return decorator


def _sa(ticker: str) -> str:
    return ticker if ticker.endswith(".SA") else ticker + ".SA"


def _f(val: Any) -> float | None:
    try:
        v = float(val)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def _yf_history(ticker_sa: str, period: str, retries: int = 3) -> pd.DataFrame:
    """Fetch yfinance history with semaphore + retry to handle rate-limits."""
    for attempt in range(retries):
        try:
            with _YF_SEMAPHORE:
                df = yf.Ticker(ticker_sa).history(period=period, auto_adjust=True)
            if not df.empty:
                return df
        except Exception as exc:
            _logger.debug("yfinance attempt %d/%d failed for %s: %s", attempt + 1, retries, ticker_sa, exc)
        if attempt < retries - 1:
            _time.sleep(0.8 * (attempt + 1))
    _logger.warning("yfinance returned no data for %s (period=%s) after %d attempts", ticker_sa, period, retries)
    return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# Stock history
# ─────────────────────────────────────────────────────────────────────────────

@_ttl_cache(ttl=900)
def stock_history(ticker: str, period: str = "1y") -> dict | None:
    df = _yf_history(_sa(ticker), period)
    if df.empty:
        return None
    df = df.reset_index()
    cotacoes = []
    for _, row in df.iterrows():
        dt = row["Date"]
        date_str = str(dt.date()) if hasattr(dt, "date") else str(dt)[:10]
        cotacoes.append({
            "data": date_str,
            "fechamento": _f(row.get("Close")),
            "abertura": _f(row.get("Open")),
            "maxima": _f(row.get("High")),
            "minima": _f(row.get("Low")),
            "volume": int(row.get("Volume") or 0),
        })
    return {"ticker": ticker, "cotacoes": cotacoes}


# ─────────────────────────────────────────────────────────────────────────────
# Macro indicators
# ─────────────────────────────────────────────────────────────────────────────

@_ttl_cache(ttl=14400)
def macro_indicator(indicator: str) -> list | None:
    if indicator == "selic":
        return _selic()
    if indicator == "ipca":
        return _ipca()
    if indicator == "cambio_dolar":
        return _cambio()
    if indicator == "igpm":
        return _igpm()
    return None


def _selic() -> list | None:
    """SELIC annual rate (% a.a.) from BCB SGS series 432."""
    from datetime import date, timedelta
    try:
        end = date.today()
        start = end - timedelta(days=730)
        url = (
            "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados"
            f"?formato=json&dataInicial={start.strftime('%d/%m/%Y')}"
            f"&dataFinal={end.strftime('%d/%m/%Y')}"
        )
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list) or not data:
            return None
        result = []
        seen_months: set[str] = set()
        for rec in data:
            raw_date = rec.get("data", "")
            val = rec.get("valor")
            if not raw_date or val in (None, ""):
                continue
            parts = raw_date.split("/")
            if len(parts) == 3:
                iso = f"{parts[2]}-{parts[1]}-{parts[0]}"
                month_key = iso[:7]
                if month_key not in seen_months:
                    seen_months.add(month_key)
                    try:
                        result.append({"data": iso, "valor": float(val)})
                    except (ValueError, TypeError):
                        pass
        return result[-24:] if result else None
    except Exception as exc:
        _logger.warning("SELIC (BCB) fetch failed: %s", exc)
        return None


def _ipca() -> list | None:
    """IPCA accumulated 12 months from IBGE (agregado 1737, variável 2265)."""
    try:
        url = (
            "https://servicodados.ibge.gov.br/api/v3/agregados/1737"
            "/periodos/last%2060/variaveis/2265?localidades=N1[all]"
        )
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        serie = r.json()[0]["resultados"][0]["series"][0]["serie"]
        result = []
        for period, valor in sorted(serie.items()):
            if valor not in (".", ""):
                year, month = period[:4], period[4:]
                result.append({
                    "data": f"{year}-{month}-01",
                    "valor": float(valor),
                })
        return result or None
    except Exception as exc:
        _logger.warning("IPCA (IBGE) fetch failed: %s", exc)
        return None


def _bcb_ptax_hoje() -> dict | None:
    """Latest USD/BRL PTAX closing rate from BCB (official rate, ~5 min delay).

    Walks back up to 5 calendar days to skip weekends / holidays.
    Returns {"data": "YYYY-MM-DD", "valor": mid-rate} or None.
    """
    from datetime import date, timedelta
    for i in range(5):
        d = date.today() - timedelta(days=i)
        date_str = d.strftime("%m-%d-%Y")
        try:
            url = (
                "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
                f"CotacaoDolarDia(dataCotacao=@dataCotacao)"
                f"?@dataCotacao='{date_str}'&$format=json"
                "&$select=cotacaoCompra,cotacaoVenda,dataHoraCotacao"
            )
            r = requests.get(url, timeout=8)
            if r.status_code != 200:
                continue
            values = r.json().get("value", [])
            if values:
                latest = values[-1]
                compra = float(latest["cotacaoCompra"])
                venda  = float(latest["cotacaoVenda"])
                return {
                    "data":  d.strftime("%Y-%m-%d"),
                    "valor": round((compra + venda) / 2, 4),
                }
        except Exception as exc:
            _logger.debug("BCB PTAX fetch failed for %s: %s", date_str, exc)
            continue
    _logger.warning("BCB PTAX: no data found in last 5 business days")
    return None


@_ttl_cache(ttl=300)
def macro_cambio() -> list | None:
    """USD/BRL series: BCB PTAX for the current rate, yfinance monthly mean for history."""
    try:
        df = yf.Ticker("BRL=X").history(period="10y", auto_adjust=True)
        if df.empty:
            return None

        closes = df["Close"].dropna()

        if closes.index.tz is not None:
            closes.index = closes.index.tz_localize(None)

        today       = pd.Timestamp.today().normalize()
        month_start = today.replace(day=1)

        past    = closes[closes.index < month_start]
        monthly = past.resample("ME").mean().dropna()
        result  = [
            {"data": dt.strftime("%Y-%m-%d"), "valor": round(float(val), 4)}
            for dt, val in monthly.items()
        ]

        ptax = _bcb_ptax_hoje()
        if ptax:
            result.append(ptax)
        else:
            cur = closes[closes.index >= month_start]
            if not cur.empty:
                result.append({
                    "data":  cur.index[-1].strftime("%Y-%m-%d"),
                    "valor": round(float(cur.iloc[-1]), 4),
                })

        return result[-120:] if result else None
    except Exception as exc:
        _logger.warning("USD/BRL (macro_cambio) fetch failed: %s", exc)
        return None


def _cambio() -> list | None:
    """Kept for backward-compat; delegates to macro_cambio()."""
    return macro_cambio()


def _igpm() -> list | None:
    """IGP-M mensal via BCB (série 189 — FGV/IGP-M variação mensal %)."""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.189/dados?formato=json&ultimos=120"
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        result = []
        for item in r.json():
            try:
                dt = pd.to_datetime(item["data"], dayfirst=True).strftime("%Y-%m-%d")
                result.append({"data": dt, "valor": float(item["valor"])})
            except (KeyError, ValueError):
                continue
        return result or None
    except Exception as exc:
        _logger.warning("IGP-M (BCB série 189) fetch failed: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Financials & fundamentals
# ─────────────────────────────────────────────────────────────────────────────

@_ttl_cache(ttl=3600)
def stock_financials(ticker: str, period: str = "annual") -> list | None:
    try:
        t = yf.Ticker(_sa(ticker))
        income = t.financials if period == "annual" else t.quarterly_financials
        if income is None or income.empty:
            return None
        records = []
        for col in income.columns:
            row = income[col]
            rev = _f(row.get("Total Revenue"))
            ebitda = _f(row.get("EBITDA"))
            net = _f(row.get("Net Income"))
            records.append({
                "periodo": str(col.date()) if hasattr(col, "date") else str(col)[:10],
                "tipo_periodo": period,
                "receita_liquida": rev,
                "ebitda": ebitda,
                "lucro_liquido": net,
                "margem_ebitda": round(ebitda / rev * 100, 2) if (rev and rev != 0 and ebitda is not None) else None,
                "margem_liquida": round(net / rev * 100, 2) if (rev and rev != 0 and net is not None) else None,
            })
        return records
    except Exception as exc:
        _logger.warning("stock_financials failed for %s (period=%s): %s", ticker, period, exc)
        return None


@_ttl_cache(ttl=3600)
def stock_balance_sheet(ticker: str) -> list | None:
    try:
        bs = yf.Ticker(_sa(ticker)).balance_sheet
        if bs is None or bs.empty:
            return None
        def _first(row, *keys):
            for k in keys:
                v = row.get(k)
                if v is not None:
                    return v
            return None

        records = []
        for col in bs.columns:
            row = bs[col]
            debt   = _f(_first(row, "Total Debt", "Long Term Debt"))
            cash   = _f(_first(row, "Cash And Cash Equivalents",
                                "Cash Cash Equivalents And Short Term Investments"))
            equity = _f(_first(row, "Stockholders Equity",
                                "Total Equity Gross Minority Interest"))
            net_debt = round(debt - cash, 2) if debt is not None and cash is not None else None
            records.append({
                "periodo": str(col.date()) if hasattr(col, "date") else str(col)[:10],
                "divida_bruta": debt,
                "caixa": cash,
                "divida_liquida": net_debt,
                "patrimonio_liquido": equity,
            })
        return records
    except Exception as exc:
        _logger.warning("stock_balance_sheet failed for %s: %s", ticker, exc)
        return None


@_ttl_cache(ttl=3600)
def stock_dividends(ticker: str) -> list | None:
    try:
        divs = yf.Ticker(_sa(ticker)).dividends
        if divs is None or divs.empty:
            return None
        return [
            {
                "data_ex": str(idx.date()) if hasattr(idx, "date") else str(idx)[:10],
                "valor": round(float(v), 6),
                "tipo": "DIVIDENDO",
            }
            for idx, v in divs.items()
        ]
    except Exception as exc:
        _logger.warning("stock_dividends failed for %s: %s", ticker, exc)
        return None


@_ttl_cache(ttl=300)
def stock_valuation(ticker: str) -> dict | None:
    try:
        info = yf.Ticker(_sa(ticker)).info
        if not info:
            return None
        dy_raw     = info.get("dividendYield") or 0
        roe_raw    = info.get("returnOnEquity") or 0
        roic_raw   = info.get("returnOnAssets") or 0
        payout_raw = info.get("payoutRatio") or 0
        # yfinance >= 0.2.x retorna dividendYield já como % (ex: 9.15 = 9.15%).
        # ROE, ROA e payout continuam como fração (ex: 0.256 = 25.6%) — * 100 necessário.
        return {
            "ticker": ticker,
            "preco": _f(info.get("currentPrice") or info.get("regularMarketPrice")),
            "pl": _f(info.get("trailingPE") or info.get("forwardPE")),
            "pvp": _f(info.get("priceToBook")),
            "dy":     round(float(dy_raw), 2)         if dy_raw     else None,
            "roe":    round(float(roe_raw)    * 100, 2) if roe_raw    else None,
            "roic":   round(float(roic_raw)   * 100, 2) if roic_raw   else None,
            "payout": round(float(payout_raw) * 100, 2) if payout_raw else None,
            "market_cap": _f(info.get("marketCap")),
            "ev_ebitda": _f(info.get("enterpriseToEbitda")),
            "nome": info.get("longName") or info.get("shortName", ticker),
        }
    except Exception as exc:
        _logger.warning("stock_valuation failed for %s: %s", ticker, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Compare assets
# ─────────────────────────────────────────────────────────────────────────────

@_ttl_cache(ttl=900)
def compare_assets(tickers: tuple[str, ...], period: str = "1y") -> dict | None:
    try:
        hists = _fetch_history_parallel(list(tickers), period)

        if not hists:
            return None

        metrics, perf_series = [], []
        rf_daily = (1 + 0.1475) ** (1 / 252) - 1  # SELIC ~14,75% a.a.

        for t, cl in hists.items():
            if len(cl) < 5:
                continue
            rets = cl.pct_change().dropna()
            first, last = float(cl.iloc[0]), float(cl.iloc[-1])
            n = len(cl)
            ret_acc = (last / first - 1) * 100
            cagr = ((last / first) ** (252 / n) - 1) * 100 if n > 5 else 0
            vol = rets.std() * math.sqrt(252) * 100
            sharpe = (
                float((rets.mean() - rf_daily) / rets.std() * math.sqrt(252))
                if rets.std() > 0 else 0
            )
            neg_r = rets[rets < 0]
            sortino = (
                float((rets.mean() - rf_daily) / neg_r.std() * math.sqrt(252))
                if len(neg_r) > 0 and neg_r.std() > 0 else 0
            )
            roll_max = cl.cummax()
            max_dd = float(((cl - roll_max) / roll_max * 100).min())
            var95 = float(rets.quantile(0.05) * 100) if len(rets) >= 20 else 0
            ma20 = _f(cl.rolling(20).mean().iloc[-1]) if n >= 20 else None
            ma50 = _f(cl.rolling(50).mean().iloc[-1]) if n >= 50 else None
            ma200 = _f(cl.rolling(200).mean().iloc[-1]) if n >= 200 else None
            delta = cl.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, float("nan"))
            rsi14 = _f((100 - 100 / (1 + rs)).iloc[-1]) if n >= 15 else None

            metrics.append({
                "ticker": t, "setor": _SECTOR.get(t, ""),
                "preco_atual": round(last, 2),
                "retorno_acumulado": round(ret_acc, 2),
                "cagr": round(cagr, 2),
                "volatilidade_anual": round(vol, 2),
                "sharpe": round(sharpe, 3),
                "sortino": round(sortino, 3),
                "max_drawdown": round(max_dd, 2),
                "beta": 1.0,
                "var_95": round(var95, 3),
                "rsi_14": round(rsi14, 2) if rsi14 else None,
                "ma_20": round(ma20, 2) if ma20 else None,
                "ma_50": round(ma50, 2) if ma50 else None,
                "ma_200": round(ma200, 2) if ma200 else None,
            })

            norm = (cl / cl.iloc[0] * 100).reset_index()
            norm.columns = ["data", "normalizado"]
            norm["data"] = norm["data"].apply(
                lambda d: d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
            )
            perf_series.append({"ticker": t, "pontos": norm.to_dict("records")})

        if not metrics:
            return None

        all_rets = pd.DataFrame(
            {t: hists[t].pct_change().dropna() for t in hists}
        ).dropna()
        corr = all_rets.corr()
        corr_dict = {
            t: {t2: round(float(corr.loc[t, t2]), 4) for t2 in hists if t2 in corr.columns}
            for t in hists if t in corr.index
        }

        return {"metrics": metrics, "correlacao": corr_dict, "performance": perf_series}
    except Exception as exc:
        _logger.warning("compare_assets failed for %s: %s", tickers, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Rankings
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_history_parallel(tickers: list[str], period: str, workers: int = 10) -> dict[str, pd.Series]:
    """Fetch yfinance history for multiple tickers concurrently."""
    from concurrent.futures import ThreadPoolExecutor, as_completed as _as_completed

    def _one(t: str) -> tuple[str, pd.Series]:
        df = _yf_history(_sa(t), period)
        return t, df["Close"].dropna() if not df.empty else pd.Series(dtype=float)

    result: dict[str, pd.Series] = {}
    with ThreadPoolExecutor(max_workers=min(workers, len(tickers))) as pool:
        futures = {pool.submit(_one, t): t for t in tickers}
        try:
            for future in _as_completed(futures, timeout=60):
                try:
                    t, series = future.result()
                    if not series.empty:
                        result[t] = series
                except Exception:
                    pass
        except TimeoutError:
            for future in futures:
                if future.done():
                    try:
                        t, series = future.result()
                        if not series.empty:
                            result[t] = series
                    except Exception:
                        pass
    return result


@_ttl_cache(ttl=3600)
def ranking(kind: str, limit: int = 15) -> dict | None:
    try:
        hists = _fetch_history_parallel(_RANK_TICKERS, "1y")

        if not hists:
            return None

        rows = []
        for t, cl in hists.items():
            if len(cl) < 5:
                continue
            ret_1y = (float(cl.iloc[-1]) / float(cl.iloc[0]) - 1) * 100
            n63 = max(0, len(cl) - 63)
            ret_3m = (float(cl.iloc[-1]) / float(cl.iloc[n63]) - 1) * 100
            rets = cl.pct_change().dropna()
            vol = rets.std() * math.sqrt(252) * 100

            if kind == "dividend":
                valor = max(0.0, ret_1y * 0.4 - vol * 0.08)
            elif kind == "growth":
                valor = ret_1y
            else:
                valor = ret_3m

            rows.append({
                "ticker": t, "nome": t,
                "setor": _SECTOR.get(t, ""),
                "valor": round(valor, 2),
            })

        if not rows:
            return None

        rows.sort(key=lambda x: x["valor"], reverse=True)
        rows = rows[:limit]
        for i, r in enumerate(rows):
            r["posicao"] = i + 1

        return {"items": rows}
    except Exception as exc:
        _logger.warning("ranking failed (kind=%s): %s", kind, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Real-time market quote
# ─────────────────────────────────────────────────────────────────────────────

@_ttl_cache(ttl=300)
def market_quote(symbol: str) -> dict | None:
    """Fetch latest market quote.

    Primary: direct Yahoo Finance v8 API with semaphore guard and retry.
    Fallback: yfinance with semaphore guard.
    TTL=300 so transient failures don't keep hammering Yahoo Finance.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"

    # ── 1. Direct HTTP API — semaphore-guarded, 3 retries with backoff ────────
    for attempt in range(3):
        try:
            with _YF_SEMAPHORE:
                r = requests.get(url, headers=_YF_HEADERS, timeout=10)
            if r.status_code == 429:
                _logger.debug("market_quote 429 for %s (attempt %d)", symbol, attempt + 1)
                _time.sleep(1.5 * (attempt + 1))
                continue
            r.raise_for_status()
            data = r.json()
            result = data.get("chart", {}).get("result") or []
            if result:
                raw_closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
                closes = [c for c in raw_closes if c is not None]
                if closes:
                    last = float(closes[-1])
                    prev = float(closes[-2]) if len(closes) >= 2 else last
                    chg = last - prev
                    return {"symbol": symbol, "last": last, "prev": prev,
                            "chg": chg, "chg_pct": (chg / prev * 100) if prev else 0.0}
            err = data.get("chart", {}).get("error")
            _logger.debug("market_quote direct empty result for %s: %s", symbol, err)
            break
        except Exception as exc:
            _logger.debug("market_quote direct attempt %d failed for %s: %s", attempt + 1, symbol, exc)
            if attempt < 2:
                _time.sleep(0.8 * (attempt + 1))

    # ── 2. yfinance fallback ──────────────────────────────────────────────────
    for period in ("5d", "1mo"):
        try:
            with _YF_SEMAPHORE:
                df = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True)
            if df.empty:
                continue
            closes_s = df["Close"].dropna()
            if closes_s.empty:
                continue
            last = float(closes_s.iloc[-1])
            prev = float(closes_s.iloc[-2]) if len(closes_s) >= 2 else last
            chg = last - prev
            return {"symbol": symbol, "last": last, "prev": prev,
                    "chg": chg, "chg_pct": (chg / prev * 100) if prev else 0.0}
        except Exception as exc:
            _logger.debug("market_quote yfinance (%s, %s): %s", symbol, period, exc)

    _logger.warning("market_quote: no data for %s", symbol)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Batch stock history (rate-limit-safe bulk fetch for scoring pages)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_close(raw: "pd.DataFrame", sa_ticker: str) -> "pd.Series":
    """Extract Close series for one ticker from a yf.download() result.

    Handles all three column layouts produced by different yfinance versions:
      - Flat columns (single ticker)
      - MultiIndex (ticker, OHLCV)  — group_by='ticker'
      - MultiIndex (OHLCV, ticker)  — group_by='column' / default
    """
    if not isinstance(raw.columns, pd.MultiIndex):
        return raw.get("Close", pd.Series(dtype=float)).dropna()  # type: ignore[return-value]

    lvl0 = raw.columns.get_level_values(0)
    lvl1 = raw.columns.get_level_values(1)

    if sa_ticker in lvl0:                        # (ticker, OHLCV) layout
        sub = raw[sa_ticker]
        return sub.get("Close", pd.Series(dtype=float)).dropna()  # type: ignore[return-value]

    if "Close" in lvl0 and sa_ticker in lvl1:    # (OHLCV, ticker) layout
        return raw["Close"].get(sa_ticker, pd.Series(dtype=float)).dropna()  # type: ignore[return-value]

    return pd.Series(dtype=float)


@_ttl_cache(ttl=900)
def batch_stock_history(tickers: tuple[str, ...], period: str = "1y") -> dict[str, list]:
    """Fetch OHLCV history for many tickers via a single yf.download() request.

    yf.download() batches all tickers into one HTTP call, avoiding the per-ticker
    rate-limit pressure that kills individual _yf_history() calls at scale.
    Falls back to individual stock_history() for any tickers missing from the batch.
    """
    sa_map = {_sa(t): t for t in tickers}
    sa_list = list(sa_map.keys())
    result: dict[str, list] = {}

    # ── 1. Batch download ─────────────────────────────────────────────────────
    try:
        with _YF_SEMAPHORE:
            raw = yf.download(
                sa_list,
                period=period,
                auto_adjust=True,
                progress=False,
                group_by="ticker",
            )

        if not raw.empty:
            for sa_ticker, ticker in sa_map.items():
                try:
                    closes = _extract_close(raw, sa_ticker)
                    cotacoes = [
                        {
                            "data": (idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]),
                            "fechamento": float(v),
                            "volume": 0,
                        }
                        for idx, v in closes.items()
                        if not (isinstance(v, float) and math.isnan(v))
                    ]
                    if len(cotacoes) >= 20:
                        result[ticker] = cotacoes
                except Exception as exc:
                    _logger.debug("batch extract failed for %s: %s", sa_ticker, exc)

    except Exception as exc:
        _logger.warning("yf.download batch failed (%d tickers, period=%s): %s", len(sa_list), period, exc)

    # ── 2. Individual fallback for tickers not in batch result ────────────────
    missing = [t for t in tickers if t not in result]
    if missing:
        _logger.debug("Individual fallback for %d tickers: %s", len(missing), missing[:8])
        for ticker in missing:
            hist = stock_history(ticker, period)
            if hist and len(hist.get("cotacoes") or []) >= 20:
                result[ticker] = hist["cotacoes"]

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Forecast (linear trend fallback)
# ─────────────────────────────────────────────────────────────────────────────

@_ttl_cache(ttl=900)
def forecast_linear(ticker: str, horizon: int = 30) -> list | None:
    try:
        import numpy as np

        df = _yf_history(_sa(ticker), "6mo")
        cl = df["Close"].dropna() if not df.empty else pd.Series(dtype=float)
        if len(cl) < 20:
            return None

        x = np.arange(len(cl), dtype=float)
        y = cl.values.astype(float)
        coeffs = np.polyfit(x, y, 1)
        slope, intercept = float(coeffs[0]), float(coeffs[1])
        std_err = float(pd.Series(y - np.polyval(coeffs, x)).std())

        last_date = cl.index[-1]
        n = len(cl)
        result = []
        offset = 0
        for i in range(1, horizon + 1):
            pred = max(slope * (n + i - 1) + intercept, 0.01)
            while True:
                candidate = pd.Timestamp(last_date) + pd.Timedelta(days=i + offset)
                if candidate.weekday() < 5:
                    break
                offset += 1
            result.append({
                "data_forecast": candidate.strftime("%Y-%m-%d"),
                "preco_previsto": round(pred, 2),
                "lower_bound": round(max(pred - 1.96 * std_err, 0.01), 2),
                "upper_bound": round(pred + 1.96 * std_err, 2),
            })
        return result
    except Exception as exc:
        _logger.warning("forecast_linear failed for %s (horizon=%d): %s", ticker, horizon, exc)
        return None
