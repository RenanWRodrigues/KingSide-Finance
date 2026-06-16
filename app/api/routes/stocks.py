from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.financial import (
    CotacaoHistoricoResponse,
    EmpresaResponse,
    ForecastRequest,
    ForecastResponse,
    PaginatedResponse,
    RankingResponse,
    SentimentResponse,
)
from app.services.financial_data import YFinanceService


router = APIRouter(prefix="/stocks", tags=["stocks"])
yf_service = YFinanceService()


@router.get("", response_model=PaginatedResponse, summary="List all tracked stocks")
async def list_stocks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    setor: str | None = Query(default=None, description="Filter by sector"),
    ativo: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    from sqlalchemy import func, select

    from app.models.financial import DimEmpresa

    query = select(DimEmpresa).where(DimEmpresa.ativo == ativo)
    if setor:
        query = query.where(DimEmpresa.setor == setor)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    empresas = result.scalars().all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        data=[EmpresaResponse.model_validate(e) for e in empresas],
    )


@router.get("/{ticker}", response_model=EmpresaResponse, summary="Get stock by ticker")
async def get_stock(ticker: str, db: AsyncSession = Depends(get_db)) -> EmpresaResponse:
    from sqlalchemy import select

    from app.models.financial import DimEmpresa

    ticker = ticker.upper()
    result = await db.execute(select(DimEmpresa).where(DimEmpresa.ticker == ticker))
    empresa = result.scalar_one_or_none()

    if not empresa:
        try:
            info = await yf_service.get_ticker_info(ticker)
            return EmpresaResponse(
                id=UUID(int=0),
                ticker=ticker,
                nome=info["nome"],
                setor=info.get("setor"),
                subsetor=info.get("subsetor"),
                bolsa=info.get("bolsa", "B3"),
                pais=info.get("pais", "Brasil"),
                moeda=info.get("moeda", "BRL"),
                ativo=True,
                created_at=datetime.now(timezone.utc),
            )
        except RuntimeError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticker '{ticker}' not found",
            )

    return EmpresaResponse.model_validate(empresa)


@router.get(
    "/{ticker}/history",
    response_model=CotacaoHistoricoResponse,
    summary="Get price history for a stock",
)
async def get_stock_history(
    ticker: str,
    start: date | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end: date | None = Query(default=None, description="End date (YYYY-MM-DD)"),
    period: str = Query(default="1y", description="Period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y"),
) -> CotacaoHistoricoResponse:
    ticker = ticker.upper()
    try:
        cotacoes_raw = await yf_service.get_price_history(ticker, start=start, end=end, period=period)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if not cotacoes_raw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price data found for ticker '{ticker}'",
        )

    dates = [r["data"] for r in cotacoes_raw]
    return CotacaoHistoricoResponse(
        ticker=ticker,
        periodo_inicio=min(dates),
        periodo_fim=max(dates),
        total_registros=len(cotacoes_raw),
        cotacoes=cotacoes_raw,  # type: ignore[arg-type]
    )


@router.get("/{ticker}/financials", summary="Get income statement (annual or quarterly)")
async def get_financials(
    ticker: str,
    period: str = Query(default="annual", description="annual or quarterly"),
) -> list[dict]:
    ticker = ticker.upper()
    try:
        if period == "quarterly":
            records = await yf_service.get_quarterly_financials(ticker)
        else:
            records = await yf_service.get_financials(ticker)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return [
        {
            "periodo": str(r["periodo"]),
            "tipo_periodo": r["tipo_periodo"],
            "receita_liquida": float(r["receita_liquida"]) if r.get("receita_liquida") else None,
            "ebitda": float(r["ebitda"]) if r.get("ebitda") else None,
            "lucro_liquido": float(r["lucro_liquido"]) if r.get("lucro_liquido") else None,
            "margem_ebitda": float(r["margem_ebitda"]) if r.get("margem_ebitda") else None,
            "margem_liquida": float(r["margem_liquida"]) if r.get("margem_liquida") else None,
        }
        for r in records
    ]


@router.get("/{ticker}/dividends", summary="Get dividend history")
async def get_dividends_history(ticker: str) -> list[dict]:
    ticker = ticker.upper()
    records = await yf_service.get_dividends(ticker)
    return [
        {
            "data_ex": str(r["data_ex"]),
            "valor": float(r["valor"]),
            "tipo": r["tipo"],
        }
        for r in records
    ]


@router.get("/{ticker}/balance-sheet", summary="Get balance sheet history")
async def get_balance_sheet(ticker: str) -> list[dict]:
    ticker = ticker.upper()
    records = await yf_service.get_balance_sheet(ticker)
    return [
        {
            "periodo": str(r["periodo"]),
            "divida_bruta": float(r["divida_bruta"]) if r.get("divida_bruta") else None,
            "caixa": float(r["caixa"]) if r.get("caixa") else None,
            "divida_liquida": float(r["divida_liquida"]) if r.get("divida_liquida") else None,
            "patrimonio_liquido": float(r["patrimonio_liquido"]) if r.get("patrimonio_liquido") else None,
        }
        for r in records
    ]


@router.get("/{ticker}/valuation", summary="Get valuation multiples")
async def get_valuation(ticker: str) -> dict:
    ticker = ticker.upper()
    data = await yf_service.get_valuation_metrics(ticker)
    return {
        k: float(v) if hasattr(v, "__float__") and v is not None else v
        for k, v in data.items()
    }
