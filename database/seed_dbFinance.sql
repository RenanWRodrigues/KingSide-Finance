-- ============================================================
-- Finance — Seed Data para dbFinance
-- Popula todas as camadas: raw → marts → monitoring
-- ============================================================

-- ─────────────────────────────────────────────────────────
-- 1. raw.empresas_raw  (10 maiores empresas da B3)
-- ─────────────────────────────────────────────────────────

INSERT INTO raw.empresas_raw (ticker, nome, nome_completo, setor, subsetor, segmento, bolsa, pais, moeda, cnpj, site)
VALUES
  ('PETR4', 'Petrobras PN',       'Petróleo Brasileiro S.A. - Petrobras',    'Petróleo, Gás e Biocombustíveis', 'Petróleo e Gás',                'Integradas',                      'B3', 'Brasil', 'BRL', '33.000.167/0001-01', 'https://www.petrobras.com.br'),
  ('VALE3', 'Vale ON',            'Vale S.A.',                               'Materiais Básicos',               'Mineração',                     'Minerais Metálicos',              'B3', 'Brasil', 'BRL', '33.592.510/0001-54', 'https://www.vale.com'),
  ('ITUB4', 'Itaú Unibanco PN',   'Itaú Unibanco Holding S.A.',              'Financeiro',                      'Bancos',                        'Bancos Diversificados',           'B3', 'Brasil', 'BRL', '60.872.504/0001-23', 'https://www.itau.com.br'),
  ('BBDC4', 'Bradesco PN',        'Banco Bradesco S.A.',                     'Financeiro',                      'Bancos',                        'Bancos Diversificados',           'B3', 'Brasil', 'BRL', '60.746.948/0001-12', 'https://www.bradesco.com.br'),
  ('ABEV3', 'Ambev ON',           'Ambev S.A.',                              'Consumo não Cíclico',             'Bebidas',                       'Cervejas e Refrigerantes',        'B3', 'Brasil', 'BRL', '07.526.557/0001-00', 'https://www.ambev.com.br'),
  ('WEGE3', 'WEG ON',             'WEG S.A.',                                'Bens Industriais',                'Máquinas e Equipamentos',       'Motores, Compressores e Outros',  'B3', 'Brasil', 'BRL', '84.429.695/0001-11', 'https://www.weg.net'),
  ('B3SA3', 'B3 ON',              'B3 S.A. - Brasil, Bolsa, Balcão',         'Financeiro',                      'Serviços Financeiros Diversos', 'Serviços Financeiros Diversos',   'B3', 'Brasil', 'BRL', '09.346.601/0001-25', 'https://www.b3.com.br'),
  ('RENT3', 'Localiza ON',        'Localiza Rent a Car S.A.',                'Consumo Cíclico',                 'Veículos e Peças',              'Aluguel de Carros',               'B3', 'Brasil', 'BRL', '16.670.085/0001-55', 'https://www.localiza.com'),
  ('LREN3', 'Lojas Renner ON',    'Lojas Renner S.A.',                       'Consumo Cíclico',                 'Comércio',                      'Tecidos, Vestuário e Calçados',   'B3', 'Brasil', 'BRL', '92.754.738/0001-62', 'https://www.lojasrenner.com.br'),
  ('MGLU3', 'Magazine Luiza ON',  'Magazine Luiza S.A.',                     'Consumo Cíclico',                 'Comércio',                      'Eletrodomésticos',                'B3', 'Brasil', 'BRL', '47.960.950/0001-21', 'https://www.magazineluiza.com.br')
ON CONFLICT (ticker) DO NOTHING;

-- ─────────────────────────────────────────────────────────
-- 2. raw.cotacoes_raw  (90 dias úteis por ticker)
--    Preços simulados com random walk deterministico
-- ─────────────────────────────────────────────────────────

