{{
    config(
        materialized='incremental',
        unique_key='order_line_key',
        on_schema_change='append_new_columns',
        cluster_by=['order_date'] if target.type == 'snowflake' else none
    )
}}

-- Central fact of the star schema. Grain: one row per order line.
-- Incremental: on re-runs only orders on/after the latest loaded order_date
-- (minus a 7-day look-back for late-arriving lines) are merged.
select
    order_line_key,
    order_key,
    line_number,
    customer_key,
    part_key,
    supplier_key,
    order_date,
    ship_date,
    commit_date,
    receipt_date,
    order_status,
    order_priority,
    return_flag,
    line_status,
    ship_mode,
    quantity,
    extended_price,
    discount_rate,
    tax_rate,
    discount_amount,
    net_revenue,
    gross_amount,
    supply_cost_amount,
    gross_margin,
    days_to_ship,
    days_late,
    is_late_delivery
from {{ ref('int_order_lines__enriched') }}

{% if is_incremental() %}
where order_date >= (
    select {{ dbt.dateadd('day', -7, 'max(order_date)') }} from {{ this }}
)
{% endif %}
