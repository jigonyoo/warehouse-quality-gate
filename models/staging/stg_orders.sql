{{ config(materialized='view') }}

select
    cast(order_id as integer)                          as order_id,
    cast(customer_id as integer)                       as customer_id,
    cast(order_date as date)                           as order_date,
    lower(trim(status))                                as status_normalised,
    trim(status)                                       as status_raw,
    upper(trim(currency))                              as currency,
    try_cast(nullif(trim(cast(amount as varchar)), '') as double) as amount
from {{ ref(var('orders_seed')) }}
