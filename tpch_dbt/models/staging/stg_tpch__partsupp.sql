select
    ps_partkey                              as part_key,
    ps_suppkey                              as supplier_key,
    ps_availqty                             as available_quantity,
    cast(ps_supplycost as decimal(15, 2))   as supply_cost,
    ps_comment                              as partsupp_comment
from {{ source('tpch', 'partsupp') }}
