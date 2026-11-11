---
status: accepted
date: 2026-11-11
deciders: Yajushi Garg
---

# ADR-0002: Use Unity Catalog managed tables

**Summary (Y-statement):** In the context of storing bronze, silver and gold tables in Unity Catalog, facing the need for consistent governance and low operational overhead, we decided for managed tables and against external tables, to achieve full lifecycle management, automatic optimization and governance that cannot be bypassed, accepting that tables must be Delta and that dropping a table also deletes its data.

## Context and Problem Statement
Every table in the lakehouse is either managed (Unity Catalog controls where and how the data files are stored and cleaned up) or external (the data lives at a storage path we manage, and Unity Catalog only registers it). The choice affects governance, maintenance effort, recovery from mistakes and how data is deleted. It needs to be made before the first bronze table is created.

## Decision Drivers
* Governance that cannot be bypassed (all access goes through Unity Catalog grants, row filters and column masks)
* Low operational overhead (automatic file maintenance, statistics, cleanup)
* Recovery from accidental deletion
* Controlled deletion of data, including personal data

## Considered Options
* Unity Catalog managed tables
* External tables

## Decision Outcome
Chosen option: "Managed tables" for all bronze, silver and gold tables, because Unity Catalog manages the full data lifecycle, applies predictive optimisation automatically, and is the only access path to the data.

Planned exception: one external volume and table on ADLS (W1-7), to practise external locations and storage credentials. Raw source files live in a Unity Catalog volume, not in tables.

### Consequences
* Good, because predictive optimisation runs maintenance (OPTIMIZE, VACUUM, statistics) automatically.
* Good, because a dropped table can be recovered with UNDROP for a limited period (check current window in Databricks docs).
* Good, because the managed location can still be set to our own ADLS container at catalog or schema level, so data stays in our storage account.
* Bad, because managed tables must be Delta (or Iceberg); CSV, JSON, Parquet, Avro or ORC files cannot be registered as managed tables.
* Bad, because dropping a managed table deletes its data once the recovery window ends, so DROP permissions must be tightly controlled.

## Risk and Compliance
* Privacy / PII: data is only reachable through Unity Catalog, so masks and row filters always apply. Deleting a table really removes the data, which supports deletion requests.
* Card data (PCI): no direct impact; CVV handling is covered in ADR-0008.
* Access and retention: DROP and MODIFY privileges restricted to the pipeline's service principal and engineers. Retention handled by predictive optimisation and VACUUM settings.

## Pros and Cons of the Options
### Managed tables
* Good, because full lifecycle management by Unity Catalog.
* Good, because automatic optimisation (predictive optimisation).
* Good, because UNDROP recovery for a limited period.
* Good, because governance cannot be bypassed through direct storage access.
* Bad, because limited to Delta (or Iceberg).
* Bad, because DROP deletes the data.

### External tables
* Good, because data stays at a path we control, and DROP removes only the metadata.
* Good, because supports many file formats (CSV, JSON, Parquet, Avro, ORC, Delta).
* Good, because the files can be shared with systems outside Databricks.
* Bad, because anyone with direct storage access can read the files without Unity Catalog's masks and grants.
* Bad, because maintenance and cleanup are our responsibility.
* Bad, because it needs extra setup (storage credential and external location).

## Revisit
If data must be shared with or written by systems outside Databricks, re-evaluate external tables for those datasets.