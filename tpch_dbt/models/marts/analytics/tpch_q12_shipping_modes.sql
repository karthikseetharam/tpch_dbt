-- TPC-H Q12 (Shipping Modes and Order Priority): late MAIL/SHIP lines received in 1994,
-- split by high vs low order priority.
select
    ship_mode,
    sum(case when order_priority in ('1-URGENT', '2-HIGH') then 1 else 0 end)     as high_line_count,
    sum(case when order_priority not in ('1-URGENT', '2-HIGH') then 1 else 0 end) as low_line_count
from {{ ref('fct_order_lines') }}
where ship_mode in ('MAIL', 'SHIP')
  and commit_date < receipt_date
  and ship_date < commit_date
  and receipt_date >= cast('1994-01-01' as date)
  and receipt_date <  cast('1995-01-01' as date)
group by ship_mode
order by ship_mode
