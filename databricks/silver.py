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

# DBTITLE 1,Import packages
from delta.tables import DeltaTable

# COMMAND ----------

# DBTITLE 1,Defines containers location
silver_storage_container = "silver"

adls_silver_base_path = f"abfss://{silver_storage_container}" \
                        f"@{storage_account_name}.dfs.core.windows.net"

job_base_path_silver = f"{adls_silver_base_path}/datalake/json/"

job_input_path = f"{job_base_path_silver}/input/breweries.json"
job_staging_path = f"{job_base_path_silver}/staging/"
job_output_path = f"{job_base_path_silver}/data/"

# COMMAND ----------

# DBTITLE 1,Create the schema
# MAGIC %sql
# MAGIC
# MAGIC CREATE SCHEMA IF NOT EXISTS bees

# COMMAND ----------

# DBTITLE 1,Read JSON data
df_input = spark.read.json(job_input_path)

# COMMAND ----------

# DBTITLE 1,Create delta table partitioned by location
df_input.write.saveAsTable("bees.beweries_silver",
                           format="delta",
                           mode="overwrite",
                           path=job_output_path,
                           partitionBy="state")

# COMMAND ----------

# DBTITLE 1,Saving at the staging directory
df_input.write.mode('overwrite').format('delta').save(job_staging_path)

# COMMAND ----------

# DBTITLE 1,Applies Vaccum
delta_table = DeltaTable.forName(spark, "bees.beweries_silver")
delta_table.vacuum()

# COMMAND ----------

# DBTITLE 1,Delete data from input
try:
    dbutils.fs.rm(job_input_path, True)
except Exception as e:
    raise Exception(f'Error removing data from {job_input_path}.\
                    Exception: {e}')
