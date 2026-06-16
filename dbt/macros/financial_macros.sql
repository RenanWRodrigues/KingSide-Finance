{% macro calcular_rsi(preco_col, window=14) %}
with changes as (
    select
        *,
        {{ preco_col }} - lag({{ preco_col }}) over (partition by empresa_id order by data) as delta
    from {{ this }}
),
gains_losses as (
    select
        *,
        case when delta > 0 then delta else 0 end as gain,
        case when delta < 0 then abs(delta) else 0 end as loss
    from changes
),
avg_gl as (
    select
        *,
        avg(gain) over (partition by empresa_id order by data rows {{ window - 1 }} preceding) as avg_gain,
        avg(loss) over (partition by empresa_id order by data rows {{ window - 1 }} preceding) as avg_loss
    from gains_losses
)
select
    *,
    round(100 - 100 / (1 + avg_gain / nullif(avg_loss, 0)), 2) as rsi_{{ window }}
from avg_gl
{% endmacro %}


{% macro calcular_bollinger(preco_col, window=20, num_std=2) %}
    avg({{ preco_col }}) over (partition by empresa_id order by data rows {{ window - 1 }} preceding)
        as bb_media_{{ window }},
    avg({{ preco_col }}) over (partition by empresa_id order by data rows {{ window - 1 }} preceding)
        + {{ num_std }} * stddev({{ preco_col }}) over (partition by empresa_id order by data rows {{ window - 1 }} preceding)
        as bb_upper_{{ window }},
    avg({{ preco_col }}) over (partition by empresa_id order by data rows {{ window - 1 }} preceding)
        - {{ num_std }} * stddev({{ preco_col }}) over (partition by empresa_id order by data rows {{ window - 1 }} preceding)
        as bb_lower_{{ window }}
{% endmacro %}


{% macro calcular_macd(preco_col, fast=12, slow=26, signal=9) %}
    -- EMA-based MACD (approximate via window functions)
    avg({{ preco_col }}) over (partition by empresa_id order by data rows {{ fast - 1 }} preceding)
        - avg({{ preco_col }}) over (partition by empresa_id order by data rows {{ slow - 1 }} preceding)
        as macd_line
{% endmacro %}


{% macro render_period_filter(date_col, periods) %}
    {% if periods == '1y' %}
        {{ date_col }} >= current_date - interval '1 year'
    {% elif periods == '6m' %}
        {{ date_col }} >= current_date - interval '6 months'
    {% elif periods == '3m' %}
        {{ date_col }} >= current_date - interval '3 months'
    {% elif periods == 'ytd' %}
        {{ date_col }} >= date_trunc('year', current_date)
    {% else %}
        1 = 1
    {% endif %}
{% endmacro %}


{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
