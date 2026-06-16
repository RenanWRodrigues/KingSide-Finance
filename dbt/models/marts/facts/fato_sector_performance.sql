{{
    config(
        materialized='table',
        tags=['marts', 'facts', 'sector'],
        description='Daily sector-level performance aggregates: avg return, avg volatility, best/worst ticker per sector'
    )
}}

with retornos as (
    select * from {{ ref('agg_retornos') }}
),

setor_agg as (
    select
        setor,
        data,
        count(distinct ticker)                                                  as total_ativos,
        round(avg(retorno_1d_pct), 4)                                           as retorno_medio_1d_pct,
        round(avg(retorno_5d_pct), 4)                                           as retorno_medio_5d_pct,
        round(avg(retorno_21d_pct), 4)                                          as retorno_medio_21d_pct,
        round(avg(retorno_252d_pct), 4)                                         as retorno_medio_252d_pct,
        round(avg(retorno_ytd_pct), 4)                                          as retorno_medio_ytd_pct,
        max(retorno_1d_pct)                                                     as melhor_retorno_1d,
        min(retorno_1d_pct)                                                     as pior_retorno_1d
    from retornos
    where setor is not null
    group by setor, data
),

best_worst as (
    select
        r.setor,
        r.data,
        max(case when r.retorno_1d_pct = s.melhor_retorno_1d then r.ticker end) as melhor_ticker_1d,
        max(case when r.retorno_1d_pct = s.pior_retorno_1d  then r.ticker end) as pior_ticker_1d
    from retornos r
    inner join setor_agg s using (setor, data)
    where r.setor is not null
    group by r.setor, r.data
),

final as (
    select
        s.setor,
        s.data,
        s.total_ativos,
        s.retorno_medio_1d_pct,
        s.retorno_medio_5d_pct,
        s.retorno_medio_21d_pct,
        s.retorno_medio_252d_pct,
        s.retorno_medio_ytd_pct,
        s.melhor_retorno_1d,
        s.pior_retorno_1d,
        bw.melhor_ticker_1d,
        bw.pior_ticker_1d,
        current_timestamp                                                        as updated_at
    from setor_agg s
    left join best_worst bw using (setor, data)
)

select * from final
order by data desc, retorno_medio_1d_pct desc
