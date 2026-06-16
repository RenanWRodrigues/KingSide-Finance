{{
    config(
        materialized='table',
        tags=['marts', 'analytics', 'comparison'],
        description='Multi-period comparison metrics per ticker: return, CAGR, volatility, Sharpe, MaxDrawdown — latest snapshot'
    )
}}

with cotacoes as (
    select
        de.ticker,
        de.nome,
        de.setor,
        fc.data,
        fc.fechamento_ajustado
    from {{ ref('fato_cotacoes') }} fc
    inner join {{ ref('dim_empresa') }} de using (empresa_id)
    where fc.fechamento_ajustado > 0
),

with_returns as (
    select
        ticker,
        nome,
        setor,
        data,
        fechamento_ajustado,
        round(
            (fechamento_ajustado / nullif(lag(fechamento_ajustado, 1) over w, 0) - 1) * 100,
            6
        )                   as ret_1d,
        round(
            (fechamento_ajustado / nullif(lag(fechamento_ajustado, 21) over w, 0) - 1) * 100,
            4
        )                   as ret_1m,
        round(
            (fechamento_ajustado / nullif(lag(fechamento_ajustado, 63) over w, 0) - 1) * 100,
            4
        )                   as ret_3m,
        round(
            (fechamento_ajustado / nullif(lag(fechamento_ajustado, 126) over w, 0) - 1) * 100,
            4
        )                   as ret_6m,
        round(
            (fechamento_ajustado / nullif(lag(fechamento_ajustado, 252) over w, 0) - 1) * 100,
            4
        )                   as ret_1y,
        -- Volatilidade anualizada 252d
        round(
            stddev_pop(
                (fechamento_ajustado / nullif(lag(fechamento_ajustado, 1) over w, 0) - 1)
            ) over (partition by ticker order by data rows between 251 preceding and current row)
            * sqrt(252) * 100,
            2
        )                   as volatilidade_anual_pct,
        -- Drawdown corrente vs máximo 252d
        round(
            (fechamento_ajustado / nullif(
                max(fechamento_ajustado) over (
                    partition by ticker order by data rows between 251 preceding and current row
                ), 0
            ) - 1) * 100,
            2
        )                   as max_drawdown_252d_pct
    from cotacoes
    window w as (partition by ticker order by data)
),

latest as (
    select *
    from with_returns
    where data = (select max(data) from cotacoes)
),

sharpe as (
    select
        l.*,
        case
            when volatilidade_anual_pct > 0
            then round((ret_1y - 11.75) / nullif(volatilidade_anual_pct, 0), 4)
            else null
        end                 as sharpe_1y,
        -- Quintile rank by 1y return (within sector)
        ntile(5) over (partition by setor order by ret_1y nulls last)  as quintil_retorno_setor,
        -- Percentile rank globally
        round(
            percent_rank() over (order by ret_1y nulls last) * 100,
            1
        )                   as percentil_retorno_global
    from latest
)

select
    ticker,
    nome,
    setor,
    fechamento_ajustado                 as preco_atual,
    ret_1d                              as retorno_1d_pct,
    ret_1m                              as retorno_1m_pct,
    ret_3m                              as retorno_3m_pct,
    ret_6m                              as retorno_6m_pct,
    ret_1y                              as retorno_1y_pct,
    volatilidade_anual_pct,
    max_drawdown_252d_pct,
    sharpe_1y,
    quintil_retorno_setor,
    percentil_retorno_global,
    current_timestamp                   as updated_at
from sharpe
order by ret_1y desc nulls last
