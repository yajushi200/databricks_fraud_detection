---
status: accepted
date: 2026-11-12
deciders: Yajushi Garg
---

# ADR-0006: Notebooks for bronze and gold, Lakeflow Declarative Pipelines for silver

**Summary (Y-statement):** In the context of building bronze, silver and gold layers, facing a trade-off between full manual control and managed orchestration with built-in data quality, I decided for notebooks with Lakeflow Jobs in bronze and gold, and Lakeflow Declarative Pipelines in silver, and against using a single framework everywhere, to use each framework where its strengths matter most, accepting two styles of code to maintain.

## Context and Problem Statement
The ingestion tools are decided (ADR-0003). This decision is about the framework that runs them: notebooks scheduled by Lakeflow Jobs, where every step, dependency, checkpoint and retry is written by hand, or Lakeflow Declarative Pipelines, where tables are declared and Databricks manages order, checkpoints, retries, data quality expectations and CDC. Silver needs expectations, quarantine and AUTO CDC; bronze and gold need explicit control over loads and MERGE.

## Decision Drivers
* Built-in data quality (expectations, quarantine) and CDC support where data is cleaned
* Explicit control where loads must be precise (CVV exclusion, COPY INTO, MERGE)
* Learning both frameworks and comparing them on real work
* Recoverability: safe reruns and restarts after failures

## Considered Options
* Notebooks with Lakeflow Jobs everywhere
* Lakeflow Declarative Pipelines everywhere
* Hybrid by layer

## Decision Outcome
Chosen option: "Hybrid by layer", because each layer has different needs.

| Layer | Framework | Reason |
|---|---|---|
| Bronze | Notebooks + Lakeflow Jobs | Full control over each ingestion method (Auto Loader, COPY INTO, CTAS) and the CVV exclusion |
| Silver | Lakeflow Declarative Pipelines | Expectations, quarantine, AUTO CDC (SCD Type 2), schema drift handling, automatic checkpoints |
| Gold | Notebook/SQL tasks + materialized views | MERGE into the fact table needs explicit control; KPI views refresh automatically |
| Event Hubs feed | Notebook with Structured Streaming | Watermarks, triggers and checkpoints configured directly, without a framework hiding them |

### Consequences
* Good, because silver gets data quality and CDC with far less code than doing it by hand.
* Good, because bronze and gold keep precise control where mistakes would be costly.
* Good, because the project compares both frameworks on real work (to be written up after W2-1).
* Bad, because two styles of code, deployment and debugging must be maintained.
* Bad, because Databricks recommends Auto Loader inside declarative pipelines for incremental ingestion; bronze notebooks manage checkpoints manually instead.

## Risk and Compliance
* Privacy / PII: same Unity Catalog controls in both frameworks.
* Card data (PCI): the CVV exclusion lives in the bronze notebook, covered by a test (ADR-0005).
* Access and retention: the pipeline event log records data quality results per run, which provides audit evidence; pipelines and jobs run as the service principal in prod.

## Pros and Cons of the Options
### Notebooks with Lakeflow Jobs everywhere
* Good, because full control and visibility of every step.
* Bad, because data quality, CDC, checkpoints and retries must all be written by hand.

### Lakeflow Declarative Pipelines everywhere
* Good, because the most automation and the least code.
* Bad, because less direct control over ingestion details and MERGE logic; less hands-on learning of the underlying mechanics.

### Hybrid by layer
* Good, because each layer uses the framework that suits it.
* Bad, because two frameworks to learn, deploy and debug.

## Revisit
After W2-1, compare effort and reliability between the bronze notebooks and the silver pipeline; if the pipeline proves simpler, consider moving bronze ingestion into it.