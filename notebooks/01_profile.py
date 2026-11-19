# Databricks notebook source
from databricks.connect import DatabricksSession
spark = DatabricksSession.builder.getOrCreate()
# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Load files

# COMMAND ----------
base = "/Volumes/dev_fraud_detection/landing/raw_data"
csv_paths = {
    "transactions": f"{base}/profiling_snapshot/transactions_data.csv",
    "cards": f"{base}/cards/cards_data.csv",
    "users":f"{base}/users/users_data.csv"
}
# COMMAND ----------
dfs = {}                                        # 1. an empty box to keep the results in

for name, path in csv_paths.items():            # 2. take each pair from the dictionary, one at a time
    dfs[name] = spark.read.option("header", True).csv(path)   # 3. read that file, put it in the box under its name
# COMMAND ----------
for name, df in dfs.items():
    print(name, df.count())
# COMMAND ----------
# MAGIC %md
# MAGIC ## Load JSON Files
# COMMAND ----------
from pyspark.sql import functions as F

df_labels = (
    spark.read
         .schema("target MAP<STRING,STRING>")
         .json(f"{base}/fraud_labels/train_fraud_labels.json")
         .select(F.explode("target").alias("transaction_id", "is_fraud"))
)
# COMMAND ----------
df_mcc = (
    spark.read
         .text(f"{base}/mcc/mcc_codes.json", wholetext=True)
         .select(F.explode(F.from_json("value", "MAP<STRING,STRING>")).alias("mcc", "description"))
)
# COMMAND ----------
df_labels.count()
# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Completeness and uniqueness
# COMMAND ----------
dfs["labels"] = df_labels
dfs["mcc"] = df_mcc
# COMMAND ----------
for name, df in dfs.items():
    print(name)
    df.select([
        F.count(F.when(F.col(c).isNull() | (F.col(c) == ""), c)).alias(c)
        for c in df.columns
    ]).show(truncate=False)
# COMMAND ----------
dfs["transactions"].groupBy("use_chip").count().orderBy("count", ascending=False).show(truncate=False)
# COMMAND ----------
df = dfs["transactions"]

(df.filter(F.col("merchant_state").isNull() | (F.col("merchant_state") == ""))
   .groupBy("use_chip")
   .count()
   .orderBy("count", ascending=False)
   .show(truncate=False))
# COMMAND ----------
(df.filter(F.col("merchant_state").isNull() | (F.col("merchant_state") == ""))
   .groupBy("use_chip", "merchant_city").count()
   .orderBy("count", ascending=False)
   .show(20, truncate=False))
# COMMAND ----------
conflict_merchants = (
    df.filter((F.col("merchant_city") == "ONLINE") & (F.col("use_chip") == "Chip Transaction"))
      .select("merchant_id")
      .distinct()
)
print(conflict_merchants.count())
# COMMAND ----------
(df.join(conflict_merchants, "merchant_id", "left_semi")
   .groupBy("use_chip").count()
   .orderBy("count", ascending=False)
   .show(truncate=False))
# COMMAND ----------
(df.filter((F.col("zip").isNull() | (F.col("zip") == ""))
           & F.col("merchant_state").isNotNull() & (F.col("merchant_state") != ""))
   .groupBy("merchant_state")
   .count()
   .orderBy("count", ascending=False)
   .show(20, truncate=False))
# COMMAND ----------
(df.filter((F.col("zip").isNull() | (F.col("zip") == ""))
           & (F.length("merchant_state") == 2))
   .count())
# COMMAND ----------
(df.filter((F.col("zip").isNull() | (F.col("zip") == ""))
           & F.col("merchant_state").isNotNull() & (F.col("merchant_state") != ""))
   .count())
# COMMAND ----------
# MAGIC %md
# MAGIC ## 2(b). Uniqueness
# COMMAND ----------
keys = {
    "transactions": "id",
    "cards": "id",
    "users": "id",
    "labels": "transaction_id",
    "mcc": "mcc",
}

for name, key in keys.items():
    df = dfs[name]
    total = df.count()
    unique = df.select(key).distinct().count()
    print(name, "| total:", total, "| unique keys:", unique, "| duplicates:", total - unique)
# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Validity
# COMMAND ----------
df = dfs["transactions"]
df.select("amount").show(10, truncate=False)
# COMMAND ----------
amt = df.select(
    F.col("amount").alias("raw"),
    F.regexp_replace("amount", r"\$", "").cast("decimal(12,2)").alias("num")
)
amt.show(10, truncate=False)
# COMMAND ----------
amt.filter(F.col("num").isNull()).count()
# COMMAND ----------
print("negative:", amt.filter(F.col("num") < 0).count())
print("zero:", amt.filter(F.col("num") == 0).count())
# COMMAND ----------
amt.select(F.min("num").alias("min"), F.max("num").alias("max")).show()
# COMMAND ----------
print("exactly -500:", amt.filter(F.col("num") == -500).count())
# COMMAND ----------
df_amt = df.withColumn("num", F.regexp_replace("amount", r"\$", "").cast("decimal(12,2)"))
# COMMAND ----------
(df_amt.filter(F.col("num") < 0)
   .groupBy("mcc").count()
   .join(df_mcc, "mcc", "left")
   .orderBy("count", ascending=False)
   .show(10, truncate=False))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3(d). Convert the text to a real timestamp
# COMMAND ----------
df = dfs["transactions"]

dts = df.select(
    F.col("date").alias("raw"),
    F.try_to_timestamp(F.col("date"), F.lit("yyyy-MM-dd HH:mm:ss")).alias("ts")
)
dts.show(5, truncate=False)
# COMMAND ----------
dts.filter(F.col("ts").isNull()).count()
# COMMAND ----------
dts.select(F.min("ts").alias("first"), F.max("ts").alias("last")).show(truncate=False)
# COMMAND ----------
(dts.groupBy(F.year("ts").alias("year")).count()
    .orderBy("year")
    .show(truncate=False))
# COMMAND ----------
labeled = df.join(df_labels, df.id == df_labels.transaction_id, "left")

(labeled.groupBy(F.year(F.try_to_timestamp(F.col("date"), F.lit("yyyy-MM-dd HH:mm:ss"))).alias("year"))
   .agg(F.count("*").alias("transactions"),
        F.count("transaction_id").alias("labeled"))
   .orderBy("year")
   .show(truncate=False))
# COMMAND ----------
(df.filter(F.col("errors").isNotNull() & (F.col("errors") != ""))
   .groupBy("errors").count()
   .orderBy("count", ascending=False)
   .show(20, truncate=False))
# COMMAND ----------
(df.filter(F.col("errors").isNotNull() & (F.col("errors") != ""))
   .select(F.explode(F.split("errors", ",")).alias("error"))
   .groupBy("error").count()
   .orderBy("count", ascending=False)
   .show(truncate=False))
# COMMAND ----------
(labeled.filter(F.col("is_fraud").isNotNull())
   .groupBy((F.col("errors").isNotNull() & (F.col("errors") != "")).alias("has_error"))
   .agg(F.count("*").alias("transactions"),
        F.sum(F.when(F.col("is_fraud") == "Yes", 1).otherwise(0)).alias("fraud"))
   .withColumn("fraud_rate_%", F.round(F.col("fraud") / F.col("transactions") * 100, 3))
   .show(truncate=False))
# COMMAND ----------
amt_num = F.regexp_replace("amount", r"\$", "").cast("decimal(12,2)")

(labeled.filter(F.col("is_fraud").isNotNull() & F.col("errors").isNotNull() & (F.col("errors") != ""))
   .withColumn("error", F.explode(F.split("errors", ",")))
   .groupBy("error")
   .agg(F.count("*").alias("transactions"),
        F.sum(F.when(F.col("is_fraud") == "Yes", 1).otherwise(0)).alias("fraud"),
        F.sum(F.when(F.col("is_fraud") == "Yes", amt_num).otherwise(0)).alias("fraud_amount"))
   .withColumn("fraud_rate_%", F.round(F.col("fraud") / F.col("transactions") * 100, 3))
   .orderBy("fraud_rate_%", ascending=False)
   .show(truncate=False))

# COMMAND ----------
