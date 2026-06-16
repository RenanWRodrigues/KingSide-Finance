"""Finance — DimEmpresa repository."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import DimEmpresa
from app.repositories.base import BaseRepository


class EmpresaRepository(BaseRepository[DimEmpresa]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DimEmpresa, session)

    async def get_by_ticker(self, ticker: str) -> DimEmpresa | None:
        result = await self._session.execute(
            select(DimEmpresa).where(DimEmpresa.ticker == ticker.upper())
        )
        return result.scalar_one_or_none()

    async def list_active(
        self,
        *,
        setor: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DimEmpresa]:
        q = select(DimEmpresa).where(DimEmpresa.ativo == True)  # noqa: E712
        if setor:
            q = q.where(DimEmpresa.setor == setor)
        result = await self._session.execute(q.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count_active(self) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(DimEmpresa)
            .where(DimEmpresa.ativo == True)  # noqa: E712
        )
        return result.scalar_one()

    async def upsert(
        self,
        ticker: str,
        nome: str,
        bolsa: str = "B3",
        **kwargs: object,
    ) -> DimEmpresa:
        """Insert or update a company record by ticker."""
        existing = await self.get_by_ticker(ticker)
        if existing:
            existing.nome = nome
            for key, val in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, val)
            await self._session.flush()
            return existing
        empresa = DimEmpresa(ticker=ticker.upper(), nome=nome, bolsa=bolsa, **kwargs)
        return await self.save(empresa)
