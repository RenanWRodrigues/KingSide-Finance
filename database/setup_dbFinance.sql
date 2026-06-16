-- ============================================================
-- Finance — Setup do banco dbFinance (PostgreSQL local)
-- Execute no pgAdmin: clique com botão direito em dbFinance
--   → Query Tool → cole este script → F5
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- pg_stat_statements requer shared_preload_libraries no postgresql.conf.
-- No Docker, adicione ao docker-compose: command: postgres -c shared_preload_libraries=pg_stat_statements
-- Ignorado silenciosamente se não estiver pré-carregado.
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'pg_stat_statements não pôde ser criado (shared_preload_libraries ausente): %', SQLERRM;
END
$$;

-- ── Schemas ────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS monitoring;
CREATE SCHEMA IF NOT EXISTS snapshots;
CREATE SCHEMA IF NOT EXISTS seeds;

-- ── Raw layer ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS raw.cotacoes_raw (
    id          BIGSERIAL       PRIMARY KEY,
    ticker      VARCHAR(20)     NOT NULL,
    date        DATE            NOT NULL,
    open        NUMERIC(18, 6),
    high        NUMERIC(18, 6),
    low         NUMERIC(18, 6),
    close       NUMERIC(18, 6),
    adj_close   NUMERIC(18, 6),
    volume      BIGINT,
    loaded_at   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_cotacoes_raw_ticker_date UNIQUE (ticker, date)
);

CREATE TABLE IF NOT EXISTS raw.macro_raw (
    id          BIGSERIAL       PRIMARY KEY,
    indicador   VARCHAR(100)    NOT NULL,
    data        DATE            NOT NULL,
    valor       NUMERIC(24, 8)  NOT NULL,
    fonte       VARCHAR(100),
    loaded_at   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_macro_raw_indicador_data UNIQUE (indicador, data)
);

