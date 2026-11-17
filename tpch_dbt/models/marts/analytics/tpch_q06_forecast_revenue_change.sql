-- TPC-H Q6 (Forecasting Revenue Change): revenue gained by removing 0.05-0.07 discounts
-- on small 1994 orders.
select
    sum(discount_amount) as revenue
from {{ ref('fct_order_lines') }}
where ship_date >= cast('1994-01-01' as date)
  and ship_date <  cast('1995-01-01' as date)
  and discount_rate between 0.05 and 0.07
  and quantity < 24
