from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.schemas.financial import SentimentResponse


router = APIRouter(prefix="/sentiment", tags=["sentiment"])


@router.get("/{ticker}", response_model=SentimentResponse, summary="Sentiment analysis for ticker")
async def get_sentiment(ticker: str) -> SentimentResponse:
    ticker = ticker.upper()
    try:
        from ml.sentiment_analysis.analyzer import analyze_ticker_sentiment

        result = await analyze_ticker_sentiment(ticker)
        return SentimentResponse(
            ticker=ticker,
            score=result["score"],
            label=result["label"],
            confianca=result["confianca"],
            total_noticias=result["total_noticias"],
            data_analise=datetime.now(timezone.utc),
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sentiment analysis module not available. Install ML dependencies.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sentiment analysis failed: {e}",
        )
