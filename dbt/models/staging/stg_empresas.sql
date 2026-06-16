{{
    config(
        materialized='view',
        tags=['staging', 'empresas']
    )
}}

with source as (
    select * from {{ source('raw', 'empresas_raw') }}
),

cleaned as (
    select
        {{ dbt_utils.generate_surrogate_key(['ticker']) }}  as empresa_id,
        upper(trim(ticker))                                 as ticker,
        trim(nome)                                          as nome,
        trim(nome_completo)                                 as nome_completo,
        trim(setor)                                         as setor,
        trim(subsetor)                                      as subsetor,
        trim(segmento)                                      as segmento,
        coalesce(trim(bolsa), 'B3')                         as bolsa,
        coalesce(trim(pais), 'Brasil')                      as pais,
        coalesce(trim(moeda), 'BRL')                        as moeda,
        trim(cnpj)                                          as cnpj,
        trim(site)                                          as site,
        true                                                as ativo,
        cast(loaded_at as timestamp with time zone)         as loaded_at

    from source
    where
        ticker is not null
        and nome is not null
)

select * from cleaned
