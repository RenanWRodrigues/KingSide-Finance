"""Finance — FatosDividendos repository."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import FatosDividendos
from app.repositories.base import BaseRepository


class DividendosRepository(BaseRepository[FatosDividendos]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FatosDividendos, session)

    async def get_by_empresa(
        self,
        empresa_id: UUID,
        *,
        start: date | None = None,
        end: date | None = None,
        limit: int = 100,
    ) -> list[FatosDividendos]:
        q = select(FatosDividendos).where(FatosDividendos.empresa_id == empresa_id)
        if start:
            q = q.where(FatosDividendos.data_ex >= start)
        if end:
            q = q.where(FatosDividendos.data_ex <= end)
        q = q.order_by(FatosDividendos.data_ex.desc()).limit(limit)
        result = await self._session.execute(q)
        return list(result.scalars().all())
