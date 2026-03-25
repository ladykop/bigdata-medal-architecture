from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, current_timestamp

spark = SparkSession.builder.appName("PFE-Medallion").getOrCreate()

# 1. BRONZE (Read Raw)
df = spark.read.json("file:///opt/airflow/scripts/news_raw.json")

# 2. SILVER (Cleaning)
df_silver = df.withColumn("title_clean", lower(col("title"))) \
              .withColumn("processed_at", current_timestamp())

# 3. GOLD (Aggregation)
df_gold = df_silver.groupBy("source").count()

# 4. EXPORT TO POSTGRES
df_gold.write.format("jdbc") \
    .option("url", "jdbc:postgresql://postgres:5432/data_warehouse") \
    .option("dbtable", "kpi_articles_count") \
    .option("user", "admin").option("password", "admin") \
    .option("driver", "org.postgresql.Driver") \
    .mode("overwrite").save()

spark.stop()