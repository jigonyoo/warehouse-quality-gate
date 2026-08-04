"""Generate a clean batch and a sabotaged batch of the same source data.

The sabotaged batch carries 12 planted defects. Each defect is the kind that a
plain load accepts without complaint - the file parses, the rows land, and the
totals are quietly wrong.
"""
import csv, os, random, datetime as dt

random.seed(20260804)
OUT = "seeds"
N_CUST, N_ORD = 120, 900
CURRENCIES = ["USD", "EUR", "GBP"]
STATUSES = ["placed", "shipped", "delivered", "returned"]

PLANTED = []          # (defect_id, table, description)

def note(did, table, desc):
    PLANTED.append({"defect_id": did, "table": table, "description": desc})

def customers(sabotage):
    rows = []
    for i in range(1, N_CUST + 1):
        rows.append({
            "customer_id": i,
            "email": f"user{i}@example.com",
            "country": random.choice(["US", "DE", "GB", "KR"]),
            "signup_date": (dt.date(2025, 1, 1) + dt.timedelta(days=random.randint(0, 500))).isoformat(),
        })
    if sabotage:
        rows.append(dict(rows[7]))                      # D1 duplicate primary key
        note("D1", "customers", "Duplicate customer_id 8 - a re-sent file loaded twice")
        rows[15]["email"] = ""                          # D2 empty required field
        note("D2", "customers", "customer 16 has an empty email, loaded as a blank string not NULL")
        rows[23]["country"] = "USA"                     # D3 enum drift
        note("D3", "customers", "country 'USA' instead of ISO-2 'US' - one upstream system changed format")
        rows[31]["signup_date"] = "2027-06-01"          # D4 future date
        note("D4", "customers", "signup_date in the future - a timezone bug upstream")
    return rows

def orders(sabotage, cust_ids):
    rows = []
    for i in range(1, N_ORD + 1):
        amt = round(random.uniform(12, 900), 2)
        rows.append({
            "order_id": i,
            "customer_id": random.choice(cust_ids),
            "order_date": (dt.date(2025, 6, 1) + dt.timedelta(days=random.randint(0, 400))).isoformat(),
            "status": random.choice(STATUSES),
            "currency": "USD",
            "amount": amt,
        })
    if sabotage:
        rows[100]["customer_id"] = 99999                # D5 orphan FK
        note("D5", "orders", "order 101 points at customer 99999 which does not exist")
        rows[200]["amount"] = -450.00                   # D6 negative amount
        note("D6", "orders", "order 201 has a negative amount with status 'placed'")
        rows[300]["currency"] = "EUR"                   # D7 silent currency switch
        rows[301]["currency"] = "EUR"
        note("D7", "orders", "orders 301-302 switched to EUR mid-file while the mart still sums as USD")
        rows[400]["amount"] = 4_500_000.00              # D8 magnitude outlier
        note("D8", "orders", "order 401 amount is 4.5M - a cents/dollars unit mix-up")
        rows[500]["status"] = "Delivered"               # D9 case drift in enum
        note("D9", "orders", "status 'Delivered' with a capital D - breaks exact-match filters")
        rows.append(dict(rows[600]))                    # D10 duplicate order
        note("D10", "orders", "order 601 appears twice - double revenue recognition")
        rows[700]["order_date"] = "2024-01-05"          # D11 out-of-window date
        note("D11", "orders", "order 701 dated before the reporting window opens")
        rows[800]["amount"] = ""                        # D12 empty numeric
        note("D12", "orders", "order 801 amount arrived empty and loads as 0")
    return rows

def write(name, rows, fields):
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/{name}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def build(sabotage, suffix):
    PLANTED.clear()
    c = customers(sabotage)
    o = orders(sabotage, [r["customer_id"] for r in c])
    write(f"raw_customers{suffix}", c, ["customer_id", "email", "country", "signup_date"])
    write(f"raw_orders{suffix}", o, ["order_id", "customer_id", "order_date", "status", "currency", "amount"])
    return list(PLANTED)

if __name__ == "__main__":
    build(False, "_clean")
    planted = build(True, "_sabotaged")
    with open("scripts/planted_defects.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["defect_id", "table", "description"])
        w.writeheader(); w.writerows(planted)
    print(f"clean + sabotaged batches written; {len(planted)} defects planted")
