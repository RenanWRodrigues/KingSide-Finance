"""Initial schema — create all schemas and tables.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels = None
depends_on = None

_SCHEMAS = ("raw", "staging", "intermediate", "marts", "analytics", "monitoring")


def upgrade() -> None:
    for schema in _SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    # ── marts.dim_empresa ────────────────────────────────────────────────────
    op.create_table(
        "dim_empresa",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("nome_completo", sa.String(500)),
        sa.Column("setor", sa.String(100)),
        sa.Column("subsetor", sa.String(100)),
        sa.Column("segmento", sa.String(100)),
        sa.Column("bolsa", sa.String(20), nullable=False),
        sa.Column("pais", sa.String(50), nullable=False, server_default="Brasil"),
        sa.Column("moeda", sa.String(10), nullable=False, server_default="BRL"),
        sa.Column("cnpj", sa.String(20)),
        sa.Column("site", sa.String(300)),
        sa.Column("descricao", sa.Text()),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_extra", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("ticker", name="uq_dim_empresa_ticker"),
        schema="marts",
    )
    op.create_index("ix_dim_empresa_ticker", "dim_empresa", ["ticker"], schema="marts")
    op.create_index("ix_dim_empresa_setor", "dim_empresa", ["setor"], schema="marts")

    # ── marts.dim_tempo ──────────────────────────────────────────────────────
    op.create_table(
        "dim_tempo",
        sa.Column("data", sa.Date(), primary_key=True),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("mes", sa.Integer(), nullable=False),
        sa.Column("dia", sa.Integer(), nullable=False),
        sa.Column("trimestre", sa.Integer(), nullable=False),
        sa.Column("semana_ano", sa.Integer(), nullable=False),
        sa.Column("dia_semana", sa.Integer(), nullable=False),
        sa.Column("nome_dia_semana", sa.String(20), nullable=False),
        sa.Column("nome_mes", sa.String(20), nullable=False),
        sa.Column("eh_dia_util", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("eh_feriado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("nome_feriado", sa.String(100)),
        schema="marts",
    )
    op.create_index("ix_dim_tempo_ano_mes", "dim_tempo", ["ano", "mes"], schema="marts")

    # ── marts.fatos_cotacoes ─────────────────────────────────────────────────
    op.create_table(
        "fatos_cotacoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("marts.dim_empresa.id"), nullable=False),
        sa.Column("data", sa.Date(),
                  sa.ForeignKey("marts.dim_tempo.data"), nullable=False),
        sa.Column("abertura", sa.Numeric(18, 6)),
        sa.Column("maxima", sa.Numeric(18, 6)),
        sa.Column("minima", sa.Numeric(18, 6)),
        sa.Column("fechamento", sa.Numeric(18, 6), nullable=False),
        sa.Column("fechamento_ajustado", sa.Numeric(18, 6)),
        sa.Column("volume", sa.BigInteger()),
        sa.Column("volume_financeiro", sa.Numeric(24, 2)),
        sa.Column("variacao_dia", sa.Numeric(10, 6)),
        sa.Column("variacao_dia_pct", sa.Numeric(10, 6)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("empresa_id", "data", name="uq_fatos_cotacoes_empresa_data"),
        schema="marts",
    )
    op.create_index("ix_fatos_cotacoes_empresa_data", "fatos_cotacoes", ["empresa_id", "data"], schema="marts")
    op.create_index("ix_fatos_cotacoes_data", "fatos_cotacoes", ["data"], schema="marts")

    # ── marts.fatos_dividendos ───────────────────────────────────────────────
    op.create_table(
        "fatos_dividendos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("marts.dim_empresa.id"), nullable=False),
        sa.Column("data_ex", sa.Date(), nullable=False),
        sa.Column("data_pagamento", sa.Date()),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("valor", sa.Numeric(18, 6), nullable=False),
        sa.Column("moeda", sa.String(10), nullable=False, server_default="BRL"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="marts",
    )
    op.create_index("ix_fatos_dividendos_empresa_data", "fatos_dividendos", ["empresa_id", "data_ex"], schema="marts")

    # ── marts.fatos_financials ───────────────────────────────────────────────
    op.create_table(
        "fatos_financials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("marts.dim_empresa.id"), nullable=False),
        sa.Column("periodo", sa.Date(), nullable=False),
        sa.Column("tipo_periodo", sa.String(20), nullable=False),
        sa.Column("receita_liquida", sa.Numeric(24, 2)),
        sa.Column("ebitda", sa.Numeric(24, 2)),
        sa.Column("ebit", sa.Numeric(24, 2)),
        sa.Column("lucro_liquido", sa.Numeric(24, 2)),
        sa.Column("divida_liquida", sa.Numeric(24, 2)),
        sa.Column("patrimonio_liquido", sa.Numeric(24, 2)),
        sa.Column("ativo_total", sa.Numeric(24, 2)),
        sa.Column("caixa", sa.Numeric(24, 2)),
        sa.Column("margem_bruta", sa.Numeric(10, 6)),
        sa.Column("margem_ebitda", sa.Numeric(10, 6)),
        sa.Column("margem_liquida", sa.Numeric(10, 6)),
        sa.Column("roe", sa.Numeric(10, 6)),
        sa.Column("roa", sa.Numeric(10, 6)),
        sa.Column("roic", sa.Numeric(10, 6)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("empresa_id", "periodo", "tipo_periodo", name="uq_fatos_financials"),
        schema="marts",
    )
    op.create_index("ix_fatos_financials_empresa_periodo", "fatos_financials",
                    ["empresa_id", "periodo"], schema="marts")

    # ── marts.fatos_macro ────────────────────────────────────────────────────
    op.create_table(
        "fatos_macro",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("indicador", sa.String(100), nullable=False),
        sa.Column("descricao", sa.String(300)),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("valor", sa.Numeric(24, 8), nullable=False),
        sa.Column("unidade", sa.String(50)),
        sa.Column("fonte", sa.String(100)),
        sa.Column("pais", sa.String(50), nullable=False, server_default="Brasil"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("indicador", "data", name="uq_fatos_macro_indicador_data"),
        schema="marts",
    )
    op.create_index("ix_fatos_macro_indicador_data", "fatos_macro", ["indicador", "data"], schema="marts")

    # ── marts.fatos_forecasts ────────────────────────────────────────────────
    op.create_table(
        "fatos_forecasts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("marts.dim_empresa.id"), nullable=False),
        sa.Column("data_geracao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_forecast", sa.Date(), nullable=False),
        sa.Column("modelo", sa.String(100), nullable=False),
        sa.Column("horizonte_dias", sa.Integer(), nullable=False),
        sa.Column("preco_previsto", sa.Numeric(18, 6), nullable=False),
        sa.Column("lower_bound", sa.Numeric(18, 6)),
        sa.Column("upper_bound", sa.Numeric(18, 6)),
        sa.Column("confianca", sa.Numeric(5, 4)),
        sa.Column("metricas", postgresql.JSONB()),
        sa.Column("mlflow_run_id", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="marts",
    )
    op.create_index("ix_fatos_forecasts_empresa_data", "fatos_forecasts",
                    ["empresa_id", "data_forecast"], schema="marts")

    # ── raw.cotacoes_raw ─────────────────────────────────────────────────────
    op.create_table(
        "cotacoes_raw",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(18, 6)),
        sa.Column("high", sa.Numeric(18, 6)),
        sa.Column("low", sa.Numeric(18, 6)),
        sa.Column("close", sa.Numeric(18, 6)),
        sa.Column("adj_close", sa.Numeric(18, 6)),
        sa.Column("volume", sa.BigInteger()),
        sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("ticker", "date", name="uq_cotacoes_raw_ticker_date"),
        schema="raw",
    )
    op.create_index("ix_cotacoes_raw_ticker_date", "cotacoes_raw", ["ticker", "date"], schema="raw")

    # ── raw.macro_raw ────────────────────────────────────────────────────────
    op.create_table(
        "macro_raw",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("indicador", sa.String(100), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("valor", sa.Numeric(24, 8), nullable=False),
        sa.Column("fonte", sa.String(100)),
        sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("indicador", "data", name="uq_macro_raw_indicador_data"),
        schema="raw",
    )
    op.create_index("ix_macro_raw_indicador_data", "macro_raw", ["indicador", "data"], schema="raw")


def downgrade() -> None:
    op.drop_table("fatos_forecasts", schema="marts")
    op.drop_table("fatos_macro", schema="marts")
    op.drop_table("fatos_financials", schema="marts")
    op.drop_table("fatos_dividendos", schema="marts")
    op.drop_table("fatos_cotacoes", schema="marts")
    op.drop_table("dim_tempo", schema="marts")
    op.drop_table("dim_empresa", schema="marts")
    op.drop_table("macro_raw", schema="raw")
    op.drop_table("cotacoes_raw", schema="raw")
    for schema in reversed(_SCHEMAS):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
