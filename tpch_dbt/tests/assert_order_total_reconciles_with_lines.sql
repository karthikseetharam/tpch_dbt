-- The source system's o_totalprice must equal the sum of line gross amounts
-- (extendedprice * (1 - discount) * (1 + tax)). dbgen rounds each line to cents twice
-- (after discount, after tax), so a line can drift by up to ~0.02; observed max at
-- SF 0.1 is 0.0201 for a 1-line order and 0.107 for a 7-line order.
select
    order_key,
    line_count,
    reported_total_price,
    total_gross_amount
from {{ ref('fct_orders') }}
where abs(reported_total_price - total_gross_amount) > 0.02 * line_count + 0.01
