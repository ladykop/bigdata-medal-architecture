from pyspark.sql import SparkSession
from pyspark.sql.functions import col, length, lower, regexp_replace, current_timestamp

spark = SparkSession.builder \
    .appName("bdarch_news_pipeline_transform") \
    .getOrCreate()

# Load Raw Data (Bronze)
df_raw = spark.read.json("s3a://news-bucket/bronze/*.json")

# Silver Layer: Data Quality & Normalization
df_silver = df_raw.filter(
    (col("title").isNotNull()) & 
    (length(col("title")) > 5) &
    (col("content").isNotNull()) & 
    (length(col("content")) > 100)
).withColumn(
    "content_clean", regexp_replace(lower(col("content")), "<[^>]*>", "")
).withColumn(
    "processed_at", current_timestamp()
)

# Gold Layer: Aggregations for Dashboard
df_gold_metrics = df_silver.groupBy("source", "date_publication").count()

# Save Outputs
df_silver.write.mode("overwrite").parquet("s3a://news-bucket/silver/articles/")
df_gold_metrics.write.mode("overwrite").parquet("s3a://news-bucket/gold/source_stats/")