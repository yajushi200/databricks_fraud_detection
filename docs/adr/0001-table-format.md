---
status: accepted
date: 2026-11-11
deciders: Yajushi Garg
---

# ADR-0001: Use Delta Lake as the table format

**Summary (Y-statement):** In the context of a fraud-detection lakehouse on Azure Databricks, facing the need for reliable updates, change history and streaming on the same tables, we decided for Delta Lake and against Apache Iceberg, plain Parquet and CSV/JSON, to achieve native integration with Databricks features (Unity Catalog, Change Data Feed, declarative pipelines), accepting a weaker fit if the data must later be read natively by non-Databricks engines.

## Context and Problem Statement
The pipeline stores card transactions, customer and card data across bronze, silver and gold layers. Later stages need to update rows in place (MERGE into gold), keep change history (SCD Type 2, Change Data Feed), read tables as streams, and govern access through Unity Catalog. The table format has to support all of these, and changing it later would mean rewriting every table.

## Decision Drivers
* ACID transactions and safe in-place updates (MERGE) for incremental loads
* Change tracking and history (Change Data Feed, time travel) for SCD Type 2 and auditing
* Streaming reads and writes on the same tables
* Native support in the production platform (Azure Databricks: Unity Catalog, Lakeflow Declarative Pipelines, OPTIMIZE, liquid clustering)

## Considered Options
* Delta Lake
* Apache Iceberg
* Plain Apache Parquet
* CSV / JSON

## Decision Outcome
Chosen option: "Delta Lake", because it meets every decision driver natively on Azure Databricks. Iceberg offers comparable core features (ACID, time travel, schema evolution), but change tracking, CDC tooling, declarative pipelines and table optimisation in Databricks are built around Delta first.

### Consequences
* Good, because MERGE, Change Data Feed, time travel, streaming and Unity Catalog governance all work without extra setup.
* Good, because it is the Databricks default, so the project follows the platform's standard path.
* Bad, because tighter coupling to the Databricks ecosystem; if other engines (e.g. Trino, AWS Athena) need native access, Iceberg would fit better. This is partly mitigated by Delta UniForm, which lets Iceberg-compatible readers read Delta tables.

## Risk and Compliance
* Privacy / PII: time travel keeps old versions of rows, so deleted personal data can remain readable until VACUUM removes old files. Retention settings and VACUUM must be configured (W2-8, W3-2).
* Card data (PCI): no impact on the format choice itself. CVV is handled at ingestion (ADR-0008).
* Access and retention: Delta tables are governed by Unity Catalog grants, row filters and column masks.

## Pros and Cons of the Options
### Delta Lake
* Good, because ACID transactions, MERGE, time travel and schema enforcement.
* Good, because Change Data Feed and Databricks CDC tooling are native.
* Good, because it is the default format for Unity Catalog, declarative pipelines and table optimisation.
* Bad, because the best experience is inside Databricks; interoperability relies on UniForm or connectors.

### Apache Iceberg
* Good, because it is an open standard with broad multi-engine support (Trino, Athena, Snowflake, Spark).
* Good, because ACID transactions, time travel and schema evolution, comparable to Delta.
* Bad, because change tracking is less simple to use, and Databricks features are built around Delta first.

### Plain Apache Parquet
* Good, because efficient columnar storage, universally readable.
* Bad, because no transaction log: no ACID, no safe MERGE, no time travel, no schema enforcement.

### CSV / JSON
* Good, because simple and human-readable; the raw source files arrive in these formats.
* Bad, because no types, no compression, no transactions; only suitable as raw input in the landing zone, not as tables.

## Revisit
If a non-Databricks engine needs native access to these tables, re-evaluate Iceberg or UniForm.