"""What a plain load reports, next to what the contract reports.

Neither run raises an error at load time. That is the point: the sabotaged batch
parses cleanly, lands in the warehouse, and produces a revenue number that looks
entirely reasonable until you compare it with the truth.
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
print(f"  difference       {ls-lc:+} rows        {rs-rc:+,.2f}  ({(rs-rc)/rc*100:+.1f}%)")
print()
print("  Both loads succeeded. Nothing in the plain path noticed a problem.")
