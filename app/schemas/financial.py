from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EmpresaBase(BaseModel):
    ticker: str = Field(examples=["PETR4", "VALE3", "ITUB4"])
    nome: str
    setor: str | None = None
    subsetor: str | None = None
    bolsa: str = "B3"
    pais: str = "Brasil"
    moeda: str = "BRL"


class EmpresaCreate(EmpresaBase):
    nome_completo: str | None = None
    cnpj: str | None = None
    descricao: str | None = None


class EmpresaResponse(EmpresaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ativo: bool
    created_at: datetime


class CotacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticker: str
    data: date
    abertura: Decimal | None = None
    maxima: Decimal | None = None
    minima: Decimal | None = None
    fechamento: Decimal
    fechamento_ajustado: Decimal | None = None
    volume: int | None = None
    variacao_dia_pct: Decimal | None = None


class CotacaoSimples(BaseModel):
    data: date
    abertura: float | None = None
    maxima: float | None = None
    minima: float | None = None
    fechamento: float
    volume: int | None = None


class CotacaoHistoricoResponse(BaseModel):
    ticker: str
    periodo_inicio: date
    periodo_fim: date
    total_registros: int
    cotacoes: list[CotacaoSimples]


class DividendoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticker: str
    data_ex: date
    data_pagamento: date | None = None
    tipo: str
    valor: Decimal
    moeda: str


class FinancialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticker: str
    periodo: date
    tipo_periodo: str
    receita_liquida: Decimal | None = None
    ebitda: Decimal | None = None
    lucro_liquido: Decimal | None = None
    margem_ebitda: Decimal | None = None
    margem_liquida: Decimal | None = None
    roe: Decimal | None = None
    roic: Decimal | None = None


class MacroIndicadorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    indicador: str
    descricao: str | None = None
    data: date
    valor: Decimal
    unidade: str | None = None
    fonte: str | None = None


class ForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticker: str
    data_geracao: datetime
    data_forecast: date
    modelo: str
    horizonte_dias: int
    preco_previsto: Decimal
    lower_bound: Decimal | None = None
    upper_bound: Decimal | None = None
    confianca: Decimal | None = None


class ForecastRequest(BaseModel):
    ticker: str = Field(examples=["PETR4"])
    horizonte_dias: int = Field(default=30, ge=1, le=365)
    modelo: str = Field(default="prophet", examples=["prophet", "arima", "lstm"])
    confianca: float = Field(default=0.95, ge=0.5, le=0.99)


class RankingItem(BaseModel):
    ticker: str
    nome: str
    setor: str | None = None
    valor: Decimal
    posicao: int


class RankingResponse(BaseModel):
    tipo: str
    periodo: str
    total: int
    items: list[RankingItem]


class SentimentResponse(BaseModel):
    ticker: str
    score: float = Field(ge=-1.0, le=1.0)
    label: str
    confianca: float
    total_noticias: int
    data_analise: datetime


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    data: list


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: datetime
    services: dict[str, str]


# ── Compare / Quantitative ───────────────────────────────────

class CompareMetrics(BaseModel):
    ticker: str
    nome: str
    setor: str | None = None
    preco_atual: float | None = None
    retorno_acumulado: float | None = None
    cagr: float | None = None
    volatilidade_anual: float | None = None
    sharpe: float | None = None
    sortino: float | None = None
    max_drawdown: float | None = None
    beta: float | None = None
    alpha: float | None = None
    var_95: float | None = None
    rsi_14: float | None = None
    ma_20: float | None = None
    ma_50: float | None = None
    ma_200: float | None = None


class ComparePerformancePoint(BaseModel):
    data: str
    fechamento: float
    normalizado: float


class ComparePerformanceSeries(BaseModel):
    ticker: str
    nome: str
    setor: str | None = None
    pontos: list[ComparePerformancePoint]


class CompareResponse(BaseModel):
    tickers: list[str]
    periodo: str
    metrics: list[CompareMetrics]
    correlacao: dict[str, dict[str, float | None]]
    performance: list[ComparePerformanceSeries]


class SectorPerformanceItem(BaseModel):
    setor: str
    tickers: list[str]
    retorno_medio_pct: float | None = None
    volatilidade_proxy: float | None = None
    total_ativos: int
    posicao: int


class SectorResponse(BaseModel):
    tipo: str
    total: int
    items: list[SectorPerformanceItem]
