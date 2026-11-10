# Data Inventory

**Source:** Kaggle, "Financial Transactions Dataset: Analytics", created by CaixaBank Tech for their 2024 AI Hackathon
**Inspected:** Nov 10, 2026, locally (first rows plus Python checks). Data types and measured checks are decided in W1-3 profiling (Databricks).
**Status legend:** 🔍 to verify in profiling

## Overview

| File | Format | Size (MB) | One row = | Key | Links |
|---|---|---|---|---|---|
| transactions_data.csv | CSV | 1.17GB | one card purchase | `id` | `client_id` → users, `card_id` → cards, `mcc` → mcc_codes |
| cards_data.csv | CSV | 498KB | one card | `id` | `client_id` → users |
| users_data.csv | CSV | 161KB | one customer | `id` | referenced by transactions and cards as `client_id` |
| mcc_codes.json | JSON (dictionary) | 4.6KB | one merchant category code | code | referenced by transactions `mcc` |
| train_fraud_labels.json | JSON (nested under `"target"`) | 152MB | one transaction's fraud label | transaction id | → transactions `id` |

> Sizes: run `Get-ChildItem data | Select-Object Name, Length` and divide by 1,000,000.

## Relationships

- One **customer** has many **cards** (e.g. client 825 has at least 4 cards). ✅
- One **card** has many **transactions**. 🔍
- Each **transaction** has one **merchant category** (MCC). 🔍
- Only some **transactions** have a **fraud label**. ✅
- Naming is inconsistent: users call the key `id`; other files call it `client_id`. Rename it to `client_id` in silver.

## Key numbers

| Measure | Value | Status |
|---|---|---|
| Total transactions | 13,305,915 
| Labeled transactions | 8,914,963 |
| Fraud (`Yes`) | 13,332 | 
| Not fraud (`No`) | 8,901,631 | 
| Fraud rate (of labeled) | ≈ 0.15% (about 1 in 670) | 
| Unlabeled transactions | 4,390,952|
| MCC codes | 109 | 
| Date range | 2010–2019 | per dataset description; first row is 2010-01-01; check the last row 🔍 |

**Why this matters:** fraud is only 0.15% of labeled transactions, so accuracy is misleading. A model that always says "not fraud" scores 99.85%. Use recall, precision and PR-AUC instead. Unlabeled rows are **unknown**, not "not fraud".

---

## transactions_data.csv

| Column | Example | Meaning | Sensitive? | Notes |
|---|---|---|---|---|
| id | 7475327 | transaction ID | no | key |
| date | 2010-01-01 00:01:00 | when it happened | no | no time zone given |
| client_id | 1556 | customer | no | link to users |
| card_id | 2972 | card used | no | link to cards |
| amount | $-77.00 | amount spent | no | text with `$`; negatives probably refunds 🔍 |
| use_chip | Swipe Transaction | how the card was used | no | list all distinct values 🔍 |
| merchant_id | 59935 | merchant | no | future `dim_merchant` |
| merchant_city | Beulah | merchant city | no | |
| merchant_state | ND | merchant state | no | check what online purchases look like 🔍 |
| zip | 58523.0 | merchant zip | no | stored as decimal, so leading zeros are lost (e.g. 02134) |
| mcc | 5499 | merchant category | no | number here but text in mcc_codes, so convert before joining |
| errors | (empty) | transaction errors | no | mostly empty; check fill rate and values 🔍 |

## cards_data.csv

| Column | Example | Meaning | Sensitive? | Notes |
|---|---|---|---|---|
| id | 4524 | card ID | no | key |
| client_id | 825 | card owner | no | link to users |
| card_brand | Visa | network | no | |
| card_type | Debit | debit / credit (/ prepaid?) | no | list distinct values 🔍 |
| card_number | 4344676511950444 | full card number | **yes (card data)** | **mask** to last 4 digits |
| expires | 12/2022 | expiry month | no | text `MM/YYYY` |
| cvv | 623 | security code | **yes (card data)** | **drop in silver**; card security rules forbid storing it |
| has_chip | YES | chip present | no | `YES`/`NO` text |
| num_cards_issued | 2 | cards issued on account | no | |
| credit_limit | $24295 | credit limit | no | text with `$`; check what it means for debit cards 🔍 |
| acct_open_date | 09/2002 | account opened | no | text `MM/YYYY` |
| year_pin_last_changed | 2008 | PIN change year | no | |
| card_on_dark_web | No | card found on dark web | no | check if any `Yes` exist 🔍 |

## users_data.csv

| Column | Example | Meaning | Sensitive? | Notes |
|---|---|---|---|---|
| id | 825 | customer ID | no | key; rename to `client_id` |
| current_age | 53 | age today | yes (personal) | **today's** age, not at transaction time; use `birth_year` |
| retirement_age | 66 | expected retirement age | no | likely not useful for fraud |
| birth_year | 1966 | birth year | yes (personal) | |
| birth_month | 11 | birth month | yes (personal) | |
| gender | Female | gender | **yes (protected)** | don't use as a model feature (fairness) |
| address | 462 Rose Lane | home address | **yes (PII)** | mask |
| latitude | 34.15 | home location | **yes (PII)** | mask or round |
| longitude | -117.76 | home location | **yes (PII)** | mask or round |
| per_capita_income | $29278 | area income | **yes (financial)** | text with `$` |
| yearly_income | $59696 | customer income | **yes (financial)** | text with `$`; mask for analysts |
| total_debt | $127613 | customer debt | **yes (financial)** | text with `$` |
| credit_score | 787 | credit score | **yes (financial)** | |
| num_credit_cards | 5 | cards held | no | compare with cards file count 🔍 |

## mcc_codes.json

| Field | Example | Meaning | Notes |
|---|---|---|---|
| key | "5812" | MCC code | stored as **text** |
| value | Eating Places and Restaurants | category description | 109 entries  |

## train_fraud_labels.json

| Field | Example | Meaning | Notes |
|---|---|---|---|
| key (inside `"target"`) | "10649266" | transaction ID | stored as **text**; nested, so flatten into rows |
| value | "No" | fraud label | `"Yes"`/`"No"` text |

---

## Sensitive data summary

| Action | Columns |
|---|---|
| **Drop in silver** | cards.cvv |
| **Mask** | cards.card_number (last 4), users.address, users.latitude, users.longitude |
| **Restrict to approved groups** | users.yearly_income, users.total_debt, users.credit_score, users.per_capita_income, users.birth_year, users.birth_month, users.current_age |
| **Exclude from model features** | users.gender |

## Some factors tht might lead to a positive fraud
1. an amount much bigger than this card’s normal spending
2. many transactions in a short time
3. a merchant this card has never used
4. risky categories like wire transfers
5. online purchases
6. errors such as a bad PIN
7. a card found on the dark web

## Questions for profiling (W1-3)

1. Are negative amounts refunds? Do they share a card and merchant with an earlier positive amount?
2. What are all the values of `use_chip`, and how is an online purchase shown (merchant city, state, zip)?
3. How often is `errors` filled, and what values appear?
4. Does every `client_id` and `card_id` in transactions exist in users and cards?
5. Does every `mcc` in transactions exist in mcc_codes?
6. Does every transaction id in the labels exist in transactions?
7. What's the real date range and the row count per year? Any missing months?
8. Are there duplicate transaction ids?
9. Does `num_credit_cards` match the actual card count per customer?
10. Do any cards have `card_on_dark_web = Yes`?
