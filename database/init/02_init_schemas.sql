-- Finance PostgreSQL Initialization
-- Extensions, schemas, and raw-layer tables.
-- Runs automatically on first container start via docker-entrypoint-initdb.d.

\connect finance

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS monitoring;
CREATE SCHEMA IF NOT EXISTS snapshots;
CREATE SCHEMA IF NOT EXISTS seeds;

-- Raw layer tables (ingested by Airflow / dbt)
CREATE TABLE IF NOT EXISTS raw.cotacoes_raw (
    id          BIGSERIAL PRIMARY KEY,
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
    id          BIGSERIAL PRIMARY KEY,
    indicador   VARCHAR(100)    NOT NULL,
    data        DATE            NOT NULL,
    valor       NUMERIC(24, 8)  NOT NULL,
    fonte       VARCHAR(100),
    loaded_at   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_macro_raw_indicador_data UNIQUE (indicador, data)
);

CREATE TABLE IF NOT EXISTS raw.empresas_raw (
    id              BIGSERIAL PRIMARY KEY,
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

-- Indexes
CREATE INDEX IF NOT EXISTS ix_cotacoes_raw_ticker_date ON raw.cotacoes_raw (ticker, date DESC);
CREATE INDEX IF NOT EXISTS ix_cotacoes_raw_loaded_at   ON raw.cotacoes_raw (loaded_at);
CREATE INDEX IF NOT EXISTS ix_macro_raw_indicador_data ON raw.macro_raw (indicador, data DESC);

-- Monitoring
CREATE TABLE IF NOT EXISTS monitoring.pipeline_runs (
    id          BIGSERIAL PRIMARY KEY,
    pipeline    VARCHAR(100)    NOT NULL,
    status      VARCHAR(20)     NOT NULL,
    started_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    rows_loaded INT,
    error_msg   TEXT,
    metadata    JSONB
);

-- Grants
GRANT USAGE ON SCHEMA raw, staging, intermediate, marts, analytics, monitoring, snapshots, seeds TO finance;
GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA raw TO finance;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA raw TO finance;
GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA monitoring TO finance;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA monitoring TO finance;
