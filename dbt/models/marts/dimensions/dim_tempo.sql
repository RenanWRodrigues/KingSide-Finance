{{
    config(
        materialized='table',
        tags=['marts', 'dimensions'],
        description='Date dimension — full calendar from start_date to today+1y'
    )
}}

with date_spine as (
    {{
        dbt_utils.date_spine(
            datepart="day",
            start_date="cast('" ~ var('start_date') ~ "' as date)",
            end_date="cast(current_date + interval '365 days' as date)"
        )
    }}
),

feriados_br as (
    select cast(data as date) as data
    from {{ ref('seed_feriados_brasil') }}
),

dim as (
    select
        cast(date_day as date)                                   as data,
        extract(year  from date_day)::int                        as ano,
        extract(month from date_day)::int                        as mes,
        extract(day   from date_day)::int                        as dia,
        extract(quarter from date_day)::int                      as trimestre,
        extract(week  from date_day)::int                        as semana_ano,
        extract(isodow from date_day)::int                       as dia_semana,
        to_char(date_day, 'TMDay')                               as nome_dia_semana,
        to_char(date_day, 'TMMonth')                             as nome_mes,
        extract(isodow from date_day) not in (6, 7)              as eh_dia_util,
        f.data is not null                                       as eh_feriado,
        null::varchar                                            as nome_feriado

    from date_spine d
    left join feriados_br f on cast(d.date_day as date) = f.data
)

select * from dim
