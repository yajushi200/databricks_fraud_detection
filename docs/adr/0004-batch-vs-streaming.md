---
status: accepted
date: 2026-11-11
deciders: Yajushi Garg
---

# ADR-0004: Batch vs streaming per source

**Summary (Y-statement):** In the context of loading historical files and a simulated live transaction feed, facing different freshness needs and a limited compute budget, we decided for full batch on static files, incremental batch (Structured Streaming with the `availableNow` trigger) on growing files, and continuous streaming only for the Event Hubs feed, and against streaming everything, to give each use the latency it actually needs, accepting two operating modes to run and monitor.

## Context and Problem Statement
The project has two kinds of input. Historical files (transactions, cards, users, MCC codes, fraud labels) arrive as files: some once, some monthly. A simulated live feed of transactions (Event Hubs, W2-4) represents how card payments reach a bank in real time. Running everything continuously would be costly and pointless for data that arrives monthly; running everything as batch would miss the real-time path that fraud detection depends on.

## Decision Drivers
* Freshness: how quickly results must be available for each source
* Cost: avoid paying for compute that sits idle
* Recoverability: exactly-once processing and safe restarts after failures
* Operational simplicity: as few always-on components as possible

## Considered Options
* Full batch (reload everything each run)
* Incremental batch (Structured Streaming with `availableNow`, run on a schedule or on file arrival)
* Continuous streaming (always-on, short `processingTime` trigger)

## Decision Outcome

| Source | Mode | Reason |
|---|---|---|
| mcc_codes.json | Full batch | Static, tiny; a full rebuild is cheap and simple |
| train_fraud_labels.json | Full batch | Static one-off file |
| transactions_data.csv | Incremental batch | New monthly files; process only new data, then stop |
| cards_data.csv, users_data.csv | Incremental batch | Small change batches; no need for real-time updates |
| Event Hubs transaction feed | Continuous streaming | Simulates live card payments, where fraud must be detected within seconds |
| Silver pipeline (Lakeflow Declarative Pipelines) | Triggered (incremental) | Runs after new bronze data lands; streaming tables process only new rows |

### Consequences
* Good, because compute runs only when there is new data, except for the live feed.
* Good, because incremental batch keeps streaming benefits (checkpoints, exactly-once, recovery) without an always-on cluster.
* Good, because the project shows both paths a bank uses: batch for history and reporting, streaming for real-time decisions.
* Bad, because two operating modes must be monitored, with different failure patterns.
* Bad, because the continuous stream costs money while running, so it is run for demonstration only and stopped afterwards (W2-4).

## Risk and Compliance
* Privacy / PII: no difference between modes; the same Unity Catalog controls apply to both.
* Card data (PCI): live events must not carry CVV; the producer sends only the fields the pipeline needs.
* Access and retention: checkpoint locations hold processing state and must be restricted to the pipeline identity; the Event Hubs connection string is stored in Azure Key Vault, never in code.

## Pros and Cons of the Options
### Full batch
* Good, because simplest to build and reason about.
* Bad, because it reprocesses everything every run; wasteful for large or growing data.

### Incremental batch
* Good, because it processes only new data, recovers safely from failures, and stops when finished.
* Good, because the same code can switch to continuous mode by changing the trigger.
* Bad, because results are only as fresh as the schedule or file arrival.

### Continuous streaming
* Good, because results within seconds; required for real-time fraud checks.
* Bad, because compute runs all the time; higher cost and more to monitor.

## Revisit
If the business needs fresher reporting (e.g. hourly instead of monthly), shorten the schedule or switch the transactions load to a `processingTime` trigger; the code does not need to change.