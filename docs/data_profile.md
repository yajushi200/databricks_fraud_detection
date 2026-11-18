# Data Profile

**Scope:** all five source files, profiled on the full data in Databricks (`notebooks/01_profile.py`).
**Date:** Nov 17–18, 2026
**Purpose:** every finding leads to an action in silver; data quality rules in W2-2 trace back to this file.

## Row counts

| Source | Rows | Unique keys | Duplicates |
|---|---|---|---|
| transactions | 13,305,915 | 13,305,915 | 0 |
| cards | 6,146 | 6,146 | 0 |
| users | 2,000 | 2,000 | 0 |
| fraud_labels | 8,914,963 | 8,914,963 | 0 |
| mcc | 109 | 109 | 0 |

No duplicate keys in any source today. Silver still deduplicates, as protection against reruns and future file overlaps.

## Findings

| # | Column | Finding | Evidence | Silver action | Rule level |
|---|---|---|---|---|---|
| F1 | transactions.errors | Mostly empty but not useless | Filled in 211,393 rows (1.6%) | Keep; split into flags; candidate fraud feature | — |
| F2 | transactions.merchant_city | "ONLINE" is a placeholder for online merchants, not a city | All 1,557,912 online rows have city "ONLINE", no state, no zip | Derive `is_online`; treat "ONLINE" as a channel in gold | — |
| F3 | use_chip vs merchant_city | Channel conflict: chip transactions at online merchants | 5,788 rows from 4 merchants; their other 26,226 transactions are all online, 0 swipes | Keep rows; add `channel_conflict` flag | warn |
| F4 | transactions.merchant_state | Mixes US state codes with foreign country names | Rows with state but no zip are all countries (Mexico 27,401, Canada 10,647, …) | Split into `merchant_country` and `merchant_state`; add `is_international` | — |
| F5 | transactions.zip | Missing only where expected | 1,652,706 missing = 1,563,700 online + 89,006 foreign; 0 US rows missing | Store as 5-character text (currently decimal, e.g. 58523.0) | — |
| F6 | transactions.amount | Text with "$", but always parses | 0 parse failures; range −$500.00 to $6,820.20 | Cast to decimal(12,2) | fail if parse fails |
| F7 | transactions.amount | Negative amounts are common and mostly not refunds | 660,049 negative (~5%); ~88% at food stores (5499) and gas stations (5541); floor exactly −$500 (176 rows) | Keep; add `is_credit` flag; don't treat as errors | — |
| F8 | transactions.amount | Zero amounts exist | 10,639 rows | Keep; flag for review | warn |
| F9 | mcc lookup | Dataset's MCC descriptions differ from the official standard for 3xxx codes | e.g. 3504 = "Gardening Supplies" | Use the provided lookup in this project; note the deviation | — |

## Open questions for the data owner

1. Which channel is correct for the 5,788 conflicting rows (F3)?
2. What do negative amounts at food and gas merchants represent (F7)?
3. What are the zero-amount transactions (F8)?

## Pending checks

- Dates: parsing, range, rows per year
- `errors` values
- Referential integrity across files
- Cards, users and labels validity