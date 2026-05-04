# Big Data Platform: News Media Analysis
## Medallion Architecture Implementation

This project implements a complete Big Data pipeline that scrapes, processes, and analyzes news from Moroccan and International sources. It follows the **Medallion Architecture** (Bronze → Silver → Gold) to ensure data quality and reliability.

---

## 1. System Overview

The platform uses a multi-layer data lake approach:

*   **Bronze (Raw)**: `scripts/scraper.py` collects news via RSS (BBC, CNN, Al Jazeera, Reuters) and specialized HTML scraping (Hespress, Akhbarona, Barlamane). Data is stored as raw JSON in MinIO.
*   **Silver (Cleaned)**: `scripts/spark_transform.py` (using Pandas) cleans HTML tags, normalizes text, and filters out low-quality records. Stored as Parquet.
*   **Gold (Aggregated)**: The transformation script calculates KPIs (like article counts per source) and saves them as Parquet and into PostgreSQL for analysis.
*   **Orchestration**: Apache Airflow manages the workflow, running the scraper and then the transformation hourly.

---

## 2. Infrastructure Setup

### Start the platform
Run this command from the project root:
```bash
docker-compose up -d
```

### Verify containers
Ensure these 4 services are running (`docker ps`):
1.  **Airflow**: Workflow orchestration (Port 8080)
2.  **MinIO**: S3-compatible Data Lake (Ports 9000/9001)
3.  **PostgreSQL**: Data Warehouse (Port 5432)
4.  **Kafka**: Real-time streaming (Port 9092)

---

## 3. First-Time Configuration

### Create MinIO Bucket
1.  Open **http://localhost:9001** (Login: `admin` / `password123`).
2.  Create a bucket named: `news-bucket`.

### Access Airflow
1.  Open **http://localhost:8080** (Username: `admin`).
2.  Get your dynamic password:
    ```bash
    docker exec -it bigdata-architecture-airflow-1 cat /opt/airflow/standalone_admin_password.txt
    ```
3.  Turn **ON** the `bdarch_news_pipeline` DAG and click **Trigger DAG**.

---

## 4. Maintenance & Data Management

Use these commands to manage your data and fix common issues.

### Clear/Reset the Pipeline (Truncate)
If you want to wipe the data and start a fresh scrape (e.g., to fix encoding or duplicates):

**Wipe PostgreSQL Tables:**
```powershell
docker exec bigdata-architecture-postgres-1 psql -U airflow -d airflow -c "TRUNCATE news_articles, kpi_articles_count;"
```

**Clear MinIO Bronze Storage:**
```powershell
docker exec bigdata-architecture-airflow-1 python -c "import boto3; s3=boto3.resource('s3', endpoint_url='http://minio:9000',  aws_access_key_id='admin', aws_secret_access_key='password123'); s3.Bucket('news-bucket').objects.filter(Prefix='bronze/').delete()"
```

---

## 5. Exporting Data (Arabic Fixed)

To export your results to your local machine with correct Arabic character support, run these PowerShell commands:

### Export to CSV (Recommended)
```powershell
# Set terminal to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Export Detail (Articles)
docker exec bigdata-architecture-postgres-1 psql -U airflow -d airflow -c "\copy news_articles TO STDOUT WITH CSV HEADER" | Out-File -Encoding utf8 news_articles.csv

# Export Aggregates (KPIs)
docker exec bigdata-architecture-postgres-1 psql -U airflow -d airflow -c "\copy kpi_articles_count TO STDOUT WITH CSV HEADER" | Out-File -Encoding utf8 kpi_articles_count.csv
```

### Export to Text File (Table View)
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

docker exec bigdata-architecture-postgres-1 psql -U airflow -d airflow -c "SELECT source, date_publication, title, url FROM news_articles;" | Out-File -Encoding utf8 news_articles_view.txt
```

---

## 6. Project Structure

*   `dags/news_pipeline.py`: Airflow DAG definition and task logic.
*   `scripts/scraper.py`: Logic for RSS and specialized HTML scraping.
*   `scripts/spark_transform.py`: Data cleaning and SQL loading logic.
*   `docker-compose.yaml`: Container infrastructure configuration.
