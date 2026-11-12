---
status: accepted
date: 2026-11-11
deciders: Yajushi Garg
---

# ADR-0005: Drop card verification codes (CVV) at ingestion

**Summary (Y-statement):** In the context of loading card data into a bronze layer that normally keeps source data as-is, facing PCI DSS rules that forbid storing card verification codes, I decided to drop the CVV column during the cards load, before anything is written to Delta, and against keeping it in bronze, masking it or tokenising it, to ensure CVV never exists in any table or table history, accepting that bronze is not a perfectly complete copy of the source file.

## Context and Problem Statement
The medallion design treats bronze as a raw copy of the source, so history can be reprocessed. The cards file includes a `cvv` column. PCI DSS prohibits storing card verification codes after authorisation, even if encrypted, and the column has no analytical value. If CVV were written to a Delta table and removed later, time travel would keep older versions containing it until VACUUM removed them. The decision is where in the pipeline CVV is removed.

## Decision Drivers
* Compliance: CVV must never be stored (PCI DSS)
* No trace in table history: removing a column after writing does not erase it from time travel
* Bronze should stay as close to the source as possible
* The rule should be enforced automatically, not just documented

## Considered Options
* Drop CVV during the cards load, before bronze
* Load CVV into bronze, drop it in silver
* Mask CVV in bronze
* Hash or tokenise CVV in bronze

## Decision Outcome
Chosen option: "Drop CVV during the cards load", because it is the only option where CVV never exists in any Delta table or its history. The COPY INTO statement selects every column except `cvv`. This is a deliberate, documented exception to "bronze is raw as-is"; all other columns remain unchanged.

Enforcement:
* A test fails if a `cvv` column ever appears in `bronze.cards` (W1-5).
* Break it (W1-4): try to select `cvv` from `bronze.cards`; the query must fail.

### Consequences
* Good, because CVV never enters Delta tables, so no time-travel versions or table backups contain it.
* Good, because the rule is enforced by a test, not just by documentation.
* Bad, because bronze is no longer a complete copy of the source file; reprocessing can never restore CVV (which is intended).
* Bad, because the raw source file in the landing zone still contains CVV (see Risk and Compliance).

## Risk and Compliance
* Card data (PCI): **known limitation**: the raw `cards_data.csv` in the landing volume (dev), the ADLS landing container (prod) and the local `data/` folder still contains CVV. Mitigations: landing storage readable only by the pipeline service principal and engineers; delete or archive source files after successful ingestion; local data never committed to Git. In a real bank the upstream system would not send CVV at all.
* Privacy / PII: `card_number` remains in bronze and is masked later (W3-2).
* Access and retention: the bronze schema is readable only by the pipeline identity and data engineers; analysts read gold only.

## Pros and Cons of the Options
### Drop CVV during the cards load
* Good, because CVV never exists in any table or table history.
* Good, because it is simple: the load selects every column except `cvv`.
* Bad, because bronze differs from the source file by one column.

### Load into bronze, drop in silver
* Good, because bronze stays a complete copy of the source.
* Bad, because CVV is stored in a table, breaking PCI rules, and stays in time-travel history until VACUUM.

### Mask CVV in bronze
* Good, because most users would not see the value.
* Bad, because the real value is still stored; masking controls display, not storage.

### Hash or tokenise CVV
* Good, because the raw value is not directly readable.
* Bad, because PCI forbids storing CVV even in protected form, and a 3-digit value is easy to reverse from a hash.

## Revisit
If the source system is changed to stop sending CVV, remove the column exclusion and record that the upstream fix replaced this decision.