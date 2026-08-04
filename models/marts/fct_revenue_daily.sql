{{ config(materialized='table') }}

select
    order_date,
    currency,
    count(*)                as order_count,
    sum(amount)             as revenue
from {{ ref('stg_orders') }}
group by 1, 2
