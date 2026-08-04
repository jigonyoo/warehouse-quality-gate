{{ config(materialized='view') }}

select
    cast(customer_id as integer)          as customer_id,
    nullif(trim(email), '')               as email,
    upper(trim(country))                  as country,
    cast(signup_date as date)             as signup_date
from {{ ref(var('customers_seed')) }}
