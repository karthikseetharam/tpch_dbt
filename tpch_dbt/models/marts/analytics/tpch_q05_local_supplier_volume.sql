-- TPC-H Q5 (Local Supplier Volume): 1994 revenue in ASIA where customer and supplier
-- share a nation.
select
    customer.nation_name,
    sum(lines.net_revenue)  as revenue
from {{ ref('fct_order_lines') }} as lines
inner join {{ ref('dim_customer') }} as customer
    on lines.customer_key = customer.customer_key
inner join {{ ref('dim_supplier') }} as supplier
    on lines.supplier_key = supplier.supplier_key
where customer.nation_key = supplier.nation_key
  and supplier.region_name = 'ASIA'
  and lines.order_date >= cast('1994-01-01' as date)
  and lines.order_date <  cast('1995-01-01' as date)
group by customer.nation_name
order by revenue desc
