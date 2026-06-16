-- Creates extra databases on first postgres startup.
-- The primary database (finance) is already created by POSTGRES_DB env var.
SELECT 'CREATE DATABASE airflow'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'airflow'
)\gexec

GRANT ALL PRIVILEGES ON DATABASE airflow TO finance;
