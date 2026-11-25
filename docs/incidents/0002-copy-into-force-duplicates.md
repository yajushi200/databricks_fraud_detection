# 0002: COPY INTO with force duplicated bronze.cards

| | |
|---|---|
| Date | 2026-11-25 |
| Table | `dev_fraud_detection.bronze.cards` |
| Task | W1-4 bronze ingestion (refs #10) |
| Type | Planned break-it (run from `scratch/`, never in the pipeline notebook) |
| Impact | Row count 6,146 → 12,292 (every card twice). Dev only, no downstream tables yet |

## What happened

`bronze.cards` is an explicit-schema table (no CVV column, ADR 0005) loaded with
`COPY INTO`. The first run inserted 6,146 rows; a second normal run inserted 0.
Then I re-ran the load with the force option:

```sql
COPY INTO dev_fraud_detection.bronze.cards
FROM (SELECT ... FROM '/Volumes/dev_fraud_detection/landing/raw_data/cards/')
FILEFORMAT = CSV
FORMAT_OPTIONS ('header' = 'true')
COPY_OPTIONS ('force' = 'true')
```

**Prediction:** it would load the same file again and double the table.
**Observed:** `num_inserted_rows` = 6,146; total count 12,292.

## Why

COPY INTO is idempotent because it records which files it has already loaded in the
table's Delta log and skips them on re-runs. `force = true` tells it to ignore that
record and load every file again, so the same rows were appended a second time.

## How it was detected

COPY INTO's own output (`num_inserted_rows` should be 0 for an unchanged file) and
the row count check against the profiled source count (6,146).

## Fix

Checked the history, then restored the last good version:

```sql
DESCRIBE HISTORY dev_fraud_detection.bronze.cards;
RESTORE TABLE dev_fraud_detection.bronze.cards TO VERSION AS OF 1;
```

| Version | Operation | Rows written |
|---|---|---|
| 0 | CREATE TABLE | 0 |
| 1 | COPY INTO | 6,146 |
| (none) | COPY INTO, 2nd normal run | 0: nothing written, so no new version |
| 2 | COPY INTO with force | 6,146 (duplicates) |
| 3 | RESTORE (to version 1) | back to 6,146 |

After the restore, a normal COPY INTO inserted **0** rows (predicted correctly):
restoring to version 1 also restored COPY INTO's record that the file was already
loaded.

## Prevention

- `force` never appears in pipeline notebooks; it is only for deliberate reloads
  after emptying a table.
- Before any RESTORE, query the candidate version first
  (`SELECT count(*) FROM ... VERSION AS OF n`) to verify it.
- Later: log the table version and row count after every successful load
  (e.g. `ops.load_log`), so the last good version is known without searching history.
- Known gotcha: COPY INTO tracks files by path. A corrected file overwritten with the
  same name is skipped, so source deliveries should use new file names.

## What I learned

- A Delta version is created only when a write changes the table. CTAS rewrites
  everything and always creates a version; COPY INTO with nothing new creates none.
- RESTORE brings back the table's state, including COPY INTO's file record, not just the rows.
- CTAS gets idempotency by replacing; COPY INTO gets it by remembering.