import asyncio
import math
from datetime import date, timedelta
from decimal import Decimal
from functools import partial
from typing import Any

import yfinance as yf
from loguru import logger

from app.core.cache import cached
from app.core.config import settings


class YFinanceService:
    """Wrapper around yfinance with caching and error handling."""

    @staticmethod
    def _resolve_ticker(ticker: str) -> str:
        """Adiciona sufixo .SA para tickers da B3 (terminam em dígito: PETR4, TAEE11)."""
        if "." not in ticker and len(ticker) <= 7 and ticker[-1].isdigit():
            return f"{ticker}.SA"
        return ticker

    @cached(ttl=300, key_prefix="yf_ticker_info")
    async def get_ticker_info(self, ticker: str) -> dict[str, Any]:
        is_b3 = "." not in ticker and len(ticker) <= 7 and ticker[-1].isdigit()

        # B3 tickers: use brapi.dev (yfinance hangs in Docker)
        if is_b3 and settings.BRAPI_TOKEN:
            try:
                import httpx
                url = f"https://brapi.dev/api/quote/{ticker}"
                params = {"token": settings.BRAPI_TOKEN, "fundamental": "true"}
                async with httpx.AsyncClient(timeout=12) as client:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                results = resp.json().get("results", [])
                if results:
                    r = results[0]
                    return {
                        "ticker": ticker,
                        "nome": r.get("longName") or r.get("shortName", ticker),
                        "setor": r.get("sector"),
                        "subsetor": r.get("industry"),
                        "moeda": r.get("currency", "BRL"),
                        "bolsa": "B3",
                        "pais": "Brasil",
                        "descricao": None,
                        "site": None,
                        "market_cap": r.get("marketCap"),
                        "price": r.get("regularMarketPrice"),
                    }
            except Exception as e:
                logger.warning(
                    f"Brapi ticker info failed for {ticker}: {e} — trying yfinance")

        # Non-B3 or brapi failed: use yfinance with hard timeout
        try:
            resolved = self._resolve_ticker(ticker)
            loop = asyncio.get_running_loop()
            info = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: yf.Ticker(resolved).info),
                timeout=12.0,
            )
            return {
                "ticker": ticker,
                "nome": info.get("longName") or info.get("shortName", ticker),
                "setor": info.get("sector"),
                "subsetor": info.get("industry"),
                "moeda": info.get("currency", "BRL"),
                "bolsa": info.get("exchange", "B3"),
                "pais": info.get("country", "Brasil"),
                "descricao": info.get("longBusinessSummary"),
                "site": info.get("website"),
                "market_cap": info.get("marketCap"),
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            }
        except Exception as e:
            logger.error(f"YFinance error for {ticker}: {e}")
            raise RuntimeError(
                f"Could not fetch data for ticker '{ticker}'") from e

    @cached(ttl=300, key_prefix="yf_history")
    async def get_price_history(
        self,
        ticker: str,
        start: date | None = None,
        end: date | None = None,
        period: str = "1y",
    ) -> list[dict[str, Any]]:
        is_b3 = "." not in ticker and len(ticker) <= 7 and ticker[-1].isdigit()

        # B3 tickers with brapi token: use brapi directly (Yahoo Finance blocks Docker)
        if is_b3 and settings.BRAPI_TOKEN and not start and not end:
            try:
                brapi = BrapiService()
                result = await brapi.get_price_history(ticker, period=period)
                if result:
                    return result
            except Exception as e:
                logger.warning(
                    f"Brapi history failed for {ticker}: {e} — trying yfinance")

        # yfinance path — with hard timeout to avoid hanging in Docker
        try:
            resolved = self._resolve_ticker(ticker)
            loop = asyncio.get_running_loop()

            def _fetch() -> Any:
                t = yf.Ticker(resolved)
                if start and end:
                    return t.history(start=str(start), end=str(end), auto_adjust=True)
                return t.history(period=period, auto_adjust=True)

            df = await asyncio.wait_for(
                loop.run_in_executor(None, _fetch),
                timeout=12.0,
            )

            if not df.empty:
                df.reset_index(inplace=True)
                df.columns = [c.lower().replace(" ", "_") for c in df.columns]
                records = []
                for _, row in df.iterrows():
                    records.append({
                        "data": row["date"].date() if hasattr(row["date"], "date") else row["date"],
                        "abertura": round(float(row.get("open", 0)), 6),
                        "maxima": round(float(row.get("high", 0)), 6),
                        "minima": round(float(row.get("low", 0)), 6),
                        "fechamento": round(float(row.get("close", 0)), 6),
                        "volume": int(row.get("volume", 0)),
                    })
                return records
        except Exception as e:
            logger.warning(f"YFinance history failed for {ticker}: {e}")

        raise RuntimeError(f"Could not fetch history for ticker '{ticker}'")

    @cached(ttl=3600, key_prefix="yf_dividends")
    async def get_dividends(self, ticker: str) -> list[dict[str, Any]]:
        try:
            resolved = self._resolve_ticker(ticker)
            loop = asyncio.get_running_loop()
            divs = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: yf.Ticker(resolved).dividends),
                timeout=15.0,
            )
            if divs.empty:
                return []

            return [
                {"data_ex": idx.date(), "valor": round(
                    float(v), 6), "tipo": "DIVIDENDO"}
                for idx, v in divs.items()
            ]
        except Exception as e:
            logger.error(f"YFinance dividends error for {ticker}: {e}")
            return []

    @cached(ttl=86400, key_prefix="yf_financials")
    async def get_financials(self, ticker: str) -> list[dict[str, Any]]:
        try:
            resolved = self._resolve_ticker(ticker)
            loop = asyncio.get_running_loop()
            income = await loop.run_in_executor(None, lambda: yf.Ticker(resolved).financials)
            if income.empty:
                return []

            records = []
            for col in income.columns:
                row = income[col]
                records.append({
                    "periodo": col.date() if hasattr(col, "date") else col,
                    "tipo_periodo": "anual",
                    "receita_liquida": self._safe_decimal(row.get("Total Revenue")),
                    "ebitda": self._safe_decimal(row.get("EBITDA")),
                    "lucro_liquido": self._safe_decimal(row.get("Net Income")),
                })
            return records
        except Exception as e:
            logger.error(f"YFinance financials error for {ticker}: {e}")
            return []

    @cached(ttl=86400, key_prefix="yf_quarterly_financials")
    async def get_quarterly_financials(self, ticker: str) -> list[dict[str, Any]]:
        try:
            resolved = self._resolve_ticker(ticker)
            loop = asyncio.get_running_loop()
            income = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: yf.Ticker(resolved).quarterly_financials),
                timeout=15.0,
            )
            if income is None or income.empty:
                return []
            records = []
            for col in income.columns:
                row = income[col]
                rev = self._safe_decimal(row.get("Total Revenue"))
                ebitda = self._safe_decimal(row.get("EBITDA"))
                net = self._safe_decimal(row.get("Net Income"))
                mg_ebitda = None
                mg_net = None
                if rev and float(rev) != 0:
                    if ebitda:
                        mg_ebitda = Decimal(str(round(float(ebitda) / float(rev) * 100, 2)))
                    if net:
                        mg_net = Decimal(str(round(float(net) / float(rev) * 100, 2)))
                records.append({
                    "periodo": col.date() if hasattr(col, "date") else col,
                    "tipo_periodo": "trimestral",
                    "receita_liquida": rev,
                    "ebitda": ebitda,
                    "lucro_liquido": net,
                    "margem_ebitda": mg_ebitda,
                    "margem_liquida": mg_net,
                })
            return records
        except Exception as e:
            logger.error(f"YFinance quarterly financials error for {ticker}: {e}")
            return []

    @cached(ttl=86400, key_prefix="yf_balance_sheet")
    async def get_balance_sheet(self, ticker: str) -> list[dict[str, Any]]:
        try:
            resolved = self._resolve_ticker(ticker)
            loop = asyncio.get_running_loop()
            bs = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: yf.Ticker(resolved).balance_sheet),
                timeout=15.0,
            )
            if bs is None or bs.empty:
                return []
            records = []
            for col in bs.columns:
                row = bs[col]
                debt = self._safe_decimal(
                    row.get("Total Debt") or row.get("Long Term Debt")
                )
                cash = self._safe_decimal(
                    row.get("Cash And Cash Equivalents")
                    or row.get("Cash Cash Equivalents And Short Term Investments")
                )
                equity = self._safe_decimal(
                    row.get("Stockholders Equity")
                    or row.get("Total Equity Gross Minority Interest")
                )
                net_debt = None
                if debt is not None and cash is not None:
                    net_debt = Decimal(str(round(float(debt) - float(cash), 2)))
                records.append({
                    "periodo": col.date() if hasattr(col, "date") else col,
                    "divida_bruta": debt,
                    "caixa": cash,
                    "divida_liquida": net_debt,
                    "patrimonio_liquido": equity,
                })
            return records
        except Exception as e:
            logger.error(f"YFinance balance sheet error for {ticker}: {e}")
            return []

    @cached(ttl=300, key_prefix="yf_valuation")
    async def get_valuation_metrics(self, ticker: str) -> dict[str, Any]:
        try:
            resolved = self._resolve_ticker(ticker)
            loop = asyncio.get_running_loop()
            info = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: yf.Ticker(resolved).info),
                timeout=15.0,
            )
            dy_raw = info.get("dividendYield") or 0
            roe_raw = info.get("returnOnEquity") or 0
            roic_raw = info.get("returnOnAssets") or 0
            payout_raw = info.get("payoutRatio") or 0
            return {
                "ticker": ticker,
                "preco": self._safe_decimal(
                    info.get("currentPrice") or info.get("regularMarketPrice")
                ),
                "pl": self._safe_decimal(
                    info.get("trailingPE") or info.get("forwardPE")
                ),
                "pvp": self._safe_decimal(info.get("priceToBook")),
                "dy": Decimal(str(round(float(dy_raw) * 100, 2))),
                "roe": Decimal(str(round(float(roe_raw) * 100, 2))),
                "roic": Decimal(str(round(float(roic_raw) * 100, 2))),
                "payout": Decimal(str(round(float(payout_raw) * 100, 2))),
                "market_cap": self._safe_decimal(info.get("marketCap")),
                "ev_ebitda": self._safe_decimal(info.get("enterpriseToEbitda")),
                "nome": info.get("longName") or info.get("shortName", ticker),
            }
        except Exception as e:
            logger.error(f"YFinance valuation error for {ticker}: {e}")
            return {"ticker": ticker}

    def _safe_decimal(self, value: Any) -> Decimal | None:
        try:
            if value is None:
                return None
            f = float(value)
            if math.isnan(f) or math.isinf(f):
                return None
            return Decimal(str(round(f, 2)))
        except Exception:
            return None