WITH params AS (
  SELECT ticker, base_price, drift
  FROM (VALUES
    ('PETR4', 37.50::NUMERIC, 0.0006::NUMERIC),
    ('VALE3', 65.00::NUMERIC, 0.0004::NUMERIC),
    ('ITUB4', 28.50::NUMERIC, 0.0005::NUMERIC),
    ('BBDC4', 14.00::NUMERIC, 0.0003::NUMERIC),
    ('ABEV3', 11.20::NUMERIC, 0.0002::NUMERIC),
    ('WEGE3', 42.00::NUMERIC, 0.0008::NUMERIC),
    ('B3SA3', 12.50::NUMERIC, 0.0004::NUMERIC),
    ('RENT3', 45.00::NUMERIC, 0.0006::NUMERIC),
    ('LREN3', 17.50::NUMERIC, 0.0003::NUMERIC),
    ('MGLU3',  9.50::NUMERIC, 0.0009::NUMERIC)
  ) AS t(ticker, base_price, drift)
),
biz_dates AS (
  SELECT
    d::DATE                                     AS dt,
    ROW_NUMBER() OVER (ORDER BY d) - 1          AS day_n
  FROM generate_series(
    CURRENT_DATE - INTERVAL '130 days',
    CURRENT_DATE,
    '1 day'
  ) d
  WHERE EXTRACT(DOW FROM d) NOT IN (0, 6)
  ORDER BY d
  LIMIT 90
),
prices AS (
  SELECT
    p.ticker,
    b.dt                                        AS date,
    GREATEST(0.01,
      p.base_price
      * (1 + p.drift * b.day_n)
      * (1 + (hashtext(p.ticker || b.dt::TEXT) % 400)::NUMERIC / 10000)
    )                                           AS close_p,
    0.015::NUMERIC                              AS intra_vol
  FROM params p CROSS JOIN biz_dates b
)
INSERT INTO raw.cotacoes_raw (ticker, date, open, high, low, close, adj_close, volume)
SELECT
  ticker,
  date,
  ROUND(close_p * (1 - intra_vol * 0.4), 6)    AS open,
  ROUND(close_p * (1 + intra_vol),       6)    AS high,
  ROUND(close_p * (1 - intra_vol),       6)    AS low,
  ROUND(close_p,                         6)    AS close,
  ROUND(close_p,                         6)    AS adj_close,
  (ABS(hashtext(ticker || date::TEXT)) % 15000000 + 1000000)::BIGINT AS volume
FROM prices
ON CONFLICT (ticker, date) DO NOTHING;

-- ─────────────────────────────────────────────────────────
-- 3. raw.macro_raw  (SELIC, IPCA, Câmbio — últimos 3 anos)
-- ─────────────────────────────────────────────────────────

INSERT INTO raw.macro_raw (indicador, data, valor, fonte)
SELECT
  i.indicador,
  m::DATE                                             AS data,
  ROUND(i.base + (ABS(hashtext(i.indicador || m::TEXT)) % i.range_cents)::NUMERIC / 100.0, 4) AS valor,
  'BCB/SGS'                                           AS fonte
FROM generate_series(
  DATE_TRUNC('month', CURRENT_DATE - INTERVAL '3 years'),
  DATE_TRUNC('month', CURRENT_DATE),
  '1 month'
) m
CROSS JOIN (VALUES
  ('selic',        0.79::NUMERIC, 29::INT),  -- 0.79% a 1.08% a.m.
  ('ipca',         0.05::NUMERIC, 78::INT),  -- 0.05% a 0.83% a.m.
  ('cambio_dolar', 4.85::NUMERIC, 65::INT)   -- 4.85 a 5.50 R$/USD
) AS i(indicador, base, range_cents)
ON CONFLICT (indicador, data) DO NOTHING;

-- ─────────────────────────────────────────────────────────
-- 4. raw.noticias_raw  (amostra)
-- ─────────────────────────────────────────────────────────

INSERT INTO raw.noticias_raw (ticker, titulo, resumo, fonte, url, publicado_em, sentimento)
VALUES
  ('PETR4', 'Petrobras anuncia pagamento de dividendos bilionários',
   'A Petrobras confirmou distribuição de R$ 14 bi em dividendos para o próximo trimestre, superando as expectativas do mercado.',
   'InfoMoney', 'https://www.infomoney.com.br/mercados/petrobras-dividendos',
   NOW() - INTERVAL '3 days', 0.8200),

  ('VALE3', 'Vale registra queda na produção de minério de ferro no trimestre',
   'Produção ficou 4,5% abaixo do guidance devido a chuvas intensas na região Norte do país.',
   'Valor Econômico', 'https://www.valor.com.br/empresas/vale-producao',
   NOW() - INTERVAL '5 days', -0.4100),

  ('ITUB4', 'Itaú supera expectativas com lucro de R$ 9,8 bi',
   'O banco reportou crescimento de 15% no lucro líquido, impulsionado pela expansão de crédito e seguros.',
   'Exame', 'https://www.exame.com/invest/itau-resultado',
   NOW() - INTERVAL '7 days', 0.7500),

  ('BBDC4', 'Bradesco eleva guidance de crédito para 10–13% em 2025',
   'O banco revisa projeções para cima após desempenho acima do esperado no primeiro semestre.',
   'Broadcast', 'https://www.broadcast.com.br/bradesco-guidance',
   NOW() - INTERVAL '2 days', 0.6300),

  ('ABEV3', 'Ambev reporta queda de 3% no volume de vendas no Brasil',
   'Volumes domésticos pressionados pelo reajuste de preços e pela concorrência no segmento de cervejas.',
   'Reuters Brasil', 'https://www.reuters.com/brasil/ambev-volume',
   NOW() - INTERVAL '10 days', -0.3800),

  ('WEGE3', 'WEG expande operações na Europa com aquisição de €280 mi',
   'A companhia anunciou compra de fabricante europeia de motores de alta eficiência, reforçando presença global.',
   'Folha de S.Paulo', 'https://www.folha.uol.com.br/mercado/weg-europa',
   NOW() - INTERVAL '1 day', 0.8900),

  ('B3SA3', 'Volume financeiro da B3 cresce 12% no primeiro semestre',
   'Bolsa registrou aumento no número de investidores ativos e no ADV de contratos de derivativos.',
   'Estadão', 'https://www.estadao.com.br/economia/b3-volume',
   NOW() - INTERVAL '4 days', 0.5500),

  ('RENT3', 'Localiza expande frota e melhora margens acima do consenso',
   'Empresa atingiu 350 mil veículos em frota com margem EBITDA de 42%, superando estimativas dos analistas.',
   'InfoMoney', 'https://www.infomoney.com.br/localiza-resultado',
   NOW() - INTERVAL '6 days', 0.7100),

  ('LREN3', 'Lojas Renner acelera digitalização; vendas online crescem 28%',
   'Canal digital já representa 22% das vendas totais com melhora no ticket médio e na retenção de clientes.',
   'NeoFeed', 'https://www.neofeed.com.br/lren3-digital',
   NOW() - INTERVAL '8 days', 0.6400),

  ('MGLU3', 'Magazine Luiza anuncia reestruturação e fechamento de 50 lojas',
   'Varejista vai reduzir quadro em 8% e concentrar investimentos no canal digital para melhorar rentabilidade.',
   'Bloomberg Brasil', 'https://www.bloomberg.com.br/mglu3-reestruturacao',
   NOW() - INTERVAL '12 days', -0.5200);

