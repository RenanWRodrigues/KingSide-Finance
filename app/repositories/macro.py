"""Finance — FatosMacro repository."""
from __future__ import annotations

from datetime import date

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import FatosMacro
from app.repositories.base import BaseRepository


class MacroRepository(BaseRepository[FatosMacro]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FatosMacro, session)

    async def get_indicator_history(
        self,
        indicador: str,
        *,
        start: date | None = None,
        end: date | None = None,
        limit: int = 120,
    ) -> list[FatosMacro]:
        q = select(FatosMacro).where(FatosMacro.indicador == indicador)
        if start:
            q = q.where(FatosMacro.data >= start)
        if end:
            q = q.where(FatosMacro.data <= end)
        q = q.order_by(desc(FatosMacro.data)).limit(limit)
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def get_latest(self, indicador: str) -> FatosMacro | None:
        result = await self._session.execute(
            select(FatosMacro)
            .where(FatosMacro.indicador == indicador)
            .order_by(desc(FatosMacro.data))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def upsert_batch(self, records: list[dict]) -> int:
        """Bulk upsert macro indicators, keyed by (indicador, data)."""
        if not records:
            return 0
        stmt = pg_insert(FatosMacro).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_fatos_macro_indicador_data",
            set_={"valor": stmt.excluded.valor},
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return len(records)
