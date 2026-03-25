# Big Data Platform: Media Analysis (Medallion Architecture)

This platform implements a distributed Big Data architecture designed to collect, process, and analyze news articles from Moroccan sources (**Hespress, Akhbarona, Barlamane**) as well as international outlets (**CNN, BBC, Al Jazeera, Reuters**).

The goal is to cover the full data lifecycle—from raw ingestion to business intelligence—using modern industry standards.

---

## System Architecture

The solution is built on a **Medallion Architecture** (Multi-Layer Data Lake) to ensure data quality, reliability, and traceability:

1. **Ingestion (Bronze)**
   Automated data collection using a Python scraper (BeautifulSoup / Requests).
   Data is stored in **raw JSON format**.

2. **Transformation (Silver)**
   Data cleaning (HTML removal), text normalization, and deduplication using **Apache Spark**.
   Data is stored in optimized **Parquet format**.

3. **Analytics (Gold)**
   Aggregation of key performance indicators (KPIs) and preparation for reporting.
   Data is stored in a **PostgreSQL** data warehouse.

4. **Orchestration**
   Workflow automation, scheduling, and monitoring using **Apache Airflow**.

---

## Tech Stack

* **Infrastructure**: Docker & Docker Compose
* **Data Lake**: MinIO (Amazon S3 compatible)
* **Big Data Processing**: PySpark (Spark 3.4.1)
* **Orchestration**: Apache Airflow
* **Data Warehouse**: PostgreSQL 13
* **Languages**: Python, SQL, Java (JDBC)

---

## Project Structure

```text
pfe_bigdata/
├── Dockerfile              # Custom Spark image (S3 & JDBC drivers included)
├── docker-compose.yml      # Infrastructure orchestration
├── requirements.txt        # Python dependencies
├── airflow/
│   └── dags/
│       └── news_pipeline.py
├── scripts/
│   ├── scraper.py          # Multi-source data collection
│   └── spark_transform.py  # Medallion transformation logic
└── README.md               # Documentation
```

---

## Getting Started

### 1. Start the Infrastructure

```bash
docker-compose up --build -d
```

### 2. Verify Running Containers

```bash
docker ps
```

The following services should be running:

* postgres
* minio
* spark-master
* spark-worker
* airflow

---

### 3. Configure Data Lake (MinIO)

1. Open: http://localhost:9001
2. Credentials: `admin / admin`
3. Create the following buckets:

   * `bronze`
   * `silver`
   * `gold`

---

### 4. Configure Airflow

1. Open: http://localhost:8080
2. Credentials: `airflow / airflow`
3. Navigate to **Admin → Connections**
4. Add a connection named `spark_default`:

   * Conn Type: Spark
   * Host: spark://spark-master
   * Port: 7077

---

### 5. Run the Pipeline

1. Enable the DAG `pfe_news_pipeline`
2. Click **Trigger DAG**

---

## Data Workflow

1. **Bronze**
   The scraper collects articles and generates a raw JSON file (`news_raw.json`).

2. **Silver**
   Spark cleans and transforms the data, then stores it in Parquet format.

3. **Gold**
   Spark aggregates the data (e.g., number of articles per source) and loads it into PostgreSQL.

---

## Verify Results

Connect to PostgreSQL:

```bash
docker exec -it pfe_bigdata-postgres-1 psql -U admin -d data_warehouse
```

Run the query:

```sql
SELECT * FROM kpi_articles_count;
```
