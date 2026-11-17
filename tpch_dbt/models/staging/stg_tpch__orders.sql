select
    o_orderkey                              as order_key,
    o_custkey                               as customer_key,
    o_orderstatus                           as order_status_code,
    case o_orderstatus
        when 'F' then 'fulfilled'
        when 'O' then 'open'
        when 'P' then 'partial'
    end                                     as order_status,
    cast(o_totalprice as decimal(15, 2))    as total_price,
    cast(o_orderdate as date)               as order_date,
    trim(o_orderpriority)                   as order_priority,
    trim(o_clerk)                           as clerk,
    o_shippriority                          as ship_priority,
    o_comment                               as order_comment
from {{ source('tpch', 'orders') }}
