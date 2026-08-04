#!/usr/bin/env bash
# Runs both batches through the same contract and records the outcome.
set -uo pipefail
export DBT_PROFILES_DIR=.
mkdir -p evidence

run () {
  local label=$1 cust=$2 ord=$3
  dbt build --vars "{\"customers_seed\":\"$cust\",\"orders_seed\":\"$ord\"}" \
    > "evidence/${label}.log" 2>&1
  local line
  line=$(grep -E "^.*Done\. PASS=" "evidence/${label}.log" | tail -1)
  echo "${label}: ${line##*Done. }"
  grep -oE "FAIL 1 [a-z_0-9]+" "evidence/${label}.log" | sed 's/FAIL 1 //' | sort > "evidence/${label}_failed_tests.txt"
}

run clean     raw_customers_clean     raw_orders_clean
run sabotaged raw_customers_sabotaged raw_orders_sabotaged

echo
echo "tests that failed on the sabotaged batch:"
cat evidence/sabotaged_failed_tests.txt | sed 's/^/  /'
echo
echo "tests that failed on the clean batch: $(wc -l < evidence/clean_failed_tests.txt)"
