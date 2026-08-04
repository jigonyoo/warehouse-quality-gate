{% test within_reporting_window(model, column_name, start_date) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} < date '{{ start_date }}'
{% endtest %}
