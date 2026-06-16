# KingSide Finance

**Plataforma Enterprise de Análise Financeira e Machine Learning**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-1.9-FF694B?style=for-the-badge&logo=dbt&logoColor=white)
![Airflow](https://img.shields.io/badge/Airflow-2.10-017CEE?style=for-the-badge&logo=apache-airflow&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![MLflow](https://img.shields.io/badge/MLflow-2.18-0194E2?style=for-the-badge&logo=mlflow&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

---

## Visão Geral

A KingSide Finance é uma **plataforma de inteligência financeira pronta para produção**, projetada para fintechs, bancos digitais, fundos de hedge e equipes de pesquisa quantitativa. Combina engenharia de dados moderna, analytics engineering, machine learning e APIs REST em uma arquitetura unificada e cloud-ready.

**Principais capacidades:**

- Ingestão em tempo real do Yahoo Finance, BCB SGS, FRED e Alpha Vantage
- Pipelines ELT com arquitetura Medallion (Bronze → Prata → Ouro)
- Data warehouse dimensional com dbt (metodologia Kimball)
- Previsão com ML: Prophet, ARIMA/SARIMA, LSTM
- Classificação com ML: XGBoost, Random Forest, LightGBM
- Detecção de anomalias de mercado com Isolation Forest
- Análise de sentimento financeiro com FinBERT
- API REST com FastAPI, autenticação JWT, cache Redis e rate limiting
- Dashboard executivo com Streamlit + integração com Power BI
- Orquestração com Apache Airflow e CeleryExecutor
- Rastreamento de experimentos e registro de modelos com MLflow
- Stack completo via Docker Compose

---

## Arquitetura

```
┌──────────────────────────────────────────────────────────────────────┐
│                        FONTES DE DADOS                                │
│   Yahoo Finance │ BCB SGS │ FRED │ Alpha Vantage │ CVM │ NewsAPI      │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ DAGs do Airflow
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    CAMADA BRONZE  (raw.*)                             │
│              Tabelas brutas imutáveis e append-only                   │
│    cotacoes_raw │ macro_raw │ empresas_raw │ dividendos_raw           │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ modelos staging do dbt
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    CAMADA PRATA  (staging.*)                          │
│         Tipagem, deduplicação, renomeação e validação                 │
│   stg_cotacoes │ stg_empresas │ stg_dividendos │ stg_macro            │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ modelos mart do dbt
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     CAMADA OURO  (marts.*)                            │
│            Modelo dimensional — star schema Kimball                   │
│                                                                        │
│  DIMENSÕES                     FATOS                                  │
│  ─────────────────             ──────────────────────                 │
│  dim_empresa                   fato_cotacoes                          │
│  dim_tempo                     fato_dividendos                        │
│  dim_setor                     fato_financials                        │
│  dim_pais                      fato_macro                             │
│  dim_moeda                     fato_forecasts                         │
│                                                                        │
│  ANALYTICS                                                            │
│  ──────────────────────────────────────────────                       │
│  agg_retornos │ agg_indicadores_tecnicos │ agg_ranking                │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │   FastAPI    │ │  Streamlit   │ │   Power BI   │
    │   REST API   │ │  Dashboard   │ │  DirectQuery │
    │  Porta 8000  │ │  Porta 8501  │ │              │
    └──────────────┘ └──────────────┘ └──────────────┘
              │
    ┌──────────────────────┐
    │   Pipeline de ML      │
    │  ─────────────────── │
    │  Prophet (Previsão)   │
    │  ARIMA/SARIMA         │
    │  LSTM (Rede Neural)   │
    │  XGBoost (Classifier) │
    │  Isolation Forest     │
    │  FinBERT (Sentimento) │
    │                       │
    │  → MLflow Tracking    │
    └──────────────────────┘
```

---

## Stack Tecnológica

| Camada               | Tecnologia                            |
| -------------------- | ------------------------------------- |
| Linguagem            | Python 3.12                           |
| Framework Web        | FastAPI + Uvicorn                     |
| ORM                  | SQLAlchemy 2.0 (async)                |
| Banco de Dados       | PostgreSQL 16                         |
| Cache                | Redis 7                               |
| Migrações            | Alembic                               |
| Validação            | Pydantic v2                           |
| Processamento        | Pandas + Polars + PyArrow             |
| Transformação        | dbt-core 1.9 + dbt-postgres           |
| Orquestração         | Apache Airflow 2.10 (CeleryExecutor)  |
| ML — Previsão        | Prophet + pmdarima + TensorFlow/Keras |
| ML — Classificação   | XGBoost + LightGBM + Scikit-Learn     |
| Detecção de Anomalia | Isolation Forest (Scikit-Learn)       |
| NLP                  | FinBERT (HuggingFace Transformers)    |
| Tracking de Experim. | MLflow 2.18                           |
| Monitoramento Drift  | Evidently AI                          |
| Visualização         | Streamlit + Plotly                    |
| BI                   | Power BI (DirectQuery)                |
| Logging              | Loguru (JSON estruturado)             |
| DevOps               | Docker + Docker Compose               |
| CI/CD                | GitHub Actions                        |
| Qualidade de Código  | Ruff + Black + MyPy                   |
| Testes               | Pytest + pytest-asyncio               |

---

## Início Rápido

### Pré-requisitos

- Docker e Docker Compose
- Python 3.12 + Poetry

### 1. Clonar e configurar

```bash
git clone https://github.com/seu-usuario/finance.git
cd finance
cp .env.example .env
# Edite o .env com suas chaves de API e senhas
```

### 2. Subir com Docker Compose

```bash
docker-compose up -d
```

Serviços disponíveis após inicialização:

| Serviço    | URL                                   |
| ---------- | ------------------------------------- |
| FastAPI    | http://localhost:8000/docs            |
| Streamlit  | http://localhost:8501                 |
| Airflow    | http://localhost:8080 (admin / admin) |
| MLflow     | http://localhost:5000                 |
| PostgreSQL | localhost:5433                        |
| Redis      | localhost:6379                        |

### 3. Desenvolvimento local (sem Docker)

```bash
# Instalar dependências
poetry install --with test,lint,ml,viz

# Subir apenas PostgreSQL e Redis
docker-compose up -d postgres redis

# Iniciar a API
uvicorn app.main:app --reload --port 8000

# Iniciar o dashboard
streamlit run dashboards/streamlit/app.py --server.port 8501
```

---

## Endpoints da API

### Ações

| Método | Endpoint                             | Descrição                       |
| ------ | ------------------------------------ | ------------------------------- |
| GET    | `/api/v1/stocks`                     | Lista todas as ações (paginado) |
| GET    | `/api/v1/stocks/{ticker}`            | Detalhes de uma ação            |
| GET    | `/api/v1/stocks/{ticker}/history`    | Histórico de preços (OHLCV)     |
| GET    | `/api/v1/stocks/{ticker}/dividends`  | Histórico de dividendos         |
| GET    | `/api/v1/stocks/{ticker}/financials` | Demonstrações financeiras       |
| GET    | `/api/v1/stocks/{ticker}/valuation`  | Múltiplos de valuation          |

### Previsão

| Método | Endpoint                    | Descrição                  |
| ------ | --------------------------- | -------------------------- |
| GET    | `/api/v1/forecast/{ticker}` | Previsão de preço por ML   |
| POST   | `/api/v1/forecast/generate` | Aciona previsão assíncrona |

### Rankings

| Método | Endpoint                   | Descrição                    |
| ------ | -------------------------- | ---------------------------- |
| GET    | `/api/v1/ranking/dividend` | Top ações por dividend yield |
| GET    | `/api/v1/ranking/growth`   | Top ações por crescimento    |
| GET    | `/api/v1/ranking/momentum` | Top ações por momentum       |

### Macro

| Método | Endpoint                           | Descrição                            |
| ------ | ---------------------------------- | ------------------------------------ |
| GET    | `/api/v1/macro`                    | Lista indicadores disponíveis        |
| GET    | `/api/v1/macro/brasil/{indicador}` | BCB: selic, ipca, cambio_dolar, igpm |
| GET    | `/api/v1/macro/fred/{series_id}`   | FRED: DFF, SP500, UNRATE, GDP        |

### Sentimento

| Método | Endpoint                     | Descrição                   |
| ------ | ---------------------------- | --------------------------- |
| GET    | `/api/v1/sentiment/{ticker}` | Score de sentimento via NLP |

### Comparação e Insights

| Método | Endpoint           | Descrição                            |
| ------ | ------------------ | ------------------------------------ |
| GET    | `/api/v1/compare`  | Comparação de múltiplos ativos       |
| GET    | `/api/v1/insights` | Insights automáticos de investimento |
| GET    | `/api/v1/heatmap`  | Mapa de calor do mercado             |

### Sistema

| Método | Endpoint  | Descrição             |
| ------ | --------- | --------------------- |
| GET    | `/health` | Health check completo |

---

## Pipeline ELT

```
1. Extração  (DAG do Airflow: finance_daily_ingestion)
   ├── yfinance: OHLCV diário para ~200 tickers da B3
   ├── BCB SGS: SELIC, IPCA, IGPM, USD/BRL
   └── FRED: DFF, UNRATE, SP500, PIB

2. Carga → PostgreSQL raw.*
   └── Upsert com ON CONFLICT DO UPDATE

3. Transformação  (dbt run)
   ├── staging.*      → tipagem, renomeação, filtros
   ├── intermediate.* → joins complexos (ephemeral)
   └── marts.*        → dimensões, fatos, analytics

4. Testes  (dbt test)
   ├── Testes de unicidade
   ├── Testes de not-null
   ├── Testes de integridade referencial
   └── Regras de negócio (SQL customizado)
```

---

## Pipeline dbt

```bash
cd dbt

# Instalar pacotes
dbt deps

# Carregar dados de referência
dbt seed

# Executar todos os modelos
dbt run

# Executar por camada
dbt run --select staging
dbt run --select marts
dbt run --select tag:facts

# Testar todos os modelos
dbt test

# Gerar e servir documentação
dbt docs generate && dbt docs serve

# Executar + testar (padrão CI)
dbt build
```

---

## Pipeline de Machine Learning

```
Execução semanal de ML  (DAG do Airflow: finance_ml_pipeline)
│
├── 1. Preparação dos Dados
│   └── Busca 3 anos de histórico por ticker
│
├── 2. Previsão de Preços  (por ticker)
│   ├── Prophet: tendência + sazonalidade + feriados
│   ├── ARIMA: baseline estatístico
│   └── Ensemble: média ponderada dos modelos
│
├── 3. Classificação de Retorno
│   ├── Engenharia de features (técnico + fundamentalista)
│   ├── Classificação multiclasse com XGBoost
│   └── Saída: superar / neutro / abaixo do mercado
│
├── 4. Detecção de Anomalias
│   └── Isolation Forest em features de preço e volume
│
├── 5. Análise de Sentimento
│   └── FinBERT aplicado às últimas manchetes de notícias
│
└── 6. Registro no MLflow
    ├── Parâmetros, métricas e artefatos
    └── Registro do modelo (Staging → Production)
```

---

## DAGs do Airflow

| DAG                        | Agendamento         | Propósito                     |
| -------------------------- | ------------------- | ----------------------------- |
| `finance_daily_ingestion`  | 21h30 UTC (Seg-Sex) | Ingestão de preços e macro    |
| `finance_dbt_pipeline`     | 22h00 UTC (Seg-Sex) | dbt run + test                |
| `finance_ml_pipeline`      | 02h00 UTC (Dom)     | Treino de modelos + previsões |
| `finance_model_monitoring` | 08h00 UTC (Diário)  | Detecção de drift             |
| `finance_macro_ingestion`  | 23h00 UTC (Diário)  | Indicadores FRED + BCB        |

---

## Serviços Docker

```bash
# Subir tudo
docker-compose up -d

# Acompanhar logs
docker-compose logs -f api
docker-compose logs -f airflow-scheduler

# Escalar workers
docker-compose up -d --scale airflow-worker=3

# Parar tudo
docker-compose down

# Reconstruir após alterações
docker-compose build api && docker-compose up -d api
```

---

## Banco de Dados

```sql
-- Schemas do PostgreSQL
raw.*           -- Bronze: ingestão bruta imutável
staging.*       -- Prata: views dbt (limpo, tipado)
intermediate.*  -- Prata: modelos dbt efêmeros
marts.*         -- Ouro: dimensões + fatos
analytics.*     -- Ouro: agregações de KPI
monitoring.*    -- Métricas de saúde do pipeline
snapshots.*     -- Histórico SCD Tipo 2
seeds.*         -- Dados de referência
```

---

## Integração com Power BI

1. Abra o Power BI Desktop → Obter Dados → PostgreSQL
2. Servidor: `localhost:5433`, Banco: `finance`
3. Selecione tabelas de `marts.*` e `analytics.*`
4. Use modo **Importação** para dados históricos (mais rápido)
5. Use **DirectQuery** para dados de mercado em tempo real

**Tabelas recomendadas para importar:**

- `marts.dim_empresa`
- `marts.dim_tempo`
- `marts.fato_cotacoes`
- `analytics.agg_retornos`
- `marts.fato_macro`

---

## Deploy

O projeto inclui configuração pronta para deploy no **Render** (`render.yaml`):

```bash
# A API sobe automaticamente via Docker no Render
# PostgreSQL gerenciado pelo próprio Render (plano free)
# Variáveis de ambiente injetadas automaticamente pelo render.yaml
```

Para o dashboard Streamlit, utilize o **Streamlit Community Cloud**:

1. Acesse [share.streamlit.io](https://share.streamlit.io)
2. Conecte o repositório GitHub
3. Defina o arquivo principal: `dashboards/streamlit/app.py`
4. Configure a variável `API_URL` apontando para a API no Render

---

## Estrutura do Projeto

```
finance/
├── app/                    Aplicação FastAPI
│   ├── core/               Config, banco, segurança, cache, logging
│   ├── api/routes/         Endpoints REST por domínio
│   ├── services/           Lógica de negócio + APIs externas
│   ├── repositories/       Camada de queries ao banco
│   ├── models/             Modelos ORM SQLAlchemy
│   └── schemas/            DTOs Pydantic
├── ml/                     Módulos de machine learning
│   ├── forecasting/        Prophet, ARIMA, LSTM
│   ├── classification/     XGBoost, LightGBM, RF
│   ├── anomaly_detection/  Isolation Forest
│   └── sentiment_analysis/ FinBERT NLP
├── dbt/                    Transformação de dados
│   └── models/             Camadas staging e marts
├── airflow/dags/           Orquestração de pipelines
├── dashboards/streamlit/   Dashboard executivo
├── docker/                 Dockerfiles por serviço
├── infra/                  CI/CD e configurações de infra
├── tests/                  Testes unitários, de API, ML e integração
└── database/               Scripts de inicialização do banco
```

---

## Fluxo de Desenvolvimento

```bash
# Formatar código
black app/ ml/ tests/
ruff check --fix app/ ml/

# Verificação de tipos
mypy app/ ml/

# Executar testes
pytest tests/ -v --cov=app --cov=ml

# Hooks de pré-commit
pre-commit run --all-files
```

---

## Roadmap

- [x] Pipeline ELT completo (yfinance + BCB + FRED)
- [x] Modelo dimensional dbt (star schema Kimball)
- [x] API REST com JWT + cache Redis
- [x] Previsão com Prophet + ARIMA
- [x] Detecção de anomalias com Isolation Forest
- [x] Análise de sentimento com FinBERT
- [x] Dashboard executivo com Streamlit
- [x] Stack completo via Docker Compose
- [x] Orquestração com DAGs do Airflow
- [x] Rastreamento de experimentos com MLflow
- [ ] Integração de dados de fundos CVM
- [ ] Previsão com LSTM / Transformer (v1.1)
- [ ] Otimização de portfólio (Markowitz + Black-Litterman)
- [ ] Precificação de opções (Black-Scholes)
- [ ] Feed de preços em tempo real via WebSocket
- [ ] Manifests Kubernetes para deploy
- [ ] Infraestrutura AWS com Terraform
- [ ] Camada de API GraphQL

---

## Licença

MIT License — consulte o arquivo LICENSE para mais detalhes.

---

_Desenvolvido com padrões enterprise para fintechs, bancos digitais, fundos de investimento e plataformas de análise quantitativa._

# Finance
# KingSide-Finance
# KingSide-Finance
# KingSide-Finance
