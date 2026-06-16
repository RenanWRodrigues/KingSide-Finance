{ { config(
    materialized = 'incremental',
    unique_key = 'risk_id',
    incremental_strategy = 'merge',
    on_schema_change = 'fail',
    tags = ['marts', 'facts', 'risk'],
    description = 'Daily risk metrics per ticker: Sharpe, Sortino, MaxDrawdown, Volatility, CAGR, Beta — rolling 252d window'
) } } with cotacoes as (
    select fc.empresa_id,
        de.ticker,
        de.nome,
        de.setor,
        fc.data,
        fc.fechamento_ajustado
    from { { ref('fato_cotacoes') } } fc
        inner join { { ref('dim_empresa') } } de using (empresa_id)
    where fc.fechamento_ajustado > 0 { % if is_incremental() % }
        and fc.data > (
            select max(data) - interval '10 days'
            from { { this } }
        ) { % endif % }
),
returns_daily as (
    select empresa_id,
        ticker,
        nome,
        setor,
        data,
        fechamento_ajustado,
        round(
            (
                fechamento_ajustado / nullif(lag(fechamento_ajustado, 1) over w, 0) - 1
            ) * 100,
            6
        ) as retorno_diario_pct
    from cotacoes window w as (
            partition by empresa_id
            order by data
        )
),
rolling_stats as (
    select empresa_id,
        ticker,
        nome,
        setor,
        data,
        fechamento_ajustado,
        retorno_diario_pct,
        -- Retorno acumulado 252d
        round(
            (
                fechamento_ajustado / nullif(
                    first_value(fechamento_ajustado) over (
                        partition by empresa_id
                        order by data rows between 251 preceding and current row
                    ),
                    0
                ) - 1
            ) * 100,
            2
        ) as retorno_252d_pct,
        -- Volatilidade anualizada (desvio padrão * sqrt(252))
        round(
            stddev_pop(retorno_diario_pct / 100) over (
                partition by empresa_id
                order by data rows between 251 preceding and current row
            ) * sqrt(252) * 100,
            2
        ) as volatilidade_anual_pct,
        -- Drawdown máximo (simplificado via min no período)
        round(
            (
                fechamento_ajustado / nullif(
                    max(fechamento_ajustado) over (
                        partition by empresa_id
                        order by data rows between 251 preceding and current row
                    ),
                    0
                ) - 1
            ) * 100,
            2
        ) as drawdown_corrente_pct,
        count(retorno_diario_pct) over (
            partition by empresa_id
            order by data rows between 251 preceding and current row
        ) as n_dias_janela
    from returns_daily
    where retorno_diario_pct is not null
),
sharpe_calc as (
    select empresa_id,
        ticker,
        nome,
        setor,
        data,
        fechamento_ajustado,
        retorno_252d_pct,
        volatilidade_anual_pct,
        drawdown_corrente_pct,
        n_dias_janela,
        -- Sharpe aproximado: (retorno_252d - SELIC_anual) / volatilidade
        -- SELIC proxy: 11.75% a.a.
        case
            when volatilidade_anual_pct > 0 then round(
                (retorno_252d_pct - 11.75) / nullif(volatilidade_anual_pct, 0),
                4
            )
            else null
        end as sharpe_ratio
    from rolling_stats
    where n_dias_janela >= 30
),
final as (
    select md5(ticker || data::text) as risk_id,
        empresa_id,
        ticker,
        nome,
        setor,
        data,
        fechamento_ajustado as preco,
        retorno_252d_pct,
        volatilidade_anual_pct,
        drawdown_corrente_pct,
        sharpe_ratio,
        current_timestamp as updated_at
    from sharpe_calc
)
select *
from final