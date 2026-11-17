-- Calendar covering the TPC-H date range (orders 1992-01-01..1998-08-02, receipts to ~1998-12).
with spine as (
    {{ date_spine('1992-01-01', '1998-12-31') }}
)

select
    cast(date_day as date)                                  as date_day,
    cast(extract(year from date_day) as integer) * 10000
        + cast(extract(month from date_day) as integer) * 100
        + cast(extract(day from date_day) as integer)       as date_key,
    cast(extract(year from date_day) as integer)            as year_number,
    cast(extract(quarter from date_day) as integer)         as quarter_number,
    cast(extract(month from date_day) as integer)           as month_number,
    cast(extract(day from date_day) as integer)             as day_of_month,
    cast({{ dbt.date_trunc('month', 'date_day') }} as date) as month_start,
    dayofweek(date_day)                                     as day_of_week,  -- 0 = Sunday
    dayofweek(date_day) in (0, 6)                           as is_weekend
from spine
