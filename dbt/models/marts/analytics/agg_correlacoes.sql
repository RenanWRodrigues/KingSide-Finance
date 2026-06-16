{{
    config(
        materialized='table',
        tags=['marts', 'analytics', 'correlation'],
        description='30-day rolling Pearson correlation between all ticker pairs — latest snapshot only'
    )
}}

with cotacoes as (
    select
        de.ticker,
        fc.data,
        round(
            (fc.fechamento_ajustado / nullif(
                lag(fc.fechamento_ajustado, 1) over (partition by fc.empresa_id order by fc.data),
                0
            ) - 1) * 100,
            6
        )                           as retorno_diario_pct
    from {{ ref('fato_cotacoes') }} fc
    inner join {{ ref('dim_empresa') }} de using (empresa_id)
    where fc.fechamento_ajustado > 0
      and fc.data >= current_date - interval '90 days'
),

-- Self-join to compute pairwise correlation on last 30 data points
pairs as (
    select distinct
        a.ticker   as ticker_a,
        b.ticker   as ticker_b
    from cotacoes a
    cross join cotacoes b
    where a.ticker < b.ticker   -- deduplicate: (A,B) only, not (B,A)
),

correlation_30d as (
    select
        p.ticker_a,
        p.ticker_b,
        count(*)                                                                as n_pontos,
        round(
            corr(a.retorno_diario_pct, b.retorno_diario_pct)::numeric,
            4
        )                                                                       as correlacao_pearson
    from pairs p
    inner join (
        select ticker, data, retorno_diario_pct
        from cotacoes
        where data >= current_date - interval '30 days'
          and retorno_diario_pct is not null
    ) a on a.ticker = p.ticker_a
    inner join (
        select ticker, data, retorno_diario_pct
        from cotacoes
        where data >= current_date - interval '30 days'
          and retorno_diario_pct is not null
    ) b on b.ticker = p.ticker_b and b.data = a.data
    group by p.ticker_a, p.ticker_b
    having count(*) >= 10   -- mínimo de 10 dias para correlação confiável
),

final as (
    select
        ticker_a,
        ticker_b,
        n_pontos,
        correlacao_pearson,
        case
            when correlacao_pearson >= 0.7  then 'alta_positiva'
            when correlacao_pearson >= 0.3  then 'moderada_positiva'
            when correlacao_pearson > -0.3  then 'baixa'
            when correlacao_pearson > -0.7  then 'moderada_negativa'
            else                                 'alta_negativa'
        end                                                                     as categoria,
        current_timestamp                                                       as updated_at
    from correlation_30d
)

select * from final
order by abs(correlacao_pearson) desc
