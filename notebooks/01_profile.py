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
