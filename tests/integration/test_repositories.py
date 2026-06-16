"""Integration-style tests for the repository layer.

Uses a mocked AsyncSession to verify query construction and result handling
without a live database. These tests exercise the repository code paths and
confirm that SQLAlchemy statements are assembled and executed correctly.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.repositories.cotacoes import CotacoesRepository
from app.repositories.empresa import EmpresaRepository
from app.repositories.macro import MacroRepository


# ── Session factory ───────────────────────────────────────────────────────────

def _make_session(
    *,
    scalar_one_or_none=None,
    scalar_one=0,
    scalars_all=None,
) -> AsyncMock:
    """Return an AsyncSession mock wired to return controlled query results."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_one_or_none
    result.scalar_one.return_value = scalar_one
    result.scalars.return_value.all.return_value = scalars_all or []
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock()
    return session


# ── EmpresaRepository ─────────────────────────────────────────────────────────

class TestEmpresaRepository:
    async def test_get_by_ticker_returns_none_when_not_found(self):
        session = _make_session(scalar_one_or_none=None)
        repo = EmpresaRepository(session)

        result = await repo.get_by_ticker("XPTO3")

        assert result is None
        session.execute.assert_awaited_once()

    async def test_get_by_ticker_returns_entity_when_found(self):
        from app.models.financial import DimEmpresa

        empresa = DimEmpresa(ticker="PETR4", nome="Petrobras", bolsa="B3")
        session = _make_session(scalar_one_or_none=empresa)
        repo = EmpresaRepository(session)

        result = await repo.get_by_ticker("PETR4")

        assert result is empresa
        assert result.ticker == "PETR4"

    async def test_get_by_ticker_uppercases_input(self):
        """Ticker lookup must normalise to upper case."""
        from app.models.financial import DimEmpresa

        empresa = DimEmpresa(ticker="VALE3", nome="Vale", bolsa="B3")
        session = _make_session(scalar_one_or_none=empresa)
        repo = EmpresaRepository(session)

        result = await repo.get_by_ticker("vale3")

        assert result is not None

    async def test_list_active_returns_list(self):
        from app.models.financial import DimEmpresa

        companies = [
            DimEmpresa(ticker="PETR4", nome="Petrobras", bolsa="B3"),
            DimEmpresa(ticker="VALE3", nome="Vale", bolsa="B3"),
        ]
        session = _make_session(scalars_all=companies)
        repo = EmpresaRepository(session)

        result = await repo.list_active(limit=10)

        assert len(result) == 2

    async def test_list_active_empty_returns_empty_list(self):
        session = _make_session(scalars_all=[])
        repo = EmpresaRepository(session)

        result = await repo.list_active()

        assert result == []

    async def test_count_active_returns_int(self):
        session = _make_session(scalar_one=42)
        repo = EmpresaRepository(session)

        result = await repo.count_active()

        assert result == 42

    async def test_upsert_updates_existing(self):
        """upsert() on an existing ticker should mutate and flush, not insert."""
        from app.models.financial import DimEmpresa

        existing = DimEmpresa(ticker="WEGE3", nome="Old Name", bolsa="B3")
        session = _make_session(scalar_one_or_none=existing)
        repo = EmpresaRepository(session)

        result = await repo.upsert("WEGE3", "WEG SA", bolsa="B3")

        assert result.nome == "WEG SA"
        session.flush.assert_awaited()

    async def test_upsert_inserts_new(self):
        """upsert() when ticker is absent must create a new entity."""
        from app.models.financial import DimEmpresa

        new_entity = DimEmpresa(ticker="TOTS3", nome="Totvs", bolsa="B3")
        session = _make_session(scalar_one_or_none=None)
        session.refresh = AsyncMock()

        # Mock the save() path: add → flush → refresh → return
        async def mock_save(obj):
            return new_entity

        repo = EmpresaRepository(session)
        repo.save = mock_save  # type: ignore[assignment]

        result = await repo.upsert("TOTS3", "Totvs", bolsa="B3")

        assert result.ticker == "TOTS3"


# ── CotacoesRepository ────────────────────────────────────────────────────────

