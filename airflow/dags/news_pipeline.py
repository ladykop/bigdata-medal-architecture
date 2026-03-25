from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from datetime import datetime
import sys
sys.path.append('/opt/airflow/scripts')
from scraper import run_scraping

with DAG('pfe_news_pipeline', start_date=datetime(2026, 3, 25), schedule_interval='@daily') as dag:
    
    task_ingest = PythonOperator(task_id='ingest_news', python_callable=run_scraping)
    
    task_transform = SparkSubmitOperator(
        task_id='spark_process',
        application='/opt/airflow/scripts/spark_transform.py',
        conn_id='spark_default'
    )

    task_ingest >> task_transform