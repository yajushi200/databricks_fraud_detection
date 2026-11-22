# 0001: INSERT INTO duplicated bronze.mcc

| | |
|---|---|
| Date | 2026-11-22 |
| Table | `dev_fraud_detection.bronze.mcc` |
| Task | W1-4 bronze ingestion (refs #10) |
| Type | Planned break-it |
| Impact | Row count 109 → 327 (3 identical copies). Dev only, no downstream tables yet |

## What happened

After loading `bronze.mcc` with `CREATE OR REPLACE TABLE ... AS SELECT` (109 rows),
I re-ran the load as a plain `INSERT INTO` twice:

```sql
INSERT INTO dev_fraud_detection.bronze.mcc
SELECT explode(from_json(value, 'MAP<STRING,STRING>')) AS (mcc, description),
       current_timestamp(), _metadata.file_path
FROM read_files('/Volumes/dev_fraud_detection/landing/raw_data/mcc/',
                format => 'text', wholeText => true)
```

**Prediction:** the count would grow by 109 per run.
**Observed:** 109 → 218 → 327. The copies are identical except for `_ingested_at`.

## Why

`INSERT INTO` appends. It does not check whether the rows already exist, so it is
not idempotent. `CREATE OR REPLACE` swaps the whole table atomically, so re-running
it always gives 109 rows (tested: 2 runs, still 109).

## How it was detected

Row count check after the load. Without that check the duplicates would be almost
invisible, and every count, join and fraud rate built on this table would be 3x wrong.

## Fix

Used Delta time travel to go back to the last good version:

```sql
DESCRIBE HISTORY dev_fraud_detection.bronze.mcc;
RESTORE TABLE dev_fraud_detection.bronze.mcc TO VERSION AS OF 1;
```

| Version | Operation | Rows |
|---|---|---|
| 0 | CREATE OR REPLACE TABLE AS SELECT | 109 |
| 1 | CREATE OR REPLACE TABLE AS SELECT | 109 |
| 2 | WRITE (INSERT) | +109 |
| 3 | WRITE (INSERT) | +109 |
| 4 | RESTORE (to version 1) | 109 |

RESTORE does not erase versions 2 and 3. It adds a new version, so the mistake and
the fix both stay in the audit trail.

## Prevention

- Bronze loaders only use idempotent methods: CTAS with `CREATE OR REPLACE`,
  `COPY INTO` and Auto Loader.
- Every task must be safe to re-run, because a Lakeflow Job retry runs the same code again.
- Reconciliation checks (rows in source files = rows in bronze) will catch duplicates automatically.
- One-off fixes like `RESTORE` never live in pipeline notebooks: a hard-coded version
  number would undo every future load.

## What I learned

- Idempotency depends on the write method, not on the data.
- Delta history lets you undo a bad write without reloading from source.
- Databricks shows timestamps in UTC; store in UTC and convert only for display.