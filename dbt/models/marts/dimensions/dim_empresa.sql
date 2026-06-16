{{
    config(
        materialized='table',
        tags=['marts', 'dimensions'],
        description='Empresa dimension — SCD Type 1'
    )
}}

with empresas as (
    select * from {{ ref('stg_empresas') }}
),

enriched as (
    select
        empresa_id,
        ticker,
        nome,
        nome_completo,
        coalesce(setor, 'Não Classificado')     as setor,
        coalesce(subsetor, 'Não Classificado')  as subsetor,
        segmento,
        bolsa,
        pais,
        moeda,
        cnpj,
        site,
        ativo,
        loaded_at                               as created_at,
        loaded_at                               as updated_at

    from empresas
)

select * from enriched
