{{
    config(
        materialized='table',
        tags=['marts', 'analytics'],
        description='Aggregated returns by ticker: 1d, 5d, 21d, 63d, 252d, YTD'
    )
}}

with cotacoes as (
    select
        fc.empresa_id,
        de.ticker,
        de.nome,
        de.setor,
        fc.data,
        fc.fechamento_ajustado
    from {{ ref('fato_cotacoes') }} fc
    inner join {{ ref('dim_empresa') }} de using (empresa_id)
    where fc.fechamento_ajustado > 0
),

with_lags as (
    select
        *,
        lag(fechamento_ajustado, 1)   over w   as preco_1d_atras,
        lag(fechamento_ajustado, 5)   over w   as preco_5d_atras,
        lag(fechamento_ajustado, 21)  over w   as preco_21d_atras,
        lag(fechamento_ajustado, 63)  over w   as preco_63d_atras,
        lag(fechamento_ajustado, 252) over w   as preco_252d_atras,
        first_value(fechamento_ajustado) over (
            partition by empresa_id, extract(year from data)
            order by data
        )                                      as preco_inicio_ano
    from cotacoes
    window w as (partition by empresa_id order by data)
),

retornos as (
    select
        empresa_id,
        ticker,
        nome,
        setor,
        data,
        fechamento_ajustado                                                              as preco_atual,
        round((fechamento_ajustado / nullif(preco_1d_atras,   0) - 1) * 100, 4)         as retorno_1d_pct,
        round((fechamento_ajustado / nullif(preco_5d_atras,   0) - 1) * 100, 4)         as retorno_5d_pct,
        round((fechamento_ajustado / nullif(preco_21d_atras,  0) - 1) * 100, 4)         as retorno_21d_pct,
        round((fechamento_ajustado / nullif(preco_63d_atras,  0) - 1) * 100, 4)         as retorno_63d_pct,
        round((fechamento_ajustado / nullif(preco_252d_atras, 0) - 1) * 100, 4)         as retorno_252d_pct,
        round((fechamento_ajustado / nullif(preco_inicio_ano, 0) - 1) * 100, 4)         as retorno_ytd_pct

    from with_lags
)

select * from retornos
where data = (select max(data) from cotacoes)
