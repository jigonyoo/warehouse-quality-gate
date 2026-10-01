"""What a plain load reports for each batch. (For what the contract reports, run
scripts/run_evidence.sh.)

This script sums the CSV rows the way an untested load would; the same sums come
out of the DuckDB raw tables that dbt seeds from these files. Nothing in that path
raises an error. That is the point: the sabotaged batch parses cleanly, lands, and
produces a revenue number nobody questions until it is compared with something else. The two batches are separate draws from
the same generator, not the same rows with edits, so their difference is not "the
cost of the defects" - most of it is one row.
"""
import csv, duckdb

def load(path):
    with open(path) as f:
        return list(csv.DictReader(f))

def naive_revenue(rows):
    """Sum the amount column the way an untested pipeline would: cast, coalesce, move on."""
    total, loaded = 0.0, 0
    for r in rows:
        try:
            total += float(r["amount"] or 0)
        except ValueError:
            pass
        loaded += 1
    return loaded, round(total, 2)

clean = load("seeds/raw_orders_clean.csv")
sab   = load("seeds/raw_orders_sabotaged.csv")

lc, rc = naive_revenue(clean)
ls, rs = naive_revenue(sab)

print("PLAIN LOAD - no contract, no tests")
print(f"  clean batch      rows loaded {lc:>5}   revenue reported ${rc:>14,.2f}   errors raised 0")
print(f"  sabotaged batch  rows loaded {ls:>5}   revenue reported ${rs:>14,.2f}   errors raised 0")
print(f"  difference       {ls-lc:+} rows        {rs-rc:+,.2f}   (two separate draws, not the same rows)")
amounts = []
for r in sab:
    try:
        amounts.append((float(r["amount"] or 0), r["order_id"]))
    except ValueError:
        pass
top, top_id = max(amounts)
print(f"  largest order in the sabotaged batch: {top_id} at ${top:,.2f}; "
      f"without it the batch sums to ${rs - top:,.2f}")
print()
print("  Both loads succeeded. Nothing in the plain path noticed a problem.")
