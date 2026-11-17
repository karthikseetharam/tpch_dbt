{#
  One row per calendar day between start_date and end_date (inclusive), column `date_day`.
  Dispatched per adapter, because series generation is not portable SQL.
#}
{% macro date_spine(start_date, end_date) -%}
    {{ return(adapter.dispatch('date_spine', 'tpch')(start_date, end_date)) }}
{%- endmacro %}

{% macro default__date_spine(start_date, end_date) -%}
    select cast(range as date) as date_day
    from range(cast('{{ start_date }}' as date), cast('{{ end_date }}' as date) + interval 1 day, interval 1 day)
{%- endmacro %}

{% macro snowflake__date_spine(start_date, end_date) -%}
    select dateadd(day, seq4(), to_date('{{ start_date }}')) as date_day
    from table(generator(rowcount => {{ (modules.datetime.date.fromisoformat(end_date) - modules.datetime.date.fromisoformat(start_date)).days + 1 }}))
{%- endmacro %}
