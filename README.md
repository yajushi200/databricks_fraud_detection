# databricks_fraud_detection

A Databricks lakehouse that turns raw card transactions into clean, reliable and governed data using a 3-layer medallion architecture (bronze → silver → gold).
The curated data is then used downstream for **fraud detection**: explaining past fraud patterns and training a baseline model to flag likely new fraud.

Developed on Databricks Free Edition and deployed to Azure Databricks, using Azure Data Lake Storage, Key Vault, Event Hubs and Azure Monitor.

## Tech stack
- Databricks: Unity Catalog, Lakeflow Declarative Pipelines, Lakeflow Jobs, Asset Bundles
- Azure: Databricks, Data Lake Storage Gen2, Key Vault, Event Hubs, Azure Monitor
- Languages: Python (PySpark), SQL
- CI/CD: GitHub Actions

**Status:** In progress. Built on weekly releases.

## Data
- Dataset: Financial Transactions Dataset: Analytics (Kaggle) — <https://www.kaggle.com/datasets/computingvictor/transactions-fraud-datasets>
- Licence: Apache 2.0
- Credit: created by CaixaBank Tech for their 2024 AI Hackathon
- The data is not stored in this repo. See [docs/data_inventory.md](docs/data_inventory.md) for details.