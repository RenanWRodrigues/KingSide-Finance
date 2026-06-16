{{
    config(
        materialized='incremental',
        unique_key='cotacao_id',
        incremental_strategy='merge',
        on_schema_change='fail',
        tags=['marts', 'facts', 'cotacoes'],
        description='Daily OHLCV price fact table — incremental merge on cotacao_id'
    )
}}

with cotacoes as (
    select * from {{ ref('stg_cotacoes') }}

    {% if is_incremental() %}
        where loaded_at > (select max(loaded_at) from {{ this }})
    {% endif %}
),

dim_empresa as (
    select empresa_id, ticker from {{ ref('dim_empresa') }}
),

fato as (
    select
        c.cotacao_id,
        e.empresa_id,
        c.data,
        c.abertura,
        c.maxima,
        c.minima,
        c.fechamento,
        c.fechamento_ajustado,
        c.volume,
        round(
            cast(c.volume as numeric) * c.fechamento_ajustado,
            2
        )                                   as volume_financeiro,
        c.variacao_dia,
        c.variacao_dia_pct,
        c.fonte,
        c.loaded_at                         as created_at,
        current_timestamp                   as updated_at

    from cotacoes c
    inner join dim_empresa e using (ticker)
)

select * from fato
