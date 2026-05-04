import io
import json
import re
from datetime import datetime

import boto3
import pandas as pd
import psycopg2
from botocore.client import Config

# ---------------------------------------------------------------------------
# MinIO (S3-compatible) client
# ---------------------------------------------------------------------------
s3 = boto3.client(
    's3',
    endpoint_url='http://minio:9000',
    aws_access_key_id='admin',
    aws_secret_access_key='password123',
    config=Config(signature_version='s3v4'),
    region_name='us-east-1',
)

BUCKET = 'news-bucket'

# ---------------------------------------------------------------------------
# Bronze → read all JSON files from MinIO
# ---------------------------------------------------------------------------
print("[Bronze] Loading raw JSON files from MinIO...")

response = s3.list_objects_v2(Bucket=BUCKET, Prefix='bronze/')
objects = response.get('Contents', [])

if not objects:
    raise RuntimeError(
        "No files found in news-bucket/bronze/ — scrape_news_data must run first."
    )

records = []
for obj in objects:
    body = s3.get_object(Bucket=BUCKET, Key=obj['Key'])['Body'].read()
    records.append(json.loads(body))

df_raw = pd.DataFrame(records)
print(f"[Bronze] Loaded {len(df_raw)} records: columns = {list(df_raw.columns)}")

# ---------------------------------------------------------------------------
# Silver → filter low-quality articles, clean HTML, normalise text
# ---------------------------------------------------------------------------
# Fill missing titles with the source URL so records are not dropped
df_raw['title'] = df_raw.apply(
    lambda r: r['title'] if pd.notna(r.get('title')) and str(r['title']).strip() else r.get('url', 'Unknown'),
    axis=1,
)

# Only drop records with no content or very short content
df_silver = df_raw[
    df_raw['content'].notna() &
    (df_raw['content'].str.len() > 50)
].copy()

df_silver['content_clean'] = df_silver['content'].apply(
    lambda x: re.sub(r'<[^>]*>', '', str(x)).lower().strip()
)
df_silver['processed_at'] = datetime.utcnow().isoformat()

print(f"[Silver] {len(df_silver)} records after quality filter")

# ---------------------------------------------------------------------------
# Gold → aggregate article counts per source / date
# ---------------------------------------------------------------------------
df_gold = (
    df_silver
    .groupby(['source', 'date_publication'], dropna=False)
    .size()
    .reset_index(name='article_count')
)

print(f"[Gold] {len(df_gold)} aggregated rows")

# ---------------------------------------------------------------------------
# Write Silver to MinIO as Parquet
# ---------------------------------------------------------------------------
silver_buf = io.BytesIO()
df_silver.to_parquet(silver_buf, index=False)
silver_buf.seek(0)
s3.put_object(
    Bucket=BUCKET,
    Key='silver/articles/data.parquet',
    Body=silver_buf.getvalue(),
)
print("[MinIO] Silver written → news-bucket/silver/articles/data.parquet")

# ---------------------------------------------------------------------------
# Write Gold to MinIO as Parquet
# ---------------------------------------------------------------------------
gold_buf = io.BytesIO()
df_gold.to_parquet(gold_buf, index=False)
gold_buf.seek(0)
s3.put_object(
    Bucket=BUCKET,
    Key='gold/source_stats/data.parquet',
    Body=gold_buf.getvalue(),
)
print("[MinIO] Gold written → news-bucket/gold/source_stats/data.parquet")

# ---------------------------------------------------------------------------
# Write to PostgreSQL  (DB: airflow / user: airflow)
# ---------------------------------------------------------------------------
conn = psycopg2.connect(
    host='postgres', port=5432,
    dbname='airflow', user='airflow', password='airflow',
)
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS news_articles (
        id              SERIAL PRIMARY KEY,
        title           TEXT,
        author          TEXT,
        date_publication TEXT,
        content         TEXT,
        content_clean   TEXT,
        source          TEXT,
        url             TEXT,
        processed_at    TEXT
    )
""")

cur.execute("""
    CREATE TABLE IF NOT EXISTS kpi_articles_count (
        source           TEXT,
        date_publication TEXT,
        article_count    INTEGER
    )
""")
conn.commit()

def _val(v):
    """Convert pandas NaN/NaT to None so psycopg2 inserts NULL correctly."""
    return None if pd.isna(v) else v

# Insert Silver rows
for _, row in df_silver.iterrows():
    cur.execute(
        """INSERT INTO news_articles
               (title, author, date_publication, content, content_clean, source, url, processed_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            _val(row.get('title')), _val(row.get('author')), _val(row.get('date_publication')),
            _val(row.get('content')), _val(row.get('content_clean')),
            _val(row.get('source')), _val(row.get('url')), _val(row.get('processed_at')),
        ),
    )

# Overwrite Gold rows
cur.execute("DELETE FROM kpi_articles_count")
for _, row in df_gold.iterrows():
    cur.execute(
        "INSERT INTO kpi_articles_count (source, date_publication, article_count) VALUES (%s, %s, %s)",
        (_val(row['source']), _val(row['date_publication']), int(row['article_count'])),
    )

conn.commit()
cur.close()
conn.close()

print("[PostgreSQL] Tables news_articles and kpi_articles_count written successfully!")