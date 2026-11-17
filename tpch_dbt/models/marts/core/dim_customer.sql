select
    customer.customer_key,
    customer.customer_name,
    customer.market_segment,
    customer.account_balance,
    geo.nation_key,
    geo.nation_name,
    geo.region_key,
    geo.region_name
from {{ ref('stg_tpch__customer') }} as customer
inner join {{ ref('int_geography') }} as geo
    on customer.nation_key = geo.nation_key
