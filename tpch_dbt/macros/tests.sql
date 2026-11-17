{# Generic test: every non-null value of column_name lies in [min_value, max_value]. #}
{% test column_between(model, column_name, min_value, max_value) %}
    select {{ column_name }}
    from {{ model }}
    where {{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }}
{% endtest %}

{# Generic test: the model has at least `min_rows` rows (catches silent empty loads). #}
{% test min_row_count(model, min_rows) %}
    select count(*) as row_count
    from {{ model }}
    having count(*) < {{ min_rows }}
{% endtest %}
