select
    l_orderkey                                  as order_key,
    l_linenumber                                as line_number,
    l_partkey                                   as part_key,
    l_suppkey                                   as supplier_key,
    cast(l_quantity as decimal(15, 2))          as quantity,
    cast(l_extendedprice as decimal(15, 2))     as extended_price,
    cast(l_discount as decimal(15, 2))          as discount_rate,
    cast(l_tax as decimal(15, 2))               as tax_rate,
    l_returnflag                                as return_flag,
    l_linestatus                                as line_status,
    cast(l_shipdate as date)                    as ship_date,
    cast(l_commitdate as date)                  as commit_date,
    cast(l_receiptdate as date)                 as receipt_date,
    trim(l_shipinstruct)                        as ship_instructions,
    trim(l_shipmode)                            as ship_mode,
    l_comment                                   as line_comment
from {{ source('tpch', 'lineitem') }}
