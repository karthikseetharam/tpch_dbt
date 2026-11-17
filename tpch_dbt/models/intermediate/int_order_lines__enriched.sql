-- Order lines joined to their order header, with the standard TPC-H revenue measures.
with lines as (
    select * from {{ ref('stg_tpch__lineitem') }}
),

orders as (
    select * from {{ ref('stg_tpch__orders') }}
),

partsupp as (
    select * from {{ ref('stg_tpch__partsupp') }}
)

select
    lines.order_key * 10 + lines.line_number                    as order_line_key,
    lines.order_key,
    lines.line_number,
    orders.customer_key,
    lines.part_key,
    lines.supplier_key,
    orders.order_date,
    lines.ship_date,
    lines.commit_date,
    lines.receipt_date,
    orders.order_status,
    orders.order_priority,
    lines.return_flag,
    lines.line_status,
    lines.ship_mode,
    lines.ship_instructions,
    lines.quantity,
    lines.extended_price,
    lines.discount_rate,
    lines.tax_rate,
    lines.extended_price * lines.discount_rate                  as discount_amount,
    lines.extended_price * (1 - lines.discount_rate)            as net_revenue,
    lines.extended_price * (1 - lines.discount_rate) * (1 + lines.tax_rate)
                                                                as gross_amount,
    partsupp.supply_cost * lines.quantity                       as supply_cost_amount,
    lines.extended_price * (1 - lines.discount_rate)
        - partsupp.supply_cost * lines.quantity                 as gross_margin,
    {{ dbt.datediff('orders.order_date', 'lines.ship_date', 'day') }}       as days_to_ship,
    {{ dbt.datediff('lines.commit_date', 'lines.receipt_date', 'day') }}    as days_late,
    lines.receipt_date > lines.commit_date                      as is_late_delivery
from lines
inner join orders
    on lines.order_key = orders.order_key
inner join partsupp
    on lines.part_key = partsupp.part_key
   and lines.supplier_key = partsupp.supplier_key