CREATE TABLE IF NOT EXISTS raw.empresas_raw (
    id              BIGSERIAL       PRIMARY KEY,
    ticker          VARCHAR(20)     NOT NULL UNIQUE,
    nome            VARCHAR(200),
    nome_completo   VARCHAR(500),
    setor           VARCHAR(100),
    subsetor        VARCHAR(100),
    segmento        VARCHAR(100),
    bolsa           VARCHAR(20)     DEFAULT 'B3',
    pais            VARCHAR(50)     DEFAULT 'Brasil',
    moeda           VARCHAR(10)     DEFAULT 'BRL',
    cnpj            VARCHAR(20),
    site            VARCHAR(300),
    loaded_at       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.noticias_raw (
    id              BIGSERIAL       PRIMARY KEY,
    ticker          VARCHAR(20),
    titulo          TEXT            NOT NULL,
    resumo          TEXT,
    fonte           VARCHAR(200),
    url             TEXT,
    publicado_em    TIMESTAMPTZ,
    sentimento      NUMERIC(5, 4),
    loaded_at       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ── Indexes raw ────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS ix_cotacoes_raw_ticker_date ON raw.cotacoes_raw (ticker, date DESC);
CREATE INDEX IF NOT EXISTS ix_cotacoes_raw_loaded_at   ON raw.cotacoes_raw (loaded_at);
CREATE INDEX IF NOT EXISTS ix_macro_raw_indicador_data ON raw.macro_raw (indicador, data DESC);
CREATE INDEX IF NOT EXISTS ix_noticias_raw_ticker      ON raw.noticias_raw (ticker, publicado_em DESC);

-- ── Marts layer ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS marts.dim_empresa (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker          VARCHAR(20)     NOT NULL,
    nome            VARCHAR(200)    NOT NULL,
    nome_completo   VARCHAR(500),
    setor           VARCHAR(100),
    subsetor        VARCHAR(100),
    segmento        VARCHAR(100),
    bolsa           VARCHAR(20)     NOT NULL,
    pais            VARCHAR(50)     NOT NULL DEFAULT 'Brasil',
    moeda           VARCHAR(10)     NOT NULL DEFAULT 'BRL',
    cnpj            VARCHAR(20),
    site            VARCHAR(300),
    descricao       TEXT,
    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,
    metadata_extra  JSONB,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_dim_empresa_ticker UNIQUE (ticker)
);

CREATE TABLE IF NOT EXISTS marts.dim_tempo (
    data            DATE            PRIMARY KEY,
    ano             INT             NOT NULL,
    mes             INT             NOT NULL,
    dia             INT             NOT NULL,
    trimestre       INT             NOT NULL,
    semana_ano      INT             NOT NULL,
    dia_semana      INT             NOT NULL,
    nome_dia_semana VARCHAR(20)     NOT NULL,
    nome_mes        VARCHAR(20)     NOT NULL,
    eh_dia_util     BOOLEAN         NOT NULL DEFAULT TRUE,
    eh_feriado      BOOLEAN         NOT NULL DEFAULT FALSE,
    nome_feriado    VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS marts.fatos_cotacoes (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id          UUID            NOT NULL REFERENCES marts.dim_empresa(id),
    data                DATE            NOT NULL REFERENCES marts.dim_tempo(data),
    abertura            NUMERIC(18, 6),
    maxima              NUMERIC(18, 6),
    minima              NUMERIC(18, 6),
    fechamento          NUMERIC(18, 6)  NOT NULL,
    fechamento_ajustado NUMERIC(18, 6),
    volume              BIGINT,
    volume_financeiro   NUMERIC(24, 2),
    variacao_dia        NUMERIC(10, 6),
    variacao_dia_pct    NUMERIC(10, 6),
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fatos_cotacoes_empresa_data UNIQUE (empresa_id, data)
);

CREATE TABLE IF NOT EXISTS marts.fatos_dividendos (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id      UUID            NOT NULL REFERENCES marts.dim_empresa(id),
    data_ex         DATE            NOT NULL,
    data_pagamento  DATE,
    tipo            VARCHAR(50)     NOT NULL,
    valor           NUMERIC(18, 6)  NOT NULL,
    moeda           VARCHAR(10)     NOT NULL DEFAULT 'BRL',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS marts.fatos_financials (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id          UUID            NOT NULL REFERENCES marts.dim_empresa(id),
    periodo             DATE            NOT NULL,
    tipo_periodo        VARCHAR(20)     NOT NULL,
    receita_liquida     NUMERIC(24, 2),
    ebitda              NUMERIC(24, 2),
    ebit                NUMERIC(24, 2),
    lucro_liquido       NUMERIC(24, 2),
    divida_liquida      NUMERIC(24, 2),
    patrimonio_liquido  NUMERIC(24, 2),
    ativo_total         NUMERIC(24, 2),
    caixa               NUMERIC(24, 2),
    margem_bruta        NUMERIC(10, 6),
    margem_ebitda       NUMERIC(10, 6),
    margem_liquida      NUMERIC(10, 6),
    roe                 NUMERIC(10, 6),
    roa                 NUMERIC(10, 6),
    roic                NUMERIC(10, 6),
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fatos_financials UNIQUE (empresa_id, periodo, tipo_periodo)
);

CREATE TABLE IF NOT EXISTS marts.fatos_macro (
    id          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    indicador   VARCHAR(100)    NOT NULL,
    descricao   VARCHAR(300),
    data        DATE            NOT NULL,
    valor       NUMERIC(24, 8)  NOT NULL,
    unidade     VARCHAR(50),
    fonte       VARCHAR(100),
    pais        VARCHAR(50)     NOT NULL DEFAULT 'Brasil',
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fatos_macro_indicador_data UNIQUE (indicador, data)
);

CREATE TABLE IF NOT EXISTS marts.fatos_forecasts (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id      UUID            NOT NULL REFERENCES marts.dim_empresa(id),
    data_geracao    TIMESTAMPTZ     NOT NULL,
    data_forecast   DATE            NOT NULL,
    modelo          VARCHAR(100)    NOT NULL,
    horizonte_dias  INT             NOT NULL,
    preco_previsto  NUMERIC(18, 6)  NOT NULL,
    lower_bound     NUMERIC(18, 6),
    upper_bound     NUMERIC(18, 6),
    confianca       NUMERIC(5, 4),
    metricas        JSONB,
    mlflow_run_id   VARCHAR(100),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ── Indexes marts ──────────────────────────────────────────

CREATE INDEX IF NOT EXISTS ix_dim_empresa_ticker         ON marts.dim_empresa (ticker);
CREATE INDEX IF NOT EXISTS ix_dim_empresa_setor          ON marts.dim_empresa (setor);
CREATE INDEX IF NOT EXISTS ix_dim_tempo_ano_mes          ON marts.dim_tempo (ano, mes);
CREATE INDEX IF NOT EXISTS ix_fatos_cotacoes_empresa_data ON marts.fatos_cotacoes (empresa_id, data);
CREATE INDEX IF NOT EXISTS ix_fatos_cotacoes_data        ON marts.fatos_cotacoes (data);
CREATE INDEX IF NOT EXISTS ix_fatos_dividendos_empresa   ON marts.fatos_dividendos (empresa_id, data_ex);
CREATE INDEX IF NOT EXISTS ix_fatos_financials_empresa   ON marts.fatos_financials (empresa_id, periodo);
CREATE INDEX IF NOT EXISTS ix_fatos_macro_indicador_data ON marts.fatos_macro (indicador, data);
CREATE INDEX IF NOT EXISTS ix_fatos_forecasts_empresa    ON marts.fatos_forecasts (empresa_id, data_forecast);

-- ── Monitoring ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS monitoring.pipeline_runs (
    id          BIGSERIAL       PRIMARY KEY,
    pipeline    VARCHAR(100)    NOT NULL,
    status      VARCHAR(20)     NOT NULL,
    started_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    rows_loaded INT,
    error_msg   TEXT,
    metadata    JSONB
);

CREATE INDEX IF NOT EXISTS ix_pipeline_runs_pipeline ON monitoring.pipeline_runs (pipeline, started_at DESC);
CREATE INDEX IF NOT EXISTS ix_pipeline_runs_status   ON monitoring.pipeline_runs (status);
