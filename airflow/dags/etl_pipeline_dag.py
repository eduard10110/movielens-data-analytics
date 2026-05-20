from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

# Logging
log = logging.getLogger(__name__)

# Default DAG arguments
DEFAULT_ARGS = {
    "owner":            "team6",
    "depends_on_past":  False,
    "email_on_failure": False,
    "email_on_retry":   False,
    "retries":          3,
    "retry_delay":      timedelta(minutes=5),
    "start_date":       datetime(2024, 1, 1),
}

APP_DIR = Path(os.getenv("APP_DIR", "/app"))

# Helper – add app directory to sys.path so we can import ETL modules
def _ensure_app_on_path():
    app_str = str(APP_DIR)
    if app_str not in sys.path:
        sys.path.insert(0, app_str)
    log.info("APP_DIR on sys.path: %s", app_str)


# Task callables
def task_extract(**context):
    """Extract all raw CSV files from the MovieLens dataset."""
    _ensure_app_on_path()
    from extract import run_extract          # noqa: PLC0415
    raw = run_extract()
    log.info("Extract complete. Tables: %s", list(raw.keys()))
    # Push to XCom so downstream tasks can use row counts for monitoring
    context["ti"].xcom_push(key="row_counts", value={k: len(v) for k, v in raw.items()})
    # Store raw data in a temp location to avoid re-reading in transform
    import pickle, tempfile
    tmp = tempfile.mktemp(suffix=".pkl")
    with open(tmp, "wb") as f:
        pickle.dump(raw, f)
    context["ti"].xcom_push(key="raw_pickle_path", value=tmp)
    log.info("Raw data pickled at %s", tmp)


def task_transform(**context):
    """Clean, normalize and reshape the raw data."""
    _ensure_app_on_path()
    import pickle
    from transform import run_transform    

    raw_path = context["ti"].xcom_pull(task_ids="extract_task", key="raw_pickle_path")
    if raw_path and Path(raw_path).exists():
        with open(raw_path, "rb") as f:
            raw = pickle.load(f)
        log.info("Loaded raw data from pickle: %s", raw_path)
    else:
        from extract import run_extract
        log.warning("Pickle not found – re-running extract.")
        raw = run_extract()

    transformed = run_transform(raw)
    log.info("Transform complete. Tables: %s", list(transformed.keys()))

    import tempfile
    tmp = tempfile.mktemp(suffix=".pkl")
    with open(tmp, "wb") as f:
        pickle.dump(transformed, f)
    context["ti"].xcom_push(key="transformed_pickle_path", value=tmp)
    context["ti"].xcom_push(key="row_counts", value={k: len(v) for k, v in transformed.items()})
    log.info("Transformed data pickled at %s", tmp)


def task_load(**context):
    """Bulk-insert cleaned DataFrames into MSSQL."""
    _ensure_app_on_path()
    import pickle
    from load import run_load                # noqa: PLC0415

    transformed_path = context["ti"].xcom_pull(
        task_ids="transform_task", key="transformed_pickle_path"
    )
    if transformed_path and Path(transformed_path).exists():
        with open(transformed_path, "rb") as f:
            transformed = pickle.load(f)
        log.info("Loaded transformed data from pickle: %s", transformed_path)
    else:
        from extract import run_extract
        from transform import run_transform
        log.warning("Pickle not found – re-running extract+transform.")
        transformed = run_transform(run_extract())

    run_load(transformed)
    log.info("Load complete – all tables written to MSSQL.")


def task_run_sql_analysis(**context):
    """Execute analytical queries and log results."""
    _ensure_app_on_path()
    import pandas as pd
    from utils import get_engine             # noqa: PLC0415
    from sqlalchemy import text

    engine = get_engine()

    queries = {
        "top_rated_movies": """
            SELECT TOP 10
                m.title,
                COUNT(r.ratingId) AS total_ratings,
                ROUND(AVG(CAST(r.rating AS FLOAT)), 3) AS avg_rating
            FROM dbo.movies m
            JOIN dbo.ratings r ON r.movieId = m.movieId
            GROUP BY m.title
            HAVING COUNT(r.ratingId) >= 200
            ORDER BY avg_rating DESC
        """,
        "top_genres": """
            SELECT
                g.genreName,
                COUNT(r.ratingId) AS total_ratings,
                ROUND(AVG(CAST(r.rating AS FLOAT)), 3) AS avg_rating
            FROM dbo.genres g
            JOIN dbo.movie_genres mg ON mg.genreId = g.genreId
            JOIN dbo.ratings r ON r.movieId = mg.movieId
            GROUP BY g.genreName
            ORDER BY total_ratings DESC
        """,
        "rating_by_year": """
            SELECT
                YEAR(rating_date) AS yr,
                COUNT(*) AS total,
                ROUND(AVG(CAST(rating AS FLOAT)), 3) AS avg_r
            FROM dbo.ratings
            GROUP BY YEAR(rating_date)
            ORDER BY yr
        """,
    }

    with engine.connect() as conn:
        for name, sql in queries.items():
            try:
                df = pd.read_sql(text(sql), conn)
                log.info("Analysis [%s]:\n%s", name, df.to_string(index=False))
                context["ti"].xcom_push(key=name, value=df.to_dict(orient="records"))
            except Exception as exc:
                log.error("Query [%s] failed: %s", name, exc)


# DAG definition
with DAG(
    dag_id="movielens_etl_pipeline",
    description="MovieLens ETL: Extract → Transform → Load → SQL Analytics",
    schedule_interval="@weekly",
    default_args=DEFAULT_ARGS,
    catchup=False,
    max_active_runs=1,
    tags=["movielens", "etl", "team6"],
    doc_md="""
## MovieLens ETL Pipeline

**Team**: Group 6  
**Purpose**: Ingests the MovieLens dataset into Microsoft SQL Server via a
full Extract → Transform → Load pipeline orchestrated by Apache Airflow.

### Tasks
| Task | Description |
|------|-------------|
| `extract_task`      | Read raw CSV files |
| `transform_task`    | Clean and normalise data |
| `load_task`         | Bulk-insert into MSSQL |
| `run_sql_analysis`  | Execute analytical SQL queries |
    """,
) as dag:

    start = EmptyOperator(task_id="start")
    end   = EmptyOperator(task_id="end", trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS)

    extract_task = PythonOperator(
        task_id="extract_task",
        python_callable=task_extract,
        doc_md="Read and validate all MovieLens CSV files.",
    )

    transform_task = PythonOperator(
        task_id="transform_task",
        python_callable=task_transform,
        doc_md="Clean, normalize genres, convert timestamps, validate FK integrity.",
    )

    load_task = PythonOperator(
        task_id="load_task",
        python_callable=task_load,
        doc_md="Bulk-insert all cleaned DataFrames into MSSQL.",
    )

    sql_analysis_task = PythonOperator(
        task_id="run_sql_analysis",
        python_callable=task_run_sql_analysis,
        doc_md="Run advanced analytical SQL queries and push results to XCom.",
    )

    start >> extract_task >> transform_task >> load_task >> sql_analysis_task >> end
