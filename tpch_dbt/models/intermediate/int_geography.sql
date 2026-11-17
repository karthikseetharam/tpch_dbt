-- Nation with its region, reused by the customer and supplier dimensions.
select
    nation.nation_key,
    nation.nation_name,
    region.region_key,
    region.region_name
from {{ ref('stg_tpch__nation') }} as nation
inner join {{ ref('stg_tpch__region') }} as region
    on nation.region_key = region.region_key
