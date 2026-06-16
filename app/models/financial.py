from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DimEmpresa(Base, TimestampMixin):
    __tablename__ = "dim_empresa"
    __table_args__ = (
        UniqueConstraint("ticker", name="uq_dim_empresa_ticker"),
        Index("ix_dim_empresa_ticker", "ticker"),
        Index("ix_dim_empresa_setor", "setor"),
        {"schema": "marts"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    nome_completo: Mapped[str | None] = mapped_column(String(500))
    setor: Mapped[str | None] = mapped_column(String(100))
    subsetor: Mapped[str | None] = mapped_column(String(100))
    segmento: Mapped[str | None] = mapped_column(String(100))
    bolsa: Mapped[str] = mapped_column(String(20), nullable=False)
    pais: Mapped[str] = mapped_column(String(50), nullable=False, default="Brasil")
    moeda: Mapped[str] = mapped_column(String(10), nullable=False, default="BRL")
    cnpj: Mapped[str | None] = mapped_column(String(20))
    site: Mapped[str | None] = mapped_column(String(300))
    descricao: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB)

    cotacoes: Mapped[list["FatosCotacoes"]] = relationship(back_populates="empresa")
    dividendos: Mapped[list["FatosDividendos"]] = relationship(back_populates="empresa")
    financials: Mapped[list["FatosFinancials"]] = relationship(back_populates="empresa")


class DimTempo(Base):
    __tablename__ = "dim_tempo"
    __table_args__ = (
        Index("ix_dim_tempo_ano_mes", "ano", "mes"),
        {"schema": "marts"},
    )

    data: Mapped[date] = mapped_column(Date, primary_key=True)
    ano: Mapped[int] = mapped_column(nullable=False)
    mes: Mapped[int] = mapped_column(nullable=False)
    dia: Mapped[int] = mapped_column(nullable=False)
    trimestre: Mapped[int] = mapped_column(nullable=False)
    semana_ano: Mapped[int] = mapped_column(nullable=False)
    dia_semana: Mapped[int] = mapped_column(nullable=False)
    nome_dia_semana: Mapped[str] = mapped_column(String(20), nullable=False)
    nome_mes: Mapped[str] = mapped_column(String(20), nullable=False)
    eh_dia_util: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    eh_feriado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    nome_feriado: Mapped[str | None] = mapped_column(String(100))


class FatosCotacoes(Base, TimestampMixin):
    __tablename__ = "fatos_cotacoes"
    __table_args__ = (
        UniqueConstraint("empresa_id", "data", name="uq_fatos_cotacoes_empresa_data"),
        Index("ix_fatos_cotacoes_empresa_data", "empresa_id", "data"),
        Index("ix_fatos_cotacoes_data", "data"),
        {"schema": "marts"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    empresa_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("marts.dim_empresa.id"), nullable=False
    )
    data: Mapped[date] = mapped_column(Date, ForeignKey("marts.dim_tempo.data"), nullable=False)
    abertura: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    maxima: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    minima: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    fechamento: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    fechamento_ajustado: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    volume: Mapped[int | None] = mapped_column(BigInteger)
    volume_financeiro: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    variacao_dia: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    variacao_dia_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))

    empresa: Mapped["DimEmpresa"] = relationship(back_populates="cotacoes")
    dim_tempo: Mapped["DimTempo"] = relationship()


class FatosDividendos(Base, TimestampMixin):
    __tablename__ = "fatos_dividendos"
    __table_args__ = (
        Index("ix_fatos_dividendos_empresa_data", "empresa_id", "data_ex"),
        {"schema": "marts"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    empresa_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("marts.dim_empresa.id"), nullable=False
    )
    data_ex: Mapped[date] = mapped_column(Date, nullable=False)
    data_pagamento: Mapped[date | None] = mapped_column(Date)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    moeda: Mapped[str] = mapped_column(String(10), nullable=False, default="BRL")

    empresa: Mapped["DimEmpresa"] = relationship(back_populates="dividendos")


class FatosFinancials(Base, TimestampMixin):
    __tablename__ = "fatos_financials"
    __table_args__ = (
        UniqueConstraint("empresa_id", "periodo", "tipo_periodo", name="uq_fatos_financials"),
        Index("ix_fatos_financials_empresa_periodo", "empresa_id", "periodo"),
        {"schema": "marts"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    empresa_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("marts.dim_empresa.id"), nullable=False
    )
    periodo: Mapped[date] = mapped_column(Date, nullable=False)
    tipo_periodo: Mapped[str] = mapped_column(String(20), nullable=False)
    receita_liquida: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    ebitda: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    ebit: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    lucro_liquido: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    divida_liquida: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    patrimonio_liquido: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    ativo_total: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    caixa: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    margem_bruta: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    margem_ebitda: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    margem_liquida: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    roe: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    roa: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    roic: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))

    empresa: Mapped["DimEmpresa"] = relationship(back_populates="financials")


class FatosMacro(Base, TimestampMixin):
    __tablename__ = "fatos_macro"
    __table_args__ = (
        UniqueConstraint("indicador", "data", name="uq_fatos_macro_indicador_data"),
        Index("ix_fatos_macro_indicador_data", "indicador", "data"),
        {"schema": "marts"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    indicador: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(300))
    data: Mapped[date] = mapped_column(Date, nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    unidade: Mapped[str | None] = mapped_column(String(50))
    fonte: Mapped[str | None] = mapped_column(String(100))
    pais: Mapped[str] = mapped_column(String(50), nullable=False, default="Brasil")


class FatosForecasts(Base, TimestampMixin):
    __tablename__ = "fatos_forecasts"
    __table_args__ = (
        Index("ix_fatos_forecasts_empresa_data", "empresa_id", "data_forecast"),
        {"schema": "marts"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    empresa_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("marts.dim_empresa.id"), nullable=False
    )
    data_geracao: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_forecast: Mapped[date] = mapped_column(Date, nullable=False)
    modelo: Mapped[str] = mapped_column(String(100), nullable=False)
    horizonte_dias: Mapped[int] = mapped_column(nullable=False)
    preco_previsto: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    lower_bound: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    upper_bound: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    confianca: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    metricas: Mapped[dict | None] = mapped_column(JSONB)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(100))
