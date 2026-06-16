{{
    config(
        materialized='view',
        tags=['staging', 'cotacoes'],
        description='Staging layer for raw price data from yfinance'
    )
}}

with source as (
    select * from {{ source('raw', 'cotacoes_raw') }}
),

renamed as (
    select
        -- identifiers
        {{ dbt_utils.generate_surrogate_key(['ticker', 'date']) }} as cotacao_id,
        upper(trim(ticker))                                         as ticker,

        -- dates
        cast(date as date)                                          as data,

        -- prices (BRL, adjusted)
        round(cast(open as numeric), 6)                             as abertura,
        round(cast(high as numeric), 6)                             as maxima,
        round(cast(low as numeric), 6)                              as minima,
        round(cast(close as numeric), 6)                            as fechamento,
        round(cast(adj_close as numeric), 6)                        as fechamento_ajustado,
        cast(volume as bigint)                                      as volume,

        -- derived
        round(
            (cast(close as numeric) - cast(open as numeric))
            / nullif(cast(open as numeric), 0),
            6
        )                                                           as variacao_dia,
        round(
            (cast(close as numeric) - cast(open as numeric))
            / nullif(cast(open as numeric), 0) * 100,
            4
        )                                                           as variacao_dia_pct,

        -- metadata
        cast(loaded_at as timestamp with time zone)                 as loaded_at,
        'yfinance'                                                  as fonte

    from source
    where
        close is not null
        and close > 0
        and date >= '{{ var("start_date") }}'
)

select * from renamed
