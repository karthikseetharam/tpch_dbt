with supply as (
    select
        part_key,
        count(*)                as supplier_count,
        min(supply_cost)        as min_supply_cost,
        avg(supply_cost)        as avg_supply_cost,
        sum(available_quantity) as total_available_quantity
    from {{ ref('stg_tpch__partsupp') }}
    group by part_key
)

select
    part.part_key,
    part.part_name,
    part.manufacturer,
    part.brand,
    part.part_type,
    part.part_size,
    part.container,
    part.retail_price,
    supply.supplier_count,
    supply.min_supply_cost,
    supply.avg_supply_cost,
    supply.total_available_quantity
from {{ ref('stg_tpch__part') }} as part
left join supply
    on part.part_key = supply.part_key
