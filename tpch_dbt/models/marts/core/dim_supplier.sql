select
    supplier.supplier_key,
    supplier.supplier_name,
    supplier.account_balance,
    geo.nation_key,
    geo.nation_name,
    geo.region_key,
    geo.region_name
from {{ ref('stg_tpch__supplier') }} as supplier
inner join {{ ref('int_geography') }} as geo
    on supplier.nation_key = geo.nation_key
