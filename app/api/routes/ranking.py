from __future__ import annotations

import asyncio
from decimal import Decimal

import httpx
from fastapi import APIRouter, Query

from app.core.cache import cache_get, cache_set
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.financial import RankingItem, RankingResponse, SectorPerformanceItem, SectorResponse

router = APIRouter(prefix="/ranking", tags=["ranking"])
logger = get_logger(__name__)

_B3_UNIVERSE: list[tuple[str, str, str]] = [
    # Petróleo e Gás
    ("PETR4", "Petrobras", "Petróleo e Gás"),
    ("PRIO3", "PetroRio", "Petróleo e Gás"),
    ("CSAN3", "Cosan", "Petróleo e Gás"),
    # Mineração
    ("VALE3", "Vale", "Mineração"),
    # Papel e Celulose
    ("SUZB3", "Suzano", "Papel e Celulose"),
    ("KLBN11", "Klabin", "Papel e Celulose"),
    # Bancos
    ("ITUB4", "Itaú Unibanco", "Bancos"),
    ("BBDC4", "Bradesco", "Bancos"),
    ("BBAS3", "Banco do Brasil", "Bancos"),
    ("SANB11", "Santander Brasil", "Bancos"),
    # Bens Industriais
    ("WEGE3", "WEG", "Bens Industriais"),
    ("EMBR3", "Embraer", "Bens Industriais"),
    # Bebidas e Alimentos
    ("ABEV3", "Ambev", "Bebidas"),
    ("JBSS3", "JBS", "Alimentos"),
    # Seguros
    ("BBSE3", "BB Seguridade", "Seguros"),
    # Energia Elétrica
    ("TAEE11", "Taesa", "Energia Elétrica"),
    ("EGIE3", "Engie Brasil", "Energia Elétrica"),
    ("ELET3", "Eletrobras", "Energia Elétrica"),
    ("CMIG4", "CEMIG", "Energia Elétrica"),
    # Varejo
    ("MGLU3", "Magazine Luiza", "Varejo"),
    ("LREN3", "Lojas Renner", "Varejo"),
    ("ASAI3", "Assaí Atacadista", "Varejo Alimentar"),
    # Tecnologia
    ("TOTS3", "Totvs", "Tecnologia"),
    # Construção Civil
    ("CYRE3", "Cyrela", "Construção Civil"),
    # Logística e Locação
    ("RAIL3", "Rumo", "Logística"),
    ("RENT3", "Localiza", "Locação de Veículos"),
    # Saneamento
    ("SBSP3", "Sabesp", "Saneamento"),
    # Saúde
    ("RADL3", "RaiaDrogasil", "Saúde"),
    ("HAPV3", "Hapvida", "Saúde"),
    # Telecomunicações
    ("VIVT3", "Telefônica Brasil", "Telecomunicações"),
]

_TICKER_META: dict[str, tuple[str, str]] = {t: (n, s) for t, n, s in _B3_UNIVERSE}
_UNIVERSE_CACHE_KEY = "ranking:universe_quotes"
_UNIVERSE_TTL = 3600


async def _brapi_quote(ticker: str) -> tuple[str, dict]:
    """Simple quote (no history) — works on brapi free plan."""
    try:
        url = f"https://brapi.dev/api/quote/{ticker}"
        params = {"token": settings.BRAPI_TOKEN}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
        results = resp.json().get("results", [])
        return ticker, (results[0] if results else {})
    except Exception as e:
        logger.warning(f"Brapi quote failed for {ticker}: {e}")
        return ticker, {}


async def _get_universe_quotes() -> dict[str, dict]:
    """Fetch simple quotes for all 30 tickers; cached 1h in Redis."""
    cached = await cache_get(_UNIVERSE_CACHE_KEY)
    if cached:
        return cached

    quotes: dict[str, dict] = {}
    for ticker, _, _ in _B3_UNIVERSE:
        t, data = await _brapi_quote(ticker)
        quotes[t] = data
        await asyncio.sleep(0.3)

    non_empty = sum(1 for v in quotes.values() if v)
    if non_empty >= len(_B3_UNIVERSE) // 2:
        await cache_set(_UNIVERSE_CACHE_KEY, quotes, _UNIVERSE_TTL)

    return quotes


def _parse_52w_return(info: dict) -> float | None:
    """Return from 52-week low as momentum proxy: (price - 52w_low) / 52w_low."""
    try:
        price = float(info.get("regularMarketPrice") or 0)
        range_str = str(info.get("fiftyTwoWeekRange") or "")
        parts = [p.strip() for p in range_str.replace(",", ".").split("-")]
        if len(parts) >= 2 and price > 0:
            low = float(parts[0])
            if low > 0:
                return round((price - low) / low * 100, 2)
    except (ValueError, TypeError, IndexError):
        pass
    return None


def _parse_52w_volatility(info: dict) -> float | None:
    """52w range / 52w_low as a simple volatility proxy."""
    try:
        range_str = str(info.get("fiftyTwoWeekRange") or "")
        parts = [p.strip() for p in range_str.replace(",", ".").split("-")]
        if len(parts) >= 2:
            low = float(parts[0])
            high = float(parts[1])
            if low > 0:
                return round((high - low) / low * 100, 2)
    except (ValueError, TypeError, IndexError):
        pass
    return None


