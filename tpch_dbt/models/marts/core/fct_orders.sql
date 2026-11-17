-- Order-level fact, aggregated from order lines. Grain: one row per order.
with lines as (
    select
        order_key,
        count(*)                                    as line_count,
        sum(quantity)                               as total_quantity,
        sum(extended_price)                         as total_extended_price,
        sum(discount_amount)                        as total_discount,
        sum(net_revenue)                            as total_net_revenue,
        sum(gross_amount)                           as total_gross_amount,
        sum(gross_margin)                           as total_gross_margin,
        sum(case when is_late_delivery then 1 else 0 end) as late_line_count,
        max(receipt_date)                           as last_receipt_date
    from {{ ref('fct_order_lines') }}
    group by order_key
)

select
    orders.order_key,
    orders.customer_key,
    orders.order_date,
    orders.order_status,
    orders.order_priority,
    orders.clerk,
    orders.ship_priority,
    orders.total_price                              as reported_total_price,
    lines.line_count,
    lines.total_quantity,
    lines.total_extended_price,
    lines.total_discount,
    lines.total_net_revenue,
    lines.total_gross_amount,
    lines.total_gross_margin,
    lines.late_line_count,
    lines.late_line_count > 0                       as has_late_delivery,
    lines.last_receipt_date,
    {{ dbt.datediff('orders.order_date', 'lines.last_receipt_date', 'day') }} as days_to_fulfil
from {{ ref('stg_tpch__orders') }} as orders
inner join lines
    on orders.order_key = lines.order_key