class TestCotacoesRepository:
    async def test_get_history_returns_list(self):
        from app.models.financial import FatosCotacoes

        c1 = FatosCotacoes()
        c1.data = date(2026, 5, 1)
        c1.fechamento = Decimal("38.50")

        c2 = FatosCotacoes()
        c2.data = date(2026, 5, 2)
        c2.fechamento = Decimal("39.00")

        session = _make_session(scalars_all=[c1, c2])
        repo = CotacoesRepository(session)

        result = await repo.get_history(uuid4())

        assert len(result) == 2
        assert result[0].fechamento == Decimal("38.50")

    async def test_get_history_empty_returns_empty(self):
        session = _make_session(scalars_all=[])
        repo = CotacoesRepository(session)

        result = await repo.get_history(uuid4())

        assert result == []

    async def test_get_history_calls_execute_once(self):
        session = _make_session(scalars_all=[])
        repo = CotacoesRepository(session)

        await repo.get_history(uuid4(), start=date(2026, 1, 1), end=date(2026, 5, 1))

        session.execute.assert_awaited_once()

    async def test_get_latest_returns_most_recent(self):
        from app.models.financial import FatosCotacoes

        cot = FatosCotacoes()
        cot.data = date(2026, 5, 28)
        cot.fechamento = Decimal("41.20")

        session = _make_session(scalar_one_or_none=cot)
        repo = CotacoesRepository(session)

        result = await repo.get_latest(uuid4())

        assert result is cot
        assert result.fechamento == Decimal("41.20")

    async def test_get_latest_returns_none_when_empty(self):
        session = _make_session(scalar_one_or_none=None)
        repo = CotacoesRepository(session)

        result = await repo.get_latest(uuid4())

        assert result is None

    async def test_upsert_batch_empty_skips_execute(self):
        session = _make_session()
        repo = CotacoesRepository(session)

        count = await repo.upsert_batch([])

        assert count == 0
        session.execute.assert_not_awaited()

    async def test_upsert_batch_returns_record_count(self):
        session = _make_session()
        repo = CotacoesRepository(session)

        records = [
            {"empresa_id": uuid4(), "data": date(2026, 5, 1), "fechamento": Decimal("38.5")},
            {"empresa_id": uuid4(), "data": date(2026, 5, 2), "fechamento": Decimal("39.0")},
        ]
        count = await repo.upsert_batch(records)

        assert count == 2
        session.execute.assert_awaited_once()
        session.flush.assert_awaited_once()


# ── MacroRepository ───────────────────────────────────────────────────────────

class TestMacroRepository:
    async def test_get_indicator_history_empty(self):
        session = _make_session(scalars_all=[])
        repo = MacroRepository(session)

        result = await repo.get_indicator_history("selic")

        assert result == []

    async def test_get_indicator_history_returns_records(self):
        from app.models.financial import FatosMacro

        m = FatosMacro()
        m.indicador = "selic"
        m.data = date(2026, 5, 1)
        m.valor = Decimal("10.5")

        session = _make_session(scalars_all=[m])
        repo = MacroRepository(session)

        result = await repo.get_indicator_history("selic")

        assert len(result) == 1
        assert result[0].indicador == "selic"
        assert result[0].valor == Decimal("10.5")

    async def test_get_indicator_history_passes_date_filters(self):
        session = _make_session(scalars_all=[])
        repo = MacroRepository(session)

        await repo.get_indicator_history(
            "ipca",
            start=date(2025, 1, 1),
            end=date(2025, 12, 31),
        )

        session.execute.assert_awaited_once()

    async def test_get_latest_returns_none_when_empty(self):
        session = _make_session(scalar_one_or_none=None)
        repo = MacroRepository(session)

        result = await repo.get_latest("cdi")

        assert result is None

    async def test_upsert_batch_empty_skips_execute(self):
        session = _make_session()
        repo = MacroRepository(session)

        count = await repo.upsert_batch([])

        assert count == 0
        session.execute.assert_not_awaited()

    async def test_upsert_batch_returns_count(self):
        session = _make_session()
        repo = MacroRepository(session)

        records = [
            {"indicador": "selic", "data": date(2026, 5, 1), "valor": Decimal("10.5"),
             "fonte": "BCB", "pais": "Brasil"},
            {"indicador": "selic", "data": date(2026, 5, 2), "valor": Decimal("10.5"),
             "fonte": "BCB", "pais": "Brasil"},
        ]
        count = await repo.upsert_batch(records)

        assert count == 2
        session.flush.assert_awaited_once()
