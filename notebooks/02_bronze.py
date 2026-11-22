# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Ingestion
# MAGIC - Loads the 5 raw sources from the landing volume into bronze Delta tables.
# MAGIC - Raw values are kept as strings; CVV is dropped before the first write (ADR 0005).
# MAGIC - Every table gets `_ingested_at` and `_source_file`.

# COMMAND ----------
from databricks.connect import DatabricksSession
spark = DatabricksSession.builder.getOrCreate()

# COMMAND ----------
catalog = "dev_fraud_detection"
source_schema = "landing"
target_schema = "bronze"
raw = f"/Volumes/{catalog}/{source_schema}/raw_data"

# COMMAND ----------
# MAGIC %md
# MAGIC ## 01. mcc (CTAS)
# MAGIC Dictionary-shaped JSON: read as text, parse as a MAP, explode into rows.

# COMMAND ----------
spark.sql(f"""
    CREATE OR REPLACE TABLE {catalog}.{target_schema}.mcc AS
    SELECT
        explode(from_json(value, 'MAP<STRING,STRING>')) AS (mcc, description),
        current_timestamp() AS _ingested_at,
        _metadata.file_path AS _source_file
    FROM read_files('{raw}/mcc/',
        format => 'text',
        wholeText => true)
""")

# COMMAND ----------
spark.sql(f"""
    SELECT * FROM {catalog}.{target_schema}.mcc
    ORDER BY mcc LIMIT 5
""").show(truncate=False)
print(spark.table(f"{catalog}.{target_schema}.mcc").count())
# COMMAND ----------
# MAGIC %md
# MAGIC ## 02. fraud_labels (CTAS)
# MAGIC - The dictionary sits inside a `target` key, so the json reader works with a MAP schema.
# MAGIC - Explode the map into one row per transaction.
# COMMAND ----------
spark.sql(f"""
    CREATE OR REPLACE TABLE {catalog}.{target_schema}.fraud_labels AS
    SELECT
        explode(target) AS (transaction_id, is_fraud),
        current_timestamp() AS _ingested_at,
        _metadata.file_path AS _source_file
    FROM read_files('{raw}/fraud_labels/',
        format => 'json',
        schema => 'target MAP<STRING,STRING>')
""")
# COMMAND ----------
spark.sql(f"""
    SELECT * FROM {catalog}.{target_schema}.fraud_labels
    ORDER BY transaction_id LIMIT 5
""").show(truncate=False)
print(spark.table(f"{catalog}.{target_schema}.fraud_labels").count())
# COMMAND ----------