-- ─────────────────────────────────────────────────────────
-- 5. marts.dim_tempo  (2020-01-01 → 2026-12-31)
-- ─────────────────────────────────────────────────────────

INSERT INTO marts.dim_tempo
  (data, ano, mes, dia, trimestre, semana_ano, dia_semana, nome_dia_semana, nome_mes, eh_dia_util, eh_feriado)
SELECT
  d::DATE,
  EXTRACT(YEAR    FROM d)::INT,
  EXTRACT(MONTH   FROM d)::INT,
  EXTRACT(DAY     FROM d)::INT,
  EXTRACT(QUARTER FROM d)::INT,
  EXTRACT(WEEK    FROM d)::INT,
  EXTRACT(DOW     FROM d)::INT,
  TO_CHAR(d, 'TMDay'),
  TO_CHAR(d, 'TMMonth'),
  EXTRACT(DOW FROM d) NOT IN (0, 6),
  FALSE
FROM generate_series('2020-01-01'::DATE, '2026-12-31'::DATE, '1 day') d
ON CONFLICT (data) DO NOTHING;

-- Feriados nacionais 2024–2026
UPDATE marts.dim_tempo
SET eh_feriado = TRUE, eh_dia_util = FALSE
WHERE data IN (
  -- 2024
  '2024-01-01','2024-02-12','2024-02-13','2024-03-29','2024-04-21',
  '2024-05-01','2024-05-30','2024-09-07','2024-10-12','2024-11-02',
  '2024-11-15','2024-11-20','2024-12-25',
  -- 2025
  '2025-01-01','2025-03-03','2025-03-04','2025-04-18','2025-04-21',
  '2025-05-01','2025-06-19','2025-09-07','2025-10-12','2025-11-02',
  '2025-11-15','2025-11-20','2025-12-25',
  -- 2026
  '2026-01-01','2026-02-16','2026-02-17','2026-04-03','2026-04-21',
  '2026-05-01','2026-06-04','2026-09-07','2026-10-12','2026-11-02',
  '2026-11-15','2026-11-20','2026-12-25'
);

-- ─────────────────────────────────────────────────────────
-- 6. marts.dim_empresa  (promovido de raw.empresas_raw)
-- ─────────────────────────────────────────────────────────

INSERT INTO marts.dim_empresa
  (ticker, nome, nome_completo, setor, subsetor, segmento, bolsa, pais, moeda, cnpj, site, ativo)
SELECT
  ticker, nome, nome_completo, setor, subsetor, segmento, bolsa, pais, moeda, cnpj, site, TRUE
FROM raw.empresas_raw
ON CONFLICT (ticker) DO UPDATE
  SET nome        = EXCLUDED.nome,
      setor       = EXCLUDED.setor,
      updated_at  = NOW();

-- ─────────────────────────────────────────────────────────
-- 7. marts.fatos_cotacoes  (raw → marts via join com dims)
-- ─────────────────────────────────────────────────────────

INSERT INTO marts.fatos_cotacoes
  (empresa_id, data, abertura, maxima, minima, fechamento,
   fechamento_ajustado, volume, variacao_dia, variacao_dia_pct)
