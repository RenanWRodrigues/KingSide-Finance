"""Finance — FatosForecasts repository."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import FatosForecasts
from app.repositories.base import BaseRepository


class ForecastsRepository(BaseRepository[FatosForecasts]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FatosForecasts, session)

    async def get_latest_for_empresa(
        self,
        empresa_id: UUID,
        *,
        modelo: str | None = None,
        limit: int = 90,
    ) -> list[FatosForecasts]:
        q = (
            select(FatosForecasts)
            .where(FatosForecasts.empresa_id == empresa_id)
            .order_by(
                desc(FatosForecasts.data_geracao),
                FatosForecasts.data_forecast.asc(),
            )
        )
        if modelo:
            q = q.where(FatosForecasts.modelo == modelo)
        result = await self._session.execute(q.limit(limit))
        return list(result.scalars().all())
