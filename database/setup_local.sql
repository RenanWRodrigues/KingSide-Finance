-- ============================================================
-- Finance — Local PostgreSQL Setup
-- Run as superuser (postgres):
--   psql -U postgres -f database/setup_local.sql
-- ============================================================

-- 1. Create role 'finance' if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'finance') THEN
        CREATE ROLE finance LOGIN PASSWORD 'finance_secure_password';
        RAISE NOTICE 'Role finance created.';
    ELSE
        RAISE NOTICE 'Role finance already exists, skipping.';
    END IF;
END
$$;

-- 2. Create database 'finance' if it doesn't exist
SELECT 'CREATE DATABASE finance OWNER finance ENCODING ''UTF8'' LC_COLLATE ''en_US.UTF-8'' LC_CTYPE ''en_US.UTF-8'' TEMPLATE template0'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'finance')\gexec

-- 3. Create database 'airflow' if it doesn't exist
SELECT 'CREATE DATABASE airflow OWNER finance ENCODING ''UTF8'' LC_COLLATE ''en_US.UTF-8'' LC_CTYPE ''en_US.UTF-8'' TEMPLATE template0'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')\gexec

GRANT ALL PRIVILEGES ON DATABASE finance TO finance;
GRANT ALL PRIVILEGES ON DATABASE airflow TO finance;

-- ============================================================
-- 4. Connect to 'finance' and create schemas + tables
-- ============================================================
\connect finance

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Schemas
CREATE SCHEMA IF NOT EXISTS raw          AUTHORIZATION finance;
CREATE SCHEMA IF NOT EXISTS staging      AUTHORIZATION finance;
CREATE SCHEMA IF NOT EXISTS intermediate AUTHORIZATION finance;
CREATE SCHEMA IF NOT EXISTS marts        AUTHORIZATION finance;
CREATE SCHEMA IF NOT EXISTS analytics    AUTHORIZATION finance;
CREATE SCHEMA IF NOT EXISTS monitoring   AUTHORIZATION finance;
CREATE SCHEMA IF NOT EXISTS snapshots    AUTHORIZATION finance;
CREATE SCHEMA IF NOT EXISTS seeds        AUTHORIZATION finance;

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
    id          BIGSERIAL       PRIMARY KEY,
    ticker      VARCHAR(20),
    titulo      TEXT            NOT NULL,
    resumo      TEXT,
    fonte       VARCHAR(200),
    url         TEXT,
    publicado_em TIMESTAMPTZ,
    sentimento  NUMERIC(5, 4),
    loaded_at   TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ── Indexes on raw ─────────────────────────────────────────

CREATE INDEX IF NOT EXISTS ix_cotacoes_raw_ticker_date ON raw.cotacoes_raw (ticker, date DESC);
CREATE INDEX IF NOT EXISTS ix_cotacoes_raw_loaded_at   ON raw.cotacoes_raw (loaded_at);
CREATE INDEX IF NOT EXISTS ix_macro_raw_indicador_data ON raw.macro_raw (indicador, data DESC);
CREATE INDEX IF NOT EXISTS ix_noticias_raw_ticker      ON raw.noticias_raw (ticker, publicado_em DESC);

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

CREATE INDEX IF NOT EXISTS ix_pipeline_runs_pipeline   ON monitoring.pipeline_runs (pipeline, started_at DESC);
CREATE INDEX IF NOT EXISTS ix_pipeline_runs_status     ON monitoring.pipeline_runs (status);

-- ── Grants ─────────────────────────────────────────────────

GRANT USAGE ON SCHEMA raw, staging, intermediate, marts, analytics, monitoring, snapshots, seeds TO finance;
GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA raw, monitoring TO finance;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA raw, monitoring TO finance;

ALTER DEFAULT PRIVILEGES IN SCHEMA raw        GRANT ALL ON TABLES    TO finance;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw        GRANT ALL ON SEQUENCES TO finance;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging    GRANT ALL ON TABLES    TO finance;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging    GRANT ALL ON SEQUENCES TO finance;
ALTER DEFAULT PRIVILEGES IN SCHEMA intermediate GRANT ALL ON TABLES  TO finance;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts      GRANT ALL ON TABLES    TO finance;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics  GRANT ALL ON TABLES    TO finance;
ALTER DEFAULT PRIVILEGES IN SCHEMA monitoring GRANT ALL ON TABLES    TO finance;
ALTER DEFAULT PRIVILEGES IN SCHEMA monitoring GRANT ALL ON SEQUENCES TO finance;

\echo '============================================================'
\echo 'Setup concluido! Banco finance criado com todos os schemas.'
\echo '============================================================'
