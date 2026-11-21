# Contributing

How this project is built and maintained.

## Setup
1. Clone the repo and open it in VS Code.
2. Install dependencies: `uv sync`
3. Log in to Databricks: `databricks auth login --profile free`
4. Data is not in the repo. Download it from Kaggle into `data/` (see README).

## Load the raw data (dev)

Run these from the repo root after downloading the dataset into `data/` (see README).

**1. Create the catalog, schemas and volume**

Run `sql/00_setup_catalog.sql` in the Databricks SQL Editor. It is safe to rerun.

**2. Create one folder per source in the landing volume**

```
databricks fs mkdir dbfs:/Volumes/dev_fraud_detection/landing/raw_data/transactions --profile free
databricks fs mkdir dbfs:/Volumes/dev_fraud_detection/landing/raw_data/cards --profile free
databricks fs mkdir dbfs:/Volumes/dev_fraud_detection/landing/raw_data/users --profile free
databricks fs mkdir dbfs:/Volumes/dev_fraud_detection/landing/raw_data/mcc --profile free
databricks fs mkdir dbfs:/Volumes/dev_fraud_detection/landing/raw_data/fraud_labels --profile free
```

`fs cp` does not create missing folders, so this step comes first.

**3. Upload the source files**

```
databricks fs cp data/cards_data.csv dbfs:/Volumes/dev_fraud_detection/landing/raw_data/cards/cards_data.csv --profile free
databricks fs cp data/users_data.csv dbfs:/Volumes/dev_fraud_detection/landing/raw_data/users/users_data.csv --profile free
databricks fs cp data/mcc_codes.json dbfs:/Volumes/dev_fraud_detection/landing/raw_data/mcc/mcc_codes.json --profile free
databricks fs cp data/train_fraud_labels.json dbfs:/Volumes/dev_fraud_detection/landing/raw_data/fraud_labels/train_fraud_labels.json --profile free
```

Transactions are not uploaded here. They are split into monthly files and uploaded in batches to simulate data arriving over time (see W1-4).

**4. Check**

```
databricks fs ls dbfs:/Volumes/dev_fraud_detection/landing/raw_data/ --profile free
```

Expected: five folders (`transactions` empty, the other four with one file each).

## Workflow
- Every task starts as a GitHub issue (using the "Plan task" form) before any code is written.
- One branch per week: `week-1`, `week-2`, …
- Commits reference their issue: `refs #<number>`.
- Each week's work is merged into `main` through a pull request every Friday, using a merge commit (not squash) so daily history is kept.
- Each merge is tagged as a release (`v0.1`, `v0.2`, …).

## Commit messages
- `feat:` new pipeline or feature work
- `fix:` bug fixes
- `docs:` documentation, ADRs, incident notes
- `test:` tests
- `chore:` setup, config, dependencies

## Before opening a pull request
- `uv run pytest` passes.
- `git status` shows no data files, secrets or tool folders.
- The PR description lists `Closes #<number>` for every finished issue.

## Secrets and data
- Never commit tokens, keys, passwords or data files.
- Secrets live outside the repo (local config, Azure Key Vault).
- Card security codes (CVV) are dropped at ingestion and never stored.

## Breaking things on purpose
Planned failures are part of the process: predict → break → observe → fix → write an incident note in `docs/incidents/`.

## AI use
AI tools may explain concepts, review code and suggest test cases. All code in this repo is written by me.