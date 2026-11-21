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
| F10 | transactions.date | Always parses; 2019 is a partial year | 0 parse failures (format `yyyy-MM-dd HH:mm:ss`); range 2010-01-01 to 2019-10-31; 2019 has 10 months at the same monthly rate as 2018 (~116k/month); steady growth, no gaps | Cast to timestamp; remember 2019 is partial when splitting by time for ML | fail if parse fails |
| F11 | fraud_labels | Labels cover ~67% of transactions evenly in every year; no year is entirely labeled or entirely unlabeled | Labeled share is 67.0% in each year 2010–2019 (e.g. 2010: 831,529 of 1,240,880 labeled, 409,351 unlabeled; 2019: 777,339 of 1,159,966 labeled) | Time-based ML split is possible (train older years, validate 2018, test 2019); the unlabeled third is a random holdout across all years, not future data | — |
| F12 | transactions.errors | 7 error types, sometimes combined; rows with errors are ~2.8× more likely to be fraud | Types: Insufficient Balance 131,621 · Bad PIN 32,482 · Technical Glitch 26,633 · Bad Card Number 7,925 · Bad Expiration 6,295 · Bad CVV 6,241 · Bad Zipcode 1,138. Fraud rate 0.401% with errors vs 0.145% without | Silver: split into an array column; gold/ML: one flag per error type + error_count | — |
| F13 | all foreign keys | Referential integrity holds across all 5 links | 0 orphans: txn.card_id→cards, txn.client_id→users, cards.client_id→users, txn.mcc→mcc, labels.transaction_id→txn. Check verified with a planted fake orphan (returned 1) | Silver: left joins are safe today, but keep an orphan check as a DQ expectation, because new monthly files may break it | — |
| F14 | transactions.client_id vs cards.client_id | Every transaction's client owns the card used | 13,305,915 rows joined (no loss), 0 mismatches | transactions.client_id is derivable from card_id; keep it in silver for convenience but treat cards as the source of truth. No "non-owner card" ML feature (it would always be 0). Keep as a DQ check in silver | — |
| F15 | users.num_credit_cards vs cards | Stated card count matches actual cards for every user | 2,000 users compared, all have ≥1 card, 0 mismatches | num_credit_cards is derivable from cards; in gold, compute it from cards, don't trust the stored copy. Keep as a DQ check | — |
| F16 | cards/users/labels categorical columns | Allowed values are clean; casing differs across files; one constant column | card_brand 4 values, card_type 3, has_chip YES/NO, gender Female/Male, is_fraud Yes/No (totals match). card_on_dark_web = "No" for all 6,146 cards | Silver: convert has_chip and is_fraud to boolean. Exclude card_on_dark_web (constant, no signal) and gender (protected attribute) from ML features | — |
| F17 | cards/users numeric columns | All parse cleanly; ranges mostly valid, with a few suspicious values; current_age is a ~2020 snapshot | 0 parse failures. credit_score 480–850 (valid), current_age 18–101, retirement_age 50–79, birth_year 1918–2002. 31 cards with $0 limit (26 credit, 3 debit, 2 prepaid). 8 users with yearly_income < $1,000 (min $1). birth_year + current_age = 2019 or 2020 for all users | Silver: flag $0-limit cards and income < $1,000 (don't fix). ML: compute age at transaction time from birth_year/birth_month; don't use current_age | — |
| F18 | cards dates vs transactions | Card dates parse cleanly; a few transactions fall outside the card's open/expiry window | expires Jul 1997–Dec 2024, acct_open_date Jan 1991–Feb 2020, 0 parse failures, 0 cards opened after expiry. 309 transactions before acct_open_date, 83 after expiry (month-end cutoff via add_months). Likely cause: cards file is a ~2020 snapshot holding current card details only | Silver: flag (don't drop) out-of-window transactions with a DQ flag. Open question: are these more often fraud? Check during feature work | — |
| F19 | users ranges, ID types, PII | Remaining ranges valid; all IDs cast to BIGINT; users holds PII | birth_month 1–12; latitude 20.88–61.2, longitude −159.41 to −68.67 (all US incl. Hawaii and Alaska); 0 BIGINT cast failures for labels.transaction_id, transactions.id, cards.id, users.id. PII columns: address, latitude, longitude, birth_year, birth_month | Silver: cast IDs to BIGINT. Governance: UC column masks on PII columns (v0.2/v0.3) | — |

## Open questions for the data owner

1. Which channel is correct for the 5,788 conflicting rows (F3)?
2. What do negative amounts at food and gas merchants represent (F7)?
3. What are the zero-amount transactions (F8)?

## Pending checks
- `errors` values
- Referential integrity across files
- Cards, users and labels validity