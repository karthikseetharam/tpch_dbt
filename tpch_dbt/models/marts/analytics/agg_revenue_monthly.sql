-- Monthly revenue by customer region and market segment; feeds the dashboard.
select
    dates.month_start,
    dates.year_number,
    customer.region_name,
    customer.market_segment,
    count(distinct lines.order_key)                         as order_count,
    sum(lines.quantity)                                     as units,
    sum(lines.net_revenue)                                  as net_revenue,
    sum(lines.gross_margin)                                 as gross_margin,
    avg(case when lines.is_late_delivery then 1.0 else 0.0 end) as late_delivery_rate
from {{ ref('fct_order_lines') }} as lines
inner join {{ ref('dim_date') }} as dates
    on lines.order_date = dates.date_day
inner join {{ ref('dim_customer') }} as customer
    on lines.customer_key = customer.customer_key
group by dates.month_start, dates.year_number, customer.region_name, customer.market_segment
