from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'iadata_student',
    'depends_on_past': False,
    'start_date': datetime(2026, 3, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'bdarch_news_pipeline',
    default_args=default_args,
    schedule_interval='@hourly',
    catchup=False
) as dag:

    def run_scraper():
        # Example URLs
        urls = [("https://example.com/news1", "Hespress")]
        from scraper import bdarch_scrape_article
        for url, source in urls:
            bdarch_scrape_article(url, source)

    task_scrape = PythonOperator(
        task_id='scrape_news_data',
        python_callable=run_scraper
    )

    # Add Spark submit tasks here to trigger spark_transform.py