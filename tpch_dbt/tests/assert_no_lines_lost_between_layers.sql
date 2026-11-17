-- Every staged line item must reach the fact table (joins must not drop rows).
select staged.line_count, fact.line_count
from (select count(*) as line_count from {{ ref('stg_tpch__lineitem') }}) as staged
cross join (select count(*) as line_count from {{ ref('fct_order_lines') }}) as fact
where staged.line_count <> fact.line_count
