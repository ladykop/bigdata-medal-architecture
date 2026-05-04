from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import subprocess
import sys

default_args = {
    'owner': 'iadata_student',
    'depends_on_past': False,
    'start_date': datetime(2026, 3, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def run_scraper():
    """
    Scrapes all 7 news sources (RSS + HTML) and uploads each article as a
    raw JSON file to MinIO news-bucket/bronze/ for the transform step.
    """
    import json
    import boto3
    from botocore.client import Config
    from scraper import scrape_all_sources

    articles = scrape_all_sources()
    print(f"[Scraper] Total articles collected: {len(articles)}")

    s3 = boto3.client(
        's3',
        endpoint_url='http://minio:9000',
        aws_access_key_id='admin',
        aws_secret_access_key='password123',
        config=Config(signature_version='s3v4'),
        region_name='us-east-1',
    )

    saved = 0
    for i, data in enumerate(articles):
        try:
            source_slug = (data.get('source') or 'unknown').lower().replace(' ', '_')
            key = f"bronze/article_{i:03d}_{source_slug}.json"
            s3.put_object(
                Bucket='news-bucket',
                Key=key,
                Body=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                ContentType='application/json',
            )
            print(f"[Bronze] Saved: {key} — {str(data.get('title', ''))[:60]}")
            saved += 1
        except Exception as e:
            print(f"[ERROR] Could not save article {i}: {e}")

    if saved == 0:
        raise RuntimeError("No articles saved to MinIO bronze — check scraper logs above")

    print(f"[Scraper] Done — {saved}/{len(articles)} articles uploaded to news-bucket/bronze/")


def run_spark_transform():
    """
    Runs spark_transform.py as a subprocess.
    Reads Bronze JSON from MinIO, writes Silver/Gold Parquet, loads PostgreSQL.
    """
    result = subprocess.run(
        [sys.executable, "/opt/airflow/scripts/spark_transform.py"],
        capture_output=True,
        text=True,
    )
    print("--- STDOUT ---")
    print(result.stdout)
    if result.stderr:
        print("--- STDERR ---")
        print(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(
            f"spark_transform.py exited with code {result.returncode}.\n"
            f"See STDERR above for details."
        )


with DAG(
    'bdarch_news_pipeline',
    default_args=default_args,
    schedule_interval='@hourly',
    catchup=False,
    description='Scrape news → MinIO Bronze → PySpark Silver/Gold → PostgreSQL',
    tags=['bigdata', 'news'],
) as dag:

    task_scrape = PythonOperator(
        task_id='scrape_news_data',
        python_callable=run_scraper,
    )

    task_transform = PythonOperator(
        task_id='transform_news_data',
        python_callable=run_spark_transform,
    )

    task_scrape >> task_transform