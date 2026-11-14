---
status: accepted
date: 2026-11-11
deciders: Yajushi Garg
---

# ADR-0003: Ingestion tool per source

**Summary (Y-statement):** In the context of loading five file-based sources into bronze, facing sources that differ in size, growth and shape, we decided for Auto Loader (transactions), COPY INTO (cards, users) and CTAS with an explicit schema (MCC codes, fraud labels), and against Lakeflow Connect managed connectors and Azure Data Factory, to match each source with the simplest tool that loads it reliably and rerunnably, accepting that three methods must be maintained instead of one.

## Context and Problem Statement
All sources are files landed in cloud storage (a Unity Catalog volume in dev, ADLS in prod). They differ: transactions grow monthly (13.3M rows), cards and users are small but change over time, and the two JSON files are static dictionaries rather than lists of records. Each needs a loading method that can be rerun safely without creating duplicates.

## Decision Drivers
* Rerunnable loads (no duplicates when a load runs twice)
* Incremental processing for sources that keep growing
* Correct handling of dictionary-shaped JSON files
* Simplicity: the least complex tool that fits each source

## Considered Options
* Auto Loader (Lakeflow Connect standard connector for cloud storage, running on Spark Structured Streaming)
* COPY INTO
* CTAS / CREATE OR REPLACE TABLE
* Lakeflow Connect managed connectors
* Azure Data Factory

## Decision Outcome

| Source | Tool | Reason |
|---|---|---|
| transactions_data.csv | Auto Loader (Structured Streaming, `availableNow` trigger) | New monthly files keep arriving; Auto Loader discovers only new files, processes each exactly once via its checkpoint, and handles schema changes |
| cards_data.csv | COPY INTO | Small, repeated batch loads; skips files already loaded; SQL-first and simple |
| users_data.csv | COPY INTO | Same as cards |
| mcc_codes.json | CTAS with explicit schema | Static 109-entry dictionary; full rebuild is cheap; explicit MAP schema plus explode turns it into rows |
| train_fraud_labels.json | CTAS with explicit schema | Static one-off file; nested dictionary under "target" read as a MAP and exploded into transaction_id, label rows |

The JSON reshaping (dictionary to rows) happens during the load, inside Databricks. It changes structure only; values are not cleaned or converted in bronze.

### Consequences
* Good, because every load can be rerun without duplicating data.
* Good, because transactions are processed incrementally as new months arrive, without a cluster running continuously.
* Good, because each source uses the simplest tool that fits it.
* Bad, because three loading methods must be understood and maintained.
* Bad, because COPY INTO's idempotency is per file: a new file containing rows already loaded will duplicate them, so silver must deduplicate.

## Risk and Compliance
* Privacy / PII: users and cards contain PII; the loading method does not change exposure. Masking is applied in later layers (W3-2).
* Card data (PCI): CVV is dropped during the cards load, before it reaches bronze (ADR-0005).
* Access and retention: Auto Loader checkpoints and source files must be readable only by the pipeline identity.

## Pros and Cons of the Options
### Auto Loader
* Good, because incremental file discovery, exactly-once processing, schema evolution, many formats.
* Good, because it runs on Structured Streaming, so it can be triggered as a scheduled batch (`availableNow`) or run continuously.
* Bad, because it adds checkpoint state to manage; more setup than needed for static files.

### COPY INTO
* Good, because simple SQL, skips already-loaded files, good for repeated small batches.
* Bad, because idempotent per file, not per row; does not reshape data.
* Bad, because Databricks now recommends streaming tables (`CREATE STREAMING TABLE`) over COPY INTO for incremental SQL ingestion.

### CTAS / CREATE OR REPLACE TABLE
* Good, because simplest for static files; full rebuild makes reruns safe; can reshape data in the query.
* Bad, because it rewrites the whole table every run; unsuitable for large growing data.

### Lakeflow Connect managed connectors
* Good, because managed ingestion from SaaS apps and databases, including change capture.
* Bad, because not applicable: all sources here are files in storage.

### Azure Data Factory
* Good, because it orchestrates data movement across Azure services.
* Bad, because not applicable: no cross-service coordination is needed, and transformations belong in Databricks.

## Revisit
* In W2-3, when change batches for cards and users arrive, re-evaluate moving them to Auto Loader feeding AUTO CDC in a declarative pipeline.
* Databricks recommends streaming tables over COPY INTO for incremental SQL ingestion; re-evaluate COPY INTO for cards and users at the same time.