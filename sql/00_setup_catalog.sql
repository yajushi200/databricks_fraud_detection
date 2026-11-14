-- =========================================================
-- 00_setup_catalog.sql
-- Creates the catalog, schemas and landing volume for the
-- fraud detection lakehouse (dev environment).
-- Safe to run more than once: every statement uses IF NOT EXISTS.
-- Prod (Azure workspace) uses the same script with the catalog
-- name swapped by the Asset Bundle (W3-1).
-- =========================================================

-- 1. Catalog: one per environment
CREATE CATALOG IF NOT EXISTS dev_fraud_detection
COMMENT 'Development catalog for the fraud detection lakehouse';

-- 2. Use the catalog for everything below
USE CATALOG dev_fraud_detection;

-- 3. Schemas: one per layer, identical names in every environment
CREATE SCHEMA IF NOT EXISTS landing
COMMENT 'Raw source files in the raw_data volume';

CREATE SCHEMA IF NOT EXISTS bronze
COMMENT 'Source data as received, one table per source';

CREATE SCHEMA IF NOT EXISTS silver
COMMENT 'Cleaned, validated, deduplicated data with history';

CREATE SCHEMA IF NOT EXISTS gold
COMMENT 'Star schema and KPI views for analysts';

CREATE SCHEMA IF NOT EXISTS ops
COMMENT 'Quarantine, data quality results and reconciliation';

CREATE SCHEMA IF NOT EXISTS ml
COMMENT 'Features, registered models and fraud scores';

CREATE SCHEMA IF NOT EXISTS shared
COMMENT 'Aggregated tables shared externally via Delta Sharing (no PII)';

-- 4. Volume for raw source files (managed, per ADR-0002)
USE SCHEMA landing;

CREATE VOLUME IF NOT EXISTS raw_data
COMMENT 'Raw source files, one folder per source';

-- 5. Checks
SHOW SCHEMAS IN dev_fraud_detection;
DESCRIBE VOLUME dev_fraud_detection.landing.raw_data;