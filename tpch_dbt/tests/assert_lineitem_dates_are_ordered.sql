-- A line cannot ship before it was ordered, nor be received before it shipped.
select order_line_key, order_date, ship_date, receipt_date
from {{ ref('fct_order_lines') }}
where ship_date < order_date
   or receipt_date < ship_date
