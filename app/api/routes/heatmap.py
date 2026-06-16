"""Market Heatmap — sector performance endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.cache import cached
from app.core.logging import get_logger
from app.services.financial_data import YFinanceService

logger = get_logger(__name__)
router = APIRouter(prefix="/market", tags=["market-heatmap"])


class AssetHeatmapItem(BaseModel):
    ticker: str
    setor: str | None = None
    change_pct: float | None = None
    preco: float | None = None
    market_cap_rel: float | None = None


class SectorPerformance(BaseModel):
    setor: str
    change_pct_avg: float
    tickers: list[str]
    best_ticker: str | None = None
    worst_ticker: str | None = None


class HeatmapResponse(BaseModel):
    period: str
    assets: list[AssetHeatmapItem]
    sectors: list[SectorPerformance]


_HEATMAP_TICKERS = [
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "SANB11.SA",
    "WEGE3.SA", "EMBR3.SA", "ABEV3.SA", "JBSS3.SA", "BBSE3.SA", "TAEE11.SA",
    "EGIE3.SA", "ELET3.SA", "CMIG4.SA", "PRIO3.SA", "SUZB3.SA", "MGLU3.SA",
    "LREN3.SA", "TOTS3.SA", "CYRE3.SA", "RAIL3.SA", "RENT3.SA", "RADL3.SA", "VIVT3.SA",
]

_SECTOR_MAP = {
    "PETR4": "Petróleo e Gás", "PRIO3": "Petróleo e Gás",
    "VALE3": "Mineração",
    "ITUB4": "Bancos", "BBDC4": "Bancos", "BBAS3": "Bancos", "SANB11": "Bancos",
    "WEGE3": "Bens Industriais", "EMBR3": "Bens Industriais",
    "ABEV3": "Bebidas",
    "JBSS3": "Alimentos",
    "BBSE3": "Seguros",
    "TAEE11": "Energia Elétrica", "EGIE3": "Energia Elétrica",
    "ELET3": "Energia Elétrica", "CMIG4": "Energia Elétrica",
    "SUZB3": "Papel e Celulose",
    "MGLU3": "Varejo", "LREN3": "Varejo",
    "TOTS3": "Tecnologia",
    "CYRE3": "Construção Civil",
    "RAIL3": "Logística",
    "RENT3": "Locação de Veículos",
    "RADL3": "Saúde",
    "VIVT3": "Telecomunicações",
}

_MARKET_CAP_WEIGHTS = {
    "PETR4": 420, "VALE3": 350, "ITUB4": 280, "BBDC4": 120, "BBAS3": 160,
    "WEGE3": 180, "ABEV3": 130, "RENT3": 85, "EMBR3": 60, "RAIL3": 70,
    "TOTS3": 45, "RADL3": 55, "BBSE3": 70, "EGIE3": 40, "TAEE11": 30,
    "ELET3": 90, "CMIG4": 25, "SUZB3": 80, "PRIO3": 65, "SANB11": 75,
    "MGLU3": 20, "LREN3": 30, "JBSS3": 50, "CYRE3": 15, "VIVT3": 55,
}


@router.get("/heatmap", response_model=HeatmapResponse, summary="B3 Market Heatmap")
@cached(ttl=900)
async def get_market_heatmap(
    period: Annotated[str, Query(description="5d, 1mo, 3mo, 6mo, 1y")] = "5d",
) -> HeatmapResponse:
    svc = YFinanceService()
    assets: list[AssetHeatmapItem] = []
    sector_data: dict[str, list[float]] = {}
    sector_tickers: dict[str, list[str]] = {}

    for yf_ticker in _HEATMAP_TICKERS:
        ticker = yf_ticker.replace(".SA", "")
        setor = _SECTOR_MAP.get(ticker)
        try:
            df = await svc.get_price_history(yf_ticker, period=period)
            if df and len(df) >= 2:
                last_p = float(df[-1]["fechamento"])
                first_p = float(df[0]["fechamento"])
                change = (last_p / first_p - 1) * 100 if first_p else 0.0
            else:
                last_p = 0.0
                change = 0.0
        except Exception:
            last_p = 0.0
            change = 0.0

        assets.append(AssetHeatmapItem(
            ticker=ticker,
            setor=setor,
            change_pct=round(change, 2),
            preco=round(last_p, 2),
            market_cap_rel=float(_MARKET_CAP_WEIGHTS.get(ticker, 30)),
        ))

        if setor:
            sector_data.setdefault(setor, []).append(change)
            sector_tickers.setdefault(setor, []).append(ticker)

    sectors: list[SectorPerformance] = []
    for setor, changes in sector_data.items():
        avg = sum(changes) / len(changes)
        tickers = sector_tickers[setor]
        matched = [(a.change_pct or 0, a.ticker) for a in assets if a.setor == setor]
        best = max(matched, key=lambda x: x[0])[1] if matched else None
        worst = min(matched, key=lambda x: x[0])[1] if matched else None
        sectors.append(SectorPerformance(
            setor=setor,
            change_pct_avg=round(avg, 2),
            tickers=tickers,
            best_ticker=best,
            worst_ticker=worst,
        ))

    sectors.sort(key=lambda x: x.change_pct_avg, reverse=True)
    return HeatmapResponse(period=period, assets=assets, sectors=sectors)


@router.get("/sector-performance", response_model=list[SectorPerformance], summary="Sector Performance")
@cached(ttl=900)
async def get_sector_performance(
    period: Annotated[str, Query()] = "1mo",
) -> list[SectorPerformance]:
    response = await get_market_heatmap(period=period)
    return response.sectors
