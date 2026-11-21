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
# MAGIC %md
# MAGIC ## 5. Referential Integrity (Finding Orphan Rows)
# COMMAND ----------
links = [
    # (name,                              child,          child_col,        parent,         parent_col)
    ("txn.card_id -> cards.id",           "transactions", "card_id",        "cards",        "id"),
    ("txn.client_id -> users.id",         "transactions", "client_id",      "users",        "id"),
    ("cards.client_id -> users.id",       "cards",        "client_id",      "users",        "id"),
    ("txn.mcc -> mcc.mcc",                "transactions", "mcc",            "mcc",          "mcc"),
    ("labels.transaction_id -> txn.id",   "labels",       "transaction_id", "transactions", "id"),
]

for name, child_name, child_col, parent_name, parent_col in links:
    child = dfs[child_name]
    parent_keys = dfs[parent_name].select(F.col(parent_col).alias("_pk"))
    orphans = child.join(parent_keys, child[child_col] == parent_keys["_pk"], "left_anti")
    print(f"{name}: {orphans.count():,} orphans")
# COMMAND ----------
fake = spark.createDataFrame([("FAKE1", "99999999")], ["id", "card_id"])
fake.join(dfs["cards"].select(F.col("id").alias("_pk")),
          fake["card_id"] == F.col("_pk"), "left_anti").count()
# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. Consistency (do the related facts agree with each other?)
# COMMAND ----------
card_owners = dfs["cards"].select(
    F.col("id").alias("card_pk"),
    F.col("client_id").alias("card_owner"),
)

joined = dfs["transactions"].join(card_owners, F.col("card_id") == F.col("card_pk"), "inner")

print(f"Joined rows: {joined.count():,}")   # should be 13,305,915

mismatches = joined.filter(F.col("client_id") != F.col("card_owner")).count()
print(f"Client/card owner mismatches: {mismatches:,}")
# COMMAND ----------
actual = (
    dfs["cards"]
    .groupBy("client_id")
    .agg(F.count("*").alias("actual_cards"))
)

print(f"Clients with at least 1 card: {actual.count():,}")
actual.orderBy(F.desc("actual_cards")).show(10)
# COMMAND ----------
compare = (
    dfs["users"]
    .select(F.col("id"), F.col("num_credit_cards").cast("int").alias("stated_cards"))
    .join(actual, F.col("id") == F.col("client_id"), "left")
    .withColumn("actual_cards", F.coalesce(F.col("actual_cards"), F.lit(0)))
)

print(f"Users compared: {compare.count():,}")   # should be 2,000
mismatch = compare.filter(F.col("stated_cards") != F.col("actual_cards"))
print(f"Users where stated != actual: {mismatch.count():,}")
mismatch.show(10)
# COMMAND ----------
# MAGIC %md
# MAGIC ## 7. Validity (Cards)
# COMMAND ----------
categorical = [
    ("cards",  "card_brand"),
    ("cards",  "card_type"),
    ("cards",  "has_chip"),
    ("cards",  "card_on_dark_web"),
    ("users",  "gender"),
    ("labels", "is_fraud"),
]

for table, col in categorical:
    print(f"--- {table}.{col} ---")
    (dfs[table]
        .groupBy(col)
        .count()
        .orderBy(F.desc("count"), col)
        .show(truncate=False))
# COMMAND ----------
numeric_cols = [
    ("cards", "credit_limit"),
    ("users", "per_capita_income"),
    ("users", "yearly_income"),
    ("users", "total_debt"),
    ("users", "credit_score"),
    ("users", "current_age"),
    ("users", "retirement_age"),
    ("users", "birth_year"),
]

for table, col in numeric_cols:
    raw = F.col(col)
    parsed = F.regexp_replace(raw, r"[$,]", "").cast("decimal(14,2)")
    (dfs[table]
        .agg(
            F.count(F.when(raw.isNotNull() & parsed.isNull(), 1)).alias("failed_parse"),
            F.min(parsed).alias("min"),
            F.max(parsed).alias("max"),
        )
        .show(truncate=False))
    print(f"^ {table}.{col}")
# COMMAND ----------
print("--- credit_limit = 0, by card_type ---")
(dfs["cards"]
    .filter(F.regexp_replace("credit_limit", r"[$,]", "").cast("decimal(14,2)") == 0)
    .groupBy("card_type").count().show())

print("--- users with yearly_income under $1,000 ---")
print(dfs["users"]
    .filter(F.regexp_replace("yearly_income", r"[$,]", "").cast("decimal(14,2)") < 1000)
    .count())

print("--- birth_year + current_age ---")
(dfs["users"]
    .groupBy((F.col("birth_year").cast("int") + F.col("current_age").cast("int")).alias("as_of_year"))
    .count().show())
# COMMAND ----------
for col in ["expires", "acct_open_date"]:
    parsed = F.try_to_timestamp(F.col(col), F.lit("MM/yyyy"))
    print(f"--- cards.{col} ---")
    (dfs["cards"]
        .agg(
            F.count(F.when(F.col(col).isNotNull() & parsed.isNull(), 1)).alias("failed_parse"),
            F.min(parsed).alias("min"),
            F.max(parsed).alias("max"),
        )
        .show(truncate=False))
# COMMAND ----------
cards_dates = dfs["cards"].select(
    F.col("id").alias("card_pk"),
    F.try_to_timestamp(F.col("acct_open_date"), F.lit("MM/yyyy")).alias("opened"),
    F.try_to_timestamp(F.col("expires"), F.lit("MM/yyyy")).alias("exp"),
)

print("Cards opened after they expire:",
      cards_dates.filter(F.col("opened") > F.col("exp")).count())

txn_dates = (
    dfs["transactions"]
    .select("card_id", F.try_to_timestamp(F.col("date"), F.lit("yyyy-MM-dd HH:mm:ss")).alias("txn_ts"))
    .join(cards_dates, F.col("card_id") == F.col("card_pk"), "inner")
)

print("Transactions before account opened:",
      txn_dates.filter(F.col("txn_ts") < F.col("opened")).count())
print("Transactions after card expired:",
      txn_dates.filter(F.col("txn_ts") >= F.add_months(F.col("exp"), 1)).count())
# COMMAND ----------
u = dfs["users"]
print("--- users: birth_month, latitude, longitude ---")
u.agg(
    F.min(F.col("birth_month").cast("int")).alias("min_month"),
    F.max(F.col("birth_month").cast("int")).alias("max_month"),
    F.min(F.col("latitude").cast("double")).alias("min_lat"),
    F.max(F.col("latitude").cast("double")).alias("max_lat"),
    F.min(F.col("longitude").cast("double")).alias("min_lon"),
    F.max(F.col("longitude").cast("double")).alias("max_lon"),
).show()

print("--- ID columns that fail to cast to BIGINT ---")
for table, col in [("labels", "transaction_id"), ("transactions", "id"), ("cards", "id"), ("users", "id")]:
    bad = dfs[table].filter(F.col(col).isNotNull() & F.col(col).try_cast("bigint").isNull()).count()
    print(f"{table}.{col}: {bad}")
# COMMAND ----------