class BrapiService:
    """brapi.dev — Brazilian stock market API (fallback para yfinance)."""

    BASE_URL = "https://brapi.dev/api"

    _PERIOD_MAP: dict[str, str] = {
        "1d": "1d", "5d": "5d", "1mo": "1mo", "3mo": "3mo",
        "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y", "max": "max",
    }

    @cached(ttl=300, key_prefix="brapi_history")
    async def get_price_history(self, ticker: str, period: str = "1y") -> list[dict[str, Any]]:
        import httpx
        from datetime import datetime as _dt

        brapi_range = self._PERIOD_MAP.get(period, "1y")
        url = f"{self.BASE_URL}/quote/{ticker}"
        params = {"range": brapi_range, "interval": "1d",
                  "token": settings.BRAPI_TOKEN}

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()

        results = resp.json().get("results", [])
        if not results:
            return []

        records = []
        for item in results[0].get("historicalDataPrice", []):
            try:
                dt = _dt.fromtimestamp(item["date"]).date()
                close = float(item.get("close")
                              or item.get("adjustedClose") or 0)
                if close <= 0:
                    continue
                records.append({
                    "data": dt,
                    "abertura": round(float(item.get("open") or close), 6),
                    "maxima": round(float(item.get("high") or close), 6),
                    "minima": round(float(item.get("low") or close), 6),
                    "fechamento": round(close, 6),
                    "volume": int(item.get("volume") or 0),
                })
            except Exception:
                continue

        return sorted(records, key=lambda x: x["data"])


