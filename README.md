# warehouse-quality-gate

**A dbt contract that stops a bad batch before it becomes a wrong number.**

The sabotaged batch in this repo loads without a single error. It parses, the rows
land, and the warehouse reports revenue of **$4,905,051**; the clean batch reports
**$395,751**. No part of a plain pipeline objects.

The two batches are separate draws from the same generator, not the same rows with
edits applied. Almost all of the gap is one row: order 401 at **4,500,000**, in a batch
where no other order is above $900. Without it the sabotaged batch sums to $405,051.

The same batch run through the contract fails **12 tests**, and the mart is not rebuilt
from it — it keeps the last good run's numbers (see *Known limits*).

---

## Measured result

| | rows loaded | revenue reported | errors raised | tests failed |
|---|---|---|---|---|
| Plain load — clean batch | 900 | $395,751.28 | 0 | — |
| Plain load — sabotaged batch | 901 | **$4,905,051.18** | **0** | — |
| Contract — clean batch | 900 | $395,751.28 | 0 | **0 of 15** |
| Contract — sabotaged batch | 901 (raw table and staging view) | mart not rebuilt — still shows the last good run | 12 | **12 of 15** |

**12 planted defects, 12 caught. Zero false alarms on the clean batch.**

Reproduce both runs:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install dbt-core dbt-duckdb      # last checked with dbt-core 1.12.5, dbt-duckdb 1.11.0
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
| D2 | customers | customer 16 email arrived blank (the seed loader reads it as NULL) | `not_null` |
| D3 | customers | country `USA` instead of ISO-2 `US` | `accepted_values` |
| D4 | customers | `signup_date` 2027-06-01, in the future | `dbt_utils_not_in_future` (compares with today's date — from 2027-06-01 this one stops failing) |
| D5 | orders | order 101 references customer 99999, which does not exist | `relationships` |
| D6 | orders | order 201 amount is `-450.0` on an order that is not a refund | `non_negative` |
| D7 | orders | orders 301–302 switched to EUR while the mart still sums as USD | `accepted_values` on currency |
| D8 | orders | order 401 amount `4,500,000` — thousands of times any other order | `within_magnitude` (fixed ceiling 100,000 — see limits) |
| D9 | orders | status `Delivered` with a capital D — breaks exact-match filters | `accepted_values` on the **raw** value |
| D10 | orders | order 601 present twice — double revenue recognition | `unique` |
| D11 | orders | order 701 dated before the reporting window opens | `within_reporting_window` |
| D12 | orders | order 801 amount arrived empty (NULL); `SUM` silently skips it | `not_null` |

Two of these deserve a note, because they are the ones teams usually miss.

**D9 tests the raw value, not the normalised one.** It is tempting to `lower()` the
status in staging and test the clean column — but then the test can never fail, and
the downstream filter that does an exact match on `'delivered'` still silently drops
the row. The model exposes both `status_raw` and `status_normalised`, and the contract
tests `status_raw` — which is only trimmed, not untouched; see *Known limits*.

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

The warehouse here is DuckDB so the whole thing runs on a laptop. The staging models
use DuckDB SQL (`try_cast`, `cast(... as double)`); moving to another warehouse means
porting those, not only changing `profiles.yml`.

## Known limits (found in review, 2026-09-30)

- **The magnitude test only catches the absurd.** `within_magnitude` fails above
  100,000. A real cents-for-dollars slip multiplies an amount by 100; with orders
  under $900 that lands under 90,000 and **passes**. A unit error needs a relative
  check (against the column's own history), not a fixed ceiling.
- **"Not rebuilt" means stale.** When the contract fails, `fct_revenue_daily` keeps
  the last good run's numbers and nothing tells the reader. Pair the contract with a
  freshness check.
- **This repo breaks its own D9 rule.** `country` (and `currency` in orders) is tested
  after `upper(trim(...))`, so a lower-case `us` passes. And `status_raw` is
  `trim(status)`, not the raw value, so a status of `shipped ` with a trailing space
  passes the status test, while any query on the source table with an exact match
  still drops that row. Test the value as it arrived.
- **Volume is not checked.** An empty batch (with declared column types) passes all
  fifteen tests and builds an empty mart.

## Where this fits

Contracts stop bad data. They do not tell you a job never ran, or that a scraper
returned an empty page. Those are separate checks — see `pipeline-heartbeat` and
`scraper-canary`.
