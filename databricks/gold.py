# Databricks notebook source
# DBTITLE 1,Defines the Storage Account Name, Secrets and Spark Configurations
storage_account_name = "projectbeesdatalake"
appid = dbutils.secrets.get(scope = "sp-scope", key = "adb-appId") #App ID
appsecret = dbutils.secrets.get(scope = "sp-scope", key = "adb-appSecret") #App Secret
tenantid = dbutils.secrets.get(scope = "sp-scope", key = "adb-tenantId") #Tenant ID

spark.conf.set("fs.azure.account.auth.type." + storage_account_name + ".dfs.core.windows.net", "OAuth") 
spark.conf.set("fs.azure.account.oauth.provider.type." + storage_account_name + ".dfs.core.windows.net", "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider")
spark.conf.set("fs.azure.account.oauth2.client.id." + storage_account_name + ".dfs.core.windows.net", appid) 
spark.conf.set("fs.azure.account.oauth2.client.secret." + storage_account_name + ".dfs.core.windows.net", appsecret)
spark.conf.set("fs.azure.account.oauth2.client.endpoint." + storage_account_name + ".dfs.core.windows.net", "https://login.microsoftonline.com/"+ tenantid +"/oauth2/token")

# COMMAND ----------

from delta.tables import DeltaTable
from pyspark.sql.functions import col, countDistinct

# COMMAND ----------

# DBTITLE 1,Defines containers location
silver_storage_container = "silver"
gold_storage_container = "gold"

adls_silver_base_path = f"abfss://{silver_storage_container}" \
                        f"@{storage_account_name}.dfs.core.windows.net"
adls_gold_base_path = f"abfss://{gold_storage_container}" \
                        f"@{storage_account_name}.dfs.core.windows.net"

job_base_path_silver = f"{adls_silver_base_path}/datalake/json/"
job_base_path_gold = f"{adls_gold_base_path}/delta/"

job_staging_path = f"{job_base_path_silver}/staging/"
job_output_path = f"{job_base_path_gold}/data/"

# COMMAND ----------

# DBTITLE 1,Read Silver Delta Table
df_input = spark.read.format('delta').load(job_staging_path)

# COMMAND ----------

# DBTITLE 1,Select only the necessary columns
df_beweries = df_input.select(col("id").alias("id"),
                        col("name").alias("name"),
                        col("brewery_type").alias("brewery_type"),
                        col("city").alias("city"),
                        col("state").alias("state"),
                        col("country").alias("country"))

# COMMAND ----------

# DBTITLE 1,Create aggregated views
df_aggregate_type = df_beweries.groupBy("brewery_type").agg(countDistinct("id")).createOrReplaceTempView("BreweryTypeCount")
df_aggregate_location = df_beweries.groupBy("country", "state", "city").agg(countDistinct("id")).createOrReplaceTempView("BreweryLocationCount")

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM BreweryTypeCount

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM BreweryLocationCount

# COMMAND ----------

# DBTITLE 1,Create delta table partitioned by location
df_beweries.write.saveAsTable("bees.beweries_gold",
                           format="delta",
                           mode="overwrite",
                           path=job_output_path,
                           partitionBy="state")

# COMMAND ----------

# DBTITLE 1,Applies Vaccum
delta_table = DeltaTable.forName(spark, "bees.beweries_gold")
delta_table.vacuum()

# COMMAND ----------

# DBTITLE 1,Delete staging from silver layer
try:
    dbutils.fs.rm(job_staging_path, True)
except Exception as e:
    raise Exception(f'Error removing data from {job_staging_path}.\
                    Exception: {e}')
