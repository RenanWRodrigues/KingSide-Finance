"""Finance — FatosFinancials repository."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import FatosFinancials
from app.repositories.base import BaseRepository


class FinancialsRepository(BaseRepository[FatosFinancials]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FatosFinancials, session)

    async def get_by_empresa(
        self,
        empresa_id: UUID,
        tipo_periodo: str = "annual",
        *,
        limit: int = 20,
    ) -> list[FatosFinancials]:
        result = await self._session.execute(
            select(FatosFinancials)
            .where(
                and_(
                    FatosFinancials.empresa_id == empresa_id,
                    FatosFinancials.tipo_periodo == tipo_periodo,
                )
            )
            .order_by(FatosFinancials.periodo.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def upsert_batch(self, records: list[dict]) -> int:
        """Bulk upsert financials, keyed by (empresa_id, periodo, tipo_periodo)."""
        if not records:
            return 0
        stmt = pg_insert(FatosFinancials).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_fatos_financials",
            set_={
                "receita_liquida": stmt.excluded.receita_liquida,
                "ebitda": stmt.excluded.ebitda,
                "ebit": stmt.excluded.ebit,
                "lucro_liquido": stmt.excluded.lucro_liquido,
                "divida_liquida": stmt.excluded.divida_liquida,
                "patrimonio_liquido": stmt.excluded.patrimonio_liquido,
                "ativo_total": stmt.excluded.ativo_total,
                "caixa": stmt.excluded.caixa,
                "margem_bruta": stmt.excluded.margem_bruta,
                "margem_ebitda": stmt.excluded.margem_ebitda,
                "margem_liquida": stmt.excluded.margem_liquida,
                "roe": stmt.excluded.roe,
                "roa": stmt.excluded.roa,
                "roic": stmt.excluded.roic,
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return len(records)
