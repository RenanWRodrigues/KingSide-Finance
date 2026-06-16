from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.financial import MacroIndicadorResponse
from app.services.financial_data import BCBService, FREDService


router = APIRouter(prefix="/macro", tags=["macro"])
bcb_service = BCBService()
fred_service = FREDService()

BCB_INDICATORS = ["selic", "ipca", "igpm", "cambio_dolar", "pib_mensal", "desemprego"]
FRED_SERIES = ["DFF", "UNRATE", "CPIAUCSL", "GDP", "SP500", "T10Y2Y"]


@router.get("", summary="List available macro indicators")
async def list_macro_indicators() -> dict:
    return {
        "brasil": {
            "source": "Banco Central do Brasil (SGS)",
            "indicators": BCB_INDICATORS,
        },
        "eua": {
            "source": "Federal Reserve Economic Data (FRED)",
            "indicators": FRED_SERIES,
        },
    }


@router.get("/brasil/{indicador}", response_model=list[MacroIndicadorResponse])
async def get_bcb_series(
    indicador: str,
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
) -> list[MacroIndicadorResponse]:
    if indicador not in BCB_INDICATORS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid indicator. Available: {BCB_INDICATORS}",
        )
    try:
        data = await bcb_service.get_series(indicador, data_inicio, data_fim)
        return [MacroIndicadorResponse(**d) for d in data]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/fred/{series_id}", response_model=list[MacroIndicadorResponse])
async def get_fred_series(
    series_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[MacroIndicadorResponse]:
    series_id = series_id.upper()
    try:
        data = await fred_service.get_series(series_id, limit=limit)
        return [MacroIndicadorResponse(**d) for d in data]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
