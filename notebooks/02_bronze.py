# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Ingestion
# MAGIC - Loads the 5 raw sources from the landing volume into bronze Delta tables.
# MAGIC - Raw values are kept as strings; CVV is dropped before the first write (ADR 0005).
# MAGIC - Every table gets `_ingested_at` and `_source_file`.

# COMMAND ----------
from databricks.connect import DatabricksSession
spark = DatabricksSession.builder.getOrCreate()
from pyspark.sql import functions as F

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
# MAGIC %md
# MAGIC ## 03. cards (COPY INTO)
# MAGIC - Step 1 creates an explicit-schema table with no CVV column, so CVV can never be stored (ADR 0005).
# MAGIC - Step 2 loads with COPY INTO, selecting the 12 allowed columns by name; CVV is dropped by not selecting it.
# MAGIC - Idempotent: COPY INTO records loaded files in the Delta log and skips them on re-runs.
# COMMAND ----------
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {catalog}.{target_schema}.cards (
        id                    STRING,
        client_id             STRING,
        card_brand            STRING,
        card_type             STRING,
        card_number           STRING,
        expires               STRING,
        has_chip              STRING,
        num_cards_issued      STRING,
        credit_limit          STRING,
        acct_open_date        STRING,
        year_pin_last_changed STRING,
        card_on_dark_web      STRING,
        _ingested_at          TIMESTAMP,
        _source_file          STRING
    )
    COMMENT 'Raw cards. CVV is excluded on purpose (ADR 0005): it must never be stored.'
""")
# COMMAND ----------
spark.sql(f"""
    COPY INTO {catalog}.{target_schema}.cards
    FROM (
        SELECT
            id,
            client_id,
            card_brand,
            card_type,
            card_number,
            expires,
            has_chip,
            num_cards_issued,
            credit_limit,
            acct_open_date,
            year_pin_last_changed,
            card_on_dark_web,
            current_timestamp()  AS _ingested_at,
            _metadata.file_path  AS _source_file
        FROM '{raw}/cards/'
    )
    FILEFORMAT = CSV
    FORMAT_OPTIONS ('header' = 'true')
""").show()
print(spark.table(f"{catalog}.{target_schema}.cards").count())
# COMMAND ----------
# MAGIC %md
# MAGIC ## 04. users (COPY INTO)
# MAGIC - Same pattern as cards: an explicit-schema table, then COPY INTO with the columns selected by name.
# MAGIC - Contains PII (address, latitude, longitude, birth_year, birth_month): kept raw in bronze, protected with Unity Catalog column masks in v0.3.
# MAGIC - Idempotent: re-runs skip files already loaded.
# COMMAND ----------
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {catalog}.{target_schema}.users (
        id                STRING,
        current_age       STRING,
        retirement_age    STRING,
        birth_year        STRING,
        birth_month       STRING,
        gender            STRING,
        address           STRING,
        latitude          STRING,
        longitude         STRING,
        per_capita_income STRING,
        yearly_income     STRING,
        total_debt        STRING,
        credit_score      STRING,
        num_credit_cards  STRING,
        _ingested_at      TIMESTAMP,
        _source_file      STRING
    )
    COMMENT 'Raw users. Contains PII (address, latitude, longitude, birth_year, birth_month); masked in Unity Catalog in v0.3.'
""")
# COMMAND ----------
spark.sql(f"""
    COPY INTO {catalog}.{target_schema}.users
    FROM (
        SELECT
            id,
            current_age,
            retirement_age,
            birth_year,
            birth_month,
            gender,
            address,
            latitude,
            longitude,
            per_capita_income,
            yearly_income,
            total_debt,
            credit_score,
            num_credit_cards,
            current_timestamp()  AS _ingested_at,
            _metadata.file_path  AS _source_file
        FROM '{raw}/users/'
    )
    FILEFORMAT = CSV
    FORMAT_OPTIONS ('header' = 'true')
""").show()
print(spark.table(f"{catalog}.{target_schema}.users").count())
# COMMAND ----------
# MAGIC %md
# MAGIC ## 05. transactions (Auto Loader)
# MAGIC - Incremental: each run processes only files not yet recorded in the checkpoint.
# MAGIC - Values kept as strings; unparseable values go to `_rescued_data` instead of being lost.
# MAGIC - Each stream gets its own checkpoint and schema folders under `ops.checkpoints`.
# COMMAND ----------
checkpoint_base = f"/Volumes/{catalog}/ops/checkpoints/bronze_transactions"

(
    spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("header", "true")
    .option("cloudFiles.schemaLocation", f"{checkpoint_base}/_schema")
    .load(f"{raw}/transactions/")
    .withColumn("_ingested_at", F.current_timestamp())
    .withColumn("_source_file", F.col("_metadata.file_path"))
    .writeStream
    .option("checkpointLocation", f"{checkpoint_base}/_checkpoint")
    .trigger(availableNow=True)
    .toTable(f"{catalog}.{target_schema}.transactions")
    .awaitTermination()
)
# COMMAND ----------
txn = spark.table(f"{catalog}.{target_schema}.transactions")
print(f"Rows:  {txn.count():,}   (expected 12,954,865)")
print(f"Files: {txn.select('_source_file').distinct().count()}   (expected 115)")
# COMMAND ----------
