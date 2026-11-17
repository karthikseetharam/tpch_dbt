-- TPC-H Q1 (Pricing Summary Report), answered from the star schema.
-- Spec: l_shipdate <= date '1998-12-01' - interval '90' day  ->  1998-09-02.
select
    return_flag,
    line_status,
    sum(quantity)           as sum_qty,
    sum(extended_price)     as sum_base_price,
    sum(net_revenue)        as sum_disc_price,
    sum(gross_amount)       as sum_charge,
    avg(quantity)           as avg_qty,
    avg(extended_price)     as avg_price,
    avg(discount_rate)      as avg_disc,
    count(*)                as count_order
from {{ ref('fct_order_lines') }}
where ship_date <= cast('1998-09-02' as date)
group by return_flag, line_status
order by return_flag, line_status