WITH ranked AS (
  SELECT
    c.ticker,
    c.date,
    c.open,
    c.high,
    c.low,
    c.close,
    c.adj_close,
    c.volume,
    c.close - LAG(c.close) OVER (PARTITION BY c.ticker ORDER BY c.date)
      AS variacao_dia,
    CASE
      WHEN LAG(c.close) OVER (PARTITION BY c.ticker ORDER BY c.date) IS NULL THEN NULL
      ELSE ROUND(
        (c.close - LAG(c.close) OVER (PARTITION BY c.ticker ORDER BY c.date))
        / LAG(c.close) OVER (PARTITION BY c.ticker ORDER BY c.date) * 100, 6)
    END AS variacao_dia_pct
  FROM raw.cotacoes_raw c
)
SELECT
  e.id,
  r.date,
  r.open,
  r.high,
  r.low,
  r.close,
  r.adj_close,
  r.volume,
  r.variacao_dia,
  r.variacao_dia_pct
FROM ranked r
JOIN marts.dim_empresa e ON e.ticker = r.ticker
WHERE EXISTS (SELECT 1 FROM marts.dim_tempo t WHERE t.data = r.date)
ON CONFLICT (empresa_id, data) DO NOTHING;

-- ─────────────────────────────────────────────────────────
-- 8. marts.fatos_macro  (raw → marts)
-- ─────────────────────────────────────────────────────────

INSERT INTO marts.fatos_macro (indicador, data, valor, fonte, pais, descricao, unidade)
SELECT
  m.indicador,
  m.data,
  m.valor,
  m.fonte,
  'Brasil',
  d.descricao,
  d.unidade
FROM raw.macro_raw m
JOIN (VALUES
  ('selic',        'Taxa SELIC – taxa básica de juros da economia brasileira', '% a.m.'),
  ('ipca',         'IPCA – Índice Nacional de Preços ao Consumidor Amplo',     '% a.m.'),
  ('cambio_dolar', 'Taxa de câmbio comercial – venda (R$/US$)',                'R$/US$')
) AS d(indicador, descricao, unidade) ON d.indicador = m.indicador
ON CONFLICT (indicador, data) DO NOTHING;

-- ─────────────────────────────────────────────────────────
-- 9. monitoring.pipeline_runs  (histórico de execuções)
-- ─────────────────────────────────────────────────────────

INSERT INTO monitoring.pipeline_runs (pipeline, status, started_at, finished_at, rows_loaded, metadata)
VALUES
  ('ingestao_cotacoes',  'success', NOW()-INTERVAL '26 hours',  NOW()-INTERVAL '25 hours 47 minutes',  900, '{"tickers": 10, "source": "yfinance"}'),
  ('ingestao_macro',     'success', NOW()-INTERVAL '25 hours',  NOW()-INTERVAL '24 hours 57 minutes',   36, '{"indicadores": ["selic","ipca","cambio_dolar"], "source": "BCB/SGS"}'),
  ('ingestao_noticias',  'success', NOW()-INTERVAL '24 hours',  NOW()-INTERVAL '23 hours 58 minutes',   10, '{"source": "NewsAPI", "tickers": 10}'),
  ('dbt_run',            'success', NOW()-INTERVAL '23 hours',  NOW()-INTERVAL '22 hours 52 minutes',  936, '{"models": 12, "tests": 24, "warnings": 0}'),
  ('ml_scoring',         'success', NOW()-INTERVAL '22 hours',  NOW()-INTERVAL '21 hours 48 minutes',   10, '{"model": "xgboost", "version": "v1.2.0", "mape": 3.8}'),
  ('ingestao_cotacoes',  'success', NOW()-INTERVAL '50 hours',  NOW()-INTERVAL '49 hours 48 minutes',  900, '{"tickers": 10, "source": "yfinance"}'),
  ('ingestao_macro',     'success', NOW()-INTERVAL '49 hours',  NOW()-INTERVAL '48 hours 56 minutes',   36, '{"indicadores": ["selic","ipca","cambio_dolar"], "source": "BCB/SGS"}'),
  ('ingestao_noticias',  'failed',  NOW()-INTERVAL '48 hours',  NOW()-INTERVAL '47 hours 59 minutes',    0, '{"error": "NewsAPI rate limit exceeded", "retry": false}'),
  ('dbt_run',            'success', NOW()-INTERVAL '47 hours',  NOW()-INTERVAL '46 hours 51 minutes',  936, '{"models": 12, "tests": 24, "warnings": 1}'),
  ('ingestao_cotacoes',  'success', NOW()-INTERVAL '74 hours',  NOW()-INTERVAL '73 hours 46 minutes',  900, '{"tickers": 10, "source": "yfinance"}');
