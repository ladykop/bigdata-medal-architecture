# Plateforme Big Data : Analyse Médiatique (Architecture Médaillon)

Cette plateforme met en place une architecture Big Data distribuée permettant de collecter, transformer et analyser des articles de presse issus de sources marocaines (**Hespress, Akhbarona, Barlamane**) et internationales (**CNN, BBC, Al Jazeera, Reuters**).

L’objectif est de couvrir l’ensemble du cycle de vie de la donnée, depuis l’ingestion brute jusqu’à l’analyse décisionnelle, en s’appuyant sur des standards industriels modernes.

---

## Architecture du Système

La solution repose sur une **architecture médaillon** (Multi-Layer Data Lake) afin de garantir la qualité, la fiabilité et la traçabilité des données :

1. **Ingestion (Bronze)**
   Collecte automatisée via un scraper Python (BeautifulSoup / Requests).
   Stockage des données au format **JSON brut**.

2. **Transformation (Silver)**
   Nettoyage (suppression HTML), normalisation du texte et déduplication avec **Apache Spark**.
   Stockage au format optimisé **Parquet**.

3. **Analytique (Gold)**
   Agrégation des indicateurs clés (KPIs) et structuration pour le reporting.
   Stockage dans un Data Warehouse **PostgreSQL**.

4. **Orchestration**
   Automatisation, planification et supervision des workflows avec **Apache Airflow**.

---

## Stack Technique

* **Infrastructure** : Docker & Docker Compose
* **Data Lake** : MinIO (compatible Amazon S3)
* **Traitement Big Data** : PySpark (Spark 3.4.1)
* **Orchestration** : Apache Airflow
* **Data Warehouse** : PostgreSQL 13
* **Langages** : Python, SQL, Java (JDBC)

---

## Structure du Projet

```text
pfe_bigdata/
├── Dockerfile              # Image Spark personnalisée (Drivers S3 & JDBC inclus)
├── docker-compose.yml      # Orchestration de l'infrastructure
├── requirements.txt        # Dépendances Python
├── airflow/
│   └── dags/
│       └── news_pipeline.py
├── scripts/
│   ├── scraper.py          # Collecte multi-sources
│   └── spark_transform.py  # Transformation (architecture médaillon)
└── README.md               # Documentation
```

---

## Guide de Démarrage

### 1. Lancement de l'infrastructure

```bash
docker-compose up --build -d
```

### 2. Vérification des conteneurs

```bash
docker ps
```

Les services suivants doivent être actifs :

* postgres
* minio
* spark-master
* spark-worker
* airflow

### 3. Configuration du Data Lake (MinIO)

1. Accéder à : http://localhost:9001
2. Identifiants : `admin / admin`
3. Créer les buckets suivants :

   * `bronze`
   * `silver`
   * `gold`

### 4. Configuration d'Airflow

1. Accéder à : http://localhost:8080
2. Identifiants : `airflow / airflow`
3. Aller dans **Admin → Connections**
4. Ajouter une connexion `spark_default` :

   * Conn Type : Spark
   * Host : spark://spark-master
   * Port : 7077

---

### 5. Exécution du Pipeline

1. Activer le DAG `pfe_news_pipeline`
2. Cliquer sur **Trigger DAG**

---

## Flux de Données (Workflow)

1. **Bronze :**
   Le scraper collecte les articles et génère un fichier JSON brut (`news_raw.json`).

2. **Silver :**
   Spark nettoie et transforme les données, puis les stocke en Parquet.

3. **Gold :**
   Spark agrège les données (ex : nombre d’articles par source) et les charge dans PostgreSQL.

---

## Vérification des Résultats

Connexion à PostgreSQL :

```bash
docker exec -it pfe_bigdata-postgres-1 psql -U admin -d data_warehouse
```

Exécution de la requête :

```sql
SELECT * FROM kpi_articles_count;
```