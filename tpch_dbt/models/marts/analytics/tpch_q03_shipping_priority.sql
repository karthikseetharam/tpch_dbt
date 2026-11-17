-- TPC-H Q3 (Shipping Priority): top 10 unshipped BUILDING orders by revenue as of 1995-03-15.
select
    lines.order_key,
    sum(lines.net_revenue)  as revenue,
    orders.order_date,
    orders.ship_priority
from {{ ref('fct_order_lines') }} as lines
inner join {{ ref('fct_orders') }} as orders
    on lines.order_key = orders.order_key
inner join {{ ref('dim_customer') }} as customer
    on lines.customer_key = customer.customer_key
where customer.market_segment = 'BUILDING'
  and orders.order_date < cast('1995-03-15' as date)
  and lines.ship_date > cast('1995-03-15' as date)
group by lines.order_key, orders.order_date, orders.ship_priority
order by revenue desc, orders.order_date
limit 10
