select
    p_partkey                               as part_key,
    p_name                                  as part_name,
    trim(p_mfgr)                            as manufacturer,
    trim(p_brand)                           as brand,
    trim(p_type)                            as part_type,
    p_size                                  as part_size,
    trim(p_container)                       as container,
    cast(p_retailprice as decimal(15, 2))   as retail_price,
    p_comment                               as part_comment
from {{ source('tpch', 'part') }}
