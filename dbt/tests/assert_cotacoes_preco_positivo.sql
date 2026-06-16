-- Test: All closing prices must be positive
select count(*) as n_violations
from {{ ref('fato_cotacoes') }}
where fechamento <= 0
   or fechamento_ajustado <= 0
having count(*) > 0
