from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.schemas.financial import ForecastRequest, ForecastResponse


router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/{ticker}", response_model=list[ForecastResponse], summary="Get price forecast")
async def get_forecast(
    ticker: str,
    horizonte_dias: int = 30,
    modelo: str = "prophet",
) -> list[ForecastResponse]:
    from app.ml_bridge import run_forecast

    ticker = ticker.upper()
    try:
        forecasts = await run_forecast(ticker=ticker, horizonte_dias=horizonte_dias, modelo=modelo)
        return forecasts
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecast generation failed: {e}",
        )


@router.post("/generate", response_model=dict, summary="Trigger async forecast generation")
async def generate_forecast(
    request: ForecastRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    from app.ml_bridge import run_forecast_async

    background_tasks.add_task(
        run_forecast_async,
        ticker=request.ticker.upper(),
        horizonte_dias=request.horizonte_dias,
        modelo=request.modelo,
    )

    return {
        "message": f"Forecast generation started for {request.ticker.upper()}",
        "ticker": request.ticker.upper(),
        "horizonte_dias": request.horizonte_dias,
        "modelo": request.modelo,
        "status": "queued",
    }