@router.get("/dividend", response_model=RankingResponse, summary="Top stocks by Dividend Yield / daily change")
async def ranking_dividend(
    limite: int = Query(default=10, ge=1, le=50),
    setor: str | None = None,
) -> RankingResponse:
    quotes = await _get_universe_quotes()

    rows: list[tuple[str, str, str, float]] = []
    for ticker, (nome, setor_val) in _TICKER_META.items():
        if setor and setor_val != setor:
            continue
        info = quotes.get(ticker, {})
        dy = info.get("dividendYield")
        if dy is not None:
            try:
                rows.append((ticker, nome, setor_val, round(float(dy), 2)))
                continue
            except (TypeError, ValueError):
                pass
        chg = info.get("regularMarketChangePercent")
        if chg is not None:
            try:
                rows.append((ticker, nome, setor_val, round(float(chg), 2)))
            except (TypeError, ValueError):
                pass

    rows.sort(key=lambda x: x[3], reverse=True)
    items = [
        RankingItem(ticker=t, nome=n, setor=s, valor=Decimal(str(v)), posicao=i + 1)
        for i, (t, n, s, v) in enumerate(rows[:limite])
    ]
    return RankingResponse(tipo="variacao_diaria_pct", periodo="1d", total=len(items), items=items)


@router.get("/growth", response_model=RankingResponse, summary="Top stocks by Market Cap")
async def ranking_growth(
    limite: int = Query(default=10, ge=1, le=50),
    setor: str | None = None,
) -> RankingResponse:
    quotes = await _get_universe_quotes()

    rows: list[tuple[str, str, str, float]] = []
    for ticker, (nome, setor_val) in _TICKER_META.items():
        if setor and setor_val != setor:
            continue
        info = quotes.get(ticker, {})
        cap = info.get("marketCap")
        if cap is not None:
            try:
                rows.append((ticker, nome, setor_val, round(float(cap) / 1e9, 2)))
            except (TypeError, ValueError):
                pass

    rows.sort(key=lambda x: x[3], reverse=True)
    items = [
        RankingItem(ticker=t, nome=n, setor=s, valor=Decimal(str(v)), posicao=i + 1)
        for i, (t, n, s, v) in enumerate(rows[:limite])
    ]
    return RankingResponse(tipo="market_cap_bilhoes", periodo="atual", total=len(items), items=items)


@router.get("/momentum", response_model=RankingResponse, summary="Top 52-week momentum stocks")
async def ranking_momentum(
    periodo: str = Query(default="52w", description="52w"),
    limite: int = Query(default=10, ge=1, le=50),
) -> RankingResponse:
    quotes = await _get_universe_quotes()

    rows: list[tuple[str, str, str, float]] = []
    for ticker, (nome, setor_val) in _TICKER_META.items():
        pct = _parse_52w_return(quotes.get(ticker, {}))
        if pct is not None:
            rows.append((ticker, nome, setor_val, pct))

    rows.sort(key=lambda x: x[3], reverse=True)
    items = [
        RankingItem(ticker=t, nome=n, setor=s, valor=Decimal(str(v)), posicao=i + 1)
        for i, (t, n, s, v) in enumerate(rows[:limite])
    ]
    return RankingResponse(tipo="retorno_52_semanas_pct", periodo="52w", total=len(items), items=items)


@router.get("/volatility", response_model=RankingResponse, summary="Ranking by 52-week price range volatility proxy")
async def ranking_volatility(
    limite: int = Query(default=10, ge=1, le=50),
    ordem: str = Query(default="asc", description="asc (menor vol) | desc (maior vol)"),
) -> RankingResponse:
    quotes = await _get_universe_quotes()

    rows: list[tuple[str, str, str, float]] = []
    for ticker, (nome, setor_val) in _TICKER_META.items():
        vol = _parse_52w_volatility(quotes.get(ticker, {}))
        if vol is not None:
            rows.append((ticker, nome, setor_val, vol))

    rows.sort(key=lambda x: x[3], reverse=(ordem == "desc"))
    items = [
        RankingItem(ticker=t, nome=n, setor=s, valor=Decimal(str(v)), posicao=i + 1)
        for i, (t, n, s, v) in enumerate(rows[:limite])
    ]
    return RankingResponse(tipo="volatilidade_52w_proxy_pct", periodo="52w", total=len(items), items=items)


@router.get("/sectors", response_model=SectorResponse, summary="Sector performance ranking")
async def ranking_sectors() -> SectorResponse:
    quotes = await _get_universe_quotes()

    sector_data: dict[str, dict] = {}
    for ticker, (nome, setor_val) in _TICKER_META.items():
        info = quotes.get(ticker, {})
        chg = info.get("regularMarketChangePercent")
        vol = _parse_52w_volatility(info)

        if setor_val not in sector_data:
            sector_data[setor_val] = {"tickers": [], "changes": [], "vols": []}

        sector_data[setor_val]["tickers"].append(ticker)
        if chg is not None:
            try:
                sector_data[setor_val]["changes"].append(float(chg))
            except (TypeError, ValueError):
                pass
        if vol is not None:
            sector_data[setor_val]["vols"].append(vol)

    sector_rows: list[tuple[str, list[str], float | None, float | None]] = []
    for setor_val, d in sector_data.items():
        avg_chg = round(sum(d["changes"]) / len(d["changes"]), 2) if d["changes"] else None
        avg_vol = round(sum(d["vols"]) / len(d["vols"]), 2) if d["vols"] else None
        sector_rows.append((setor_val, d["tickers"], avg_chg, avg_vol))

    sector_rows.sort(key=lambda x: (x[2] is None, -(x[2] or 0)))

    items = [
        SectorPerformanceItem(
            setor=s,
            tickers=t,
            retorno_medio_pct=chg,
            volatilidade_proxy=vol,
            total_ativos=len(t),
            posicao=i + 1,
        )
        for i, (s, t, chg, vol) in enumerate(sector_rows)
    ]
    return SectorResponse(tipo="setor_performance_diaria", total=len(items), items=items)
