# warehouse-quality-gate

**A dbt contract that stops a bad batch before it becomes a wrong number.**

The sabotaged batch in this repo loads without a single error. It parses, the rows
land, and the warehouse reports revenue of **$4,905,051** instead of **$395,751** —
a **1,139% overstatement** that no part of a plain pipeline objects to.

The same batch run through the contract fails **12 tests** and never reaches the mart.

---

## Measured result

| | rows loaded | revenue reported | errors raised | tests failed |
|---|---|---|---|---|
| Plain load — clean batch | 900 | $395,751.28 | 0 | — |
| Plain load — sabotaged batch | 901 | **$4,905,051.18** | **0** | — |
| Contract — clean batch | 900 | $395,751.28 | 0 | **0 of 15** |
| Contract — sabotaged batch | *blocked* | *not built* | 12 | **12 of 15** |

**12 planted defects, 12 caught. Zero false alarms on the clean batch.**

Reproduce both runs:

```bash
pip install dbt-core dbt-duckdb
python3 scripts/make_batches.py     # regenerates both batches, seed is fixed
./scripts/run_evidence.sh           # runs the contract over each, writes evidence/
python3 scripts/naive_vs_gate.py    # shows what a plain load reports instead
```

---

## The 12 planted defects

Each one is a defect that survives a plain load. None of them throw.

| # | Table | What arrived | Caught by |
|---|---|---|---|
| D1 | customers | `customer_id` 8 duplicated — a re-sent file loaded twice | `unique` |
| D2 | customers | customer 16 email arrived as `""`, not NULL | `not_null` (blank cast to NULL in staging) |
| D3 | customers | country `USA` instead of ISO-2 `US` | `accepted_values` |
| D4 | customers | `signup_date` in 2027 — an upstream timezone bug | `dbt_utils_not_in_future` |
| D5 | orders | order 101 references customer 99999, which does not exist | `relationships` |
| D6 | orders | order 201 amount is `-450.00` with status `placed` | `non_negative` |
| D7 | orders | orders 301–302 switched to EUR while the mart still sums as USD | `accepted_values` on currency |
| D8 | orders | order 401 amount `4,500,000` — a cents/dollars unit mix-up | `within_magnitude` |
| D9 | orders | status `Delivered` with a capital D — breaks exact-match filters | `accepted_values` on the **raw** value |
| D10 | orders | order 601 present twice — double revenue recognition | `unique` |
| D11 | orders | order 701 dated before the reporting window opens | `within_reporting_window` |
| D12 | orders | order 801 amount arrived empty and loads as `0` | `not_null` (empty cast to NULL) |

Two of these deserve a note, because they are the ones teams usually miss.

**D9 tests the raw value, not the normalised one.** It is tempting to `lower()` the
status in staging and test the clean column — but then the test can never fail, and
the downstream filter that does an exact match on `'delivered'` still silently drops
the row. The model exposes both `status_raw` and `status_normalised`; the contract
tests the raw one.

**D7 is a contract, not a bug.** Nothing is wrong with an EUR order. What is wrong is
that `fct_revenue_daily` sums `amount` without conversion, so mixing currencies makes
the total meaningless. The single-currency rule is written down as a test precisely
because the assumption lives in a model somewhere else.

---

## How it is put together

```
models/
  staging/
    stg_customers.sql      typed, trimmed, blanks cast to NULL
    stg_orders.sql         keeps status_raw alongside status_normalised
    schema.yml             the contract itself, in plain YAML
  marts/
    fct_revenue_daily.sql  the number a stakeholder actually reads
tests/generic/
  non_negative.sql
  within_magnitude.sql
  within_reporting_window.sql
  dbt_utils_not_in_future.sql
scripts/
  make_batches.py          deterministic generator, seed 20260804
  naive_vs_gate.py         what a plain load reports instead
  run_evidence.sh          reruns both batches, writes evidence/
```

The warehouse here is DuckDB so the whole thing runs on a laptop in under a second.
The contract is ordinary dbt — moving it to Snowflake, BigQuery or Postgres is a
change of `profiles.yml`, not a change of tests.

## Where this fits

Contracts stop bad data. They do not tell you a job never ran, or that a scraper
returned an empty page. Those are separate checks — see `pipeline-heartbeat` and
`scraper-canary`.
