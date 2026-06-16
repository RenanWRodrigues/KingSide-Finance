"""Finance — FatosCotacoes repository."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import FatosCotacoes
from app.repositories.base import BaseRepository


class CotacoesRepository(BaseRepository[FatosCotacoes]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FatosCotacoes, session)

    async def get_history(
        self,
        empresa_id: UUID,
        *,
        start: date | None = None,
        end: date | None = None,
        limit: int = 500,
    ) -> list[FatosCotacoes]:
        q = select(FatosCotacoes).where(FatosCotacoes.empresa_id == empresa_id)
        if start:
            q = q.where(FatosCotacoes.data >= start)
        if end:
            q = q.where(FatosCotacoes.data <= end)
        q = q.order_by(FatosCotacoes.data.asc()).limit(limit)
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def get_latest(self, empresa_id: UUID) -> FatosCotacoes | None:
        result = await self._session.execute(
            select(FatosCotacoes)
            .where(FatosCotacoes.empresa_id == empresa_id)
            .order_by(desc(FatosCotacoes.data))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def upsert_batch(self, records: list[dict]) -> int:
        """Bulk upsert via PostgreSQL ON CONFLICT DO UPDATE."""
        if not records:
            return 0
        stmt = pg_insert(FatosCotacoes).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_fatos_cotacoes_empresa_data",
            set_={
                "abertura": stmt.excluded.abertura,
                "maxima": stmt.excluded.maxima,
                "minima": stmt.excluded.minima,
                "fechamento": stmt.excluded.fechamento,
                "fechamento_ajustado": stmt.excluded.fechamento_ajustado,
                "volume": stmt.excluded.volume,
                "variacao_dia_pct": stmt.excluded.variacao_dia_pct,
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return len(records)