class BCBService:
    """Banco Central do Brasil SGS API."""

    BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"

    SERIES = {
        "selic": 432,      # Taxa SELIC % a.a. (série 432) — antes era série 11 (% a.d.)
        "ipca": 13522,     # IPCA acumulado 12 meses % (série 13522) — série 4466 é variação mensal
        "igpm": 189,
        "cambio_dolar": 1,
        "pib_mensal": 4380,
        "desemprego": 24369,
    }

    @cached(ttl=3600, key_prefix="bcb_series")
    async def get_series(
        self,
        indicador: str,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> list[dict[str, Any]]:
        import httpx

        code = self.SERIES.get(indicador)
        if not code:
            raise ValueError(
                f"Indicador '{indicador}' not found. Available: {list(self.SERIES)}")

        # BCB rejects `ultimos` for daily series; always use explicit date range
        from datetime import date as _date, timedelta

        params: dict[str, Any] = {"formato": "json"}
        if not data_inicio:
            data_inicio = _date.today() - timedelta(days=365)
        if not data_fim:
            data_fim = _date.today()
        params["dataInicial"] = data_inicio.strftime("%d/%m/%Y")
        params["dataFinal"] = data_fim.strftime("%d/%m/%Y")

        url = self.BASE_URL.format(code=code)
        headers = {"Accept": "application/json", "User-Agent": "Finance/1.0"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        return [
            {
                "indicador": indicador,
                "data": self._parse_date(item["data"]),
                "valor": Decimal(str(item["valor"])),
                "fonte": "BCB/SGS",
            }
            for item in data
            if item.get("valor") not in (None, "", " ")
        ]

    def _parse_date(self, date_str: str) -> date:
        from datetime import datetime

        return datetime.strptime(date_str, "%d/%m/%Y").date()


class FREDService:
    """Federal Reserve Economic Data API."""

    def __init__(self) -> None:
        if not settings.FRED_API_KEY:
            logger.warning("FRED_API_KEY not configured")

    @cached(ttl=3600, key_prefix="fred_series")
    async def get_series(self, series_id: str, limit: int = 100) -> list[dict[str, Any]]:
        try:
            from fredapi import Fred

            fred = Fred(api_key=settings.FRED_API_KEY)
            data = fred.get_series(series_id)
            records = []
            for idx, value in data.tail(limit).items():
                if value is not None:
                    records.append({
                        "indicador": series_id,
                        "data": idx.date(),
                        "valor": Decimal(str(round(float(value), 8))),
                        "fonte": "FRED",
                    })
            return records
        except Exception as e:
            logger.error(f"FRED error for {series_id}: {e}")
            raise RuntimeError(
                f"Could not fetch FRED series '{series_id}'") from e
