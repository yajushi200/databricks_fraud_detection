# Naming conventions

All names are lowercase with underscores (`snake_case`), so they never need quoting in SQL and read the same everywhere.

## Catalogs: one per environment

| Catalog | Lives in | Purpose |
|---|---|---|
| `dev_fraud_detection` | Databricks Free Edition | Development and testing |
| `prod_fraud_detection` | Azure Databricks | Production |

**Why:** dev code can never touch prod data, and access can be granted per environment in one place. The project name in the catalog keeps it separate from other projects in the same workspace. Only the catalog name changes between environments; the bundle swaps it per target (`dev` / `prod`).

## Schemas: one per layer, identical in both catalogs

| Schema | Holds |
|---|---|
| `landing` | The `raw_data` volume with source files |
| `bronze` | Source data as received, one table per source |
| `silver` | Cleaned, validated, deduplicated data with history |
| `gold` | Star schema and KPI views for analysts |
| `ops` | Quarantine, data quality results, reconciliation |
| `ml` | Features, registered models, fraud scores |
| `shared` | Aggregated tables shared externally via Delta Sharing (no PII) |

**Why:** identical schema names mean only one part of a full name changes per environment (`dev_fraud_detection.bronze.transactions` → `prod_fraud_detection.bronze.transactions`). `ml` is separate so model work does not need write access to `gold`. `shared` holds only what is safe to share, so a whole schema can be shared without exposing PII by mistake.

## Tables

**Bronze and silver:** named after the source data, not the file.

| Table | Source file |
|---|---|
| `transactions` | transactions_data.csv |
| `users` | users_data.csv |
| `cards` | cards_data.csv |
| `mcc` | mcc_codes.json |
| `fraud_labels` | train_fraud_labels.json |

**Gold:** prefixed by table type.

| Prefix | Type | Examples |
|---|---|---|
| `fact_` | Fact tables (events, one row per transaction) | `fact_transactions` |
| `dim_` | Dimension tables (descriptive attributes) | `dim_users`, `dim_cards`, `dim_merchants`, `dim_mcc`, `dim_date` |
| `mv_` | Materialized views (KPI marts) | `mv_fraud_rate_by_mcc` |

**Why:** prefixes show a table's role at a glance and group related tables together in Catalog Explorer.

## Volumes

| Volume | Path | Holds |
|---|---|---|
| `raw_data` | `/Volumes/<catalog>/landing/raw_data/` | Source files, one folder per source |

**Why:** named after its contents (raw files), not the project, which the catalog already identifies.