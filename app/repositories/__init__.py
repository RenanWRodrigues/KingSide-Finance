"""Finance — Repository layer (data access objects)."""
from __future__ import annotations

from app.repositories.base import BaseRepository
from app.repositories.cotacoes import CotacoesRepository
from app.repositories.dividendos import DividendosRepository
from app.repositories.empresa import EmpresaRepository
from app.repositories.financials import FinancialsRepository
from app.repositories.forecasts import ForecastsRepository
from app.repositories.macro import MacroRepository

__all__ = [
    "BaseRepository",
    "CotacoesRepository",
    "DividendosRepository",
    "EmpresaRepository",
    "FinancialsRepository",
    "ForecastsRepository",
    "MacroRepository",
]
