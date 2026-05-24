import os
import logging
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Logging
def get_logger(name: str) -> logging.Logger:
    """Return a consistently configured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


logger = get_logger("utils")

# Database connection
def get_connection_string(database: str | None = None) -> str:
    """Build MSSQL connection string from environment variables."""
    server   = os.getenv("MSSQL_HOST", "mssql")
    port     = os.getenv("MSSQL_PORT", "1433")
    user     = os.getenv("MSSQL_USER", "sa")
    password = os.getenv("MSSQL_PASSWORD", "MovieLens@2024")
    database = database or os.getenv("MSSQL_DB", "MovieLensDB")
    driver   = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")

    user_q = quote_plus(user)
    pass_q = quote_plus(password)
    driver_q = quote_plus(driver)

    return (
        f"mssql+pyodbc://{user_q}:{pass_q}@{server}:{port}/{database}"
        f"?driver={driver_q}"
        f"&TrustServerCertificate=yes"
        f"&Encrypt=yes"
    )


def ensure_database_exists() -> None:
    """Create MovieLensDB on the server if mssql-init has not run yet."""
    target_db = os.getenv("MSSQL_DB", "MovieLensDB")
    master_engine = create_engine(
        get_connection_string("master"),
        fast_executemany=True,
        isolation_level="AUTOCOMMIT",
    )
    with master_engine.connect() as conn:
        conn.execute(
            text(
                f"IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'{target_db}') "
                f"CREATE DATABASE [{target_db}]"
            )
        )
    logger.info("Database '%s' is ready.", target_db)


def get_engine(retries: int = 10, delay: int = 6):
    """Return a SQLAlchemy engine, retrying until MSSQL is ready."""
    target_db = os.getenv("MSSQL_DB", "MovieLensDB")

    for attempt in range(1, retries + 1):
        try:
            ensure_database_exists()
            conn_str = get_connection_string(target_db)
            engine = create_engine(conn_str, fast_executemany=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Connected to MSSQL successfully.")
            return engine
        except Exception as exc:
            logger.warning(
                "MSSQL not ready (attempt %d/%d): %s", attempt, retries, exc
            )
            if attempt < retries:
                time.sleep(delay)
    raise RuntimeError("Could not connect to MSSQL after multiple retries.")


def get_sample_size() -> int:
    """Max rows to load from large CSV files (random sample)."""
    return int(os.getenv("SAMPLE_ROWS", "500000"))


def sample_csv_random(path: Path, dtype: dict, sample_size: int | None = None) -> pd.DataFrame:
    """
    Return a uniform random sample of rows from a large CSV (single pass after line count).
    """
    sample_size = sample_size or get_sample_size()
    seed = int(os.getenv("SAMPLE_SEED", "42"))
    chunksize = int(os.getenv("SAMPLE_CHUNK_SIZE", "500000"))

    logger.info("Random sample target: %d rows from %s", sample_size, path.name)

    with open(path, encoding="utf-8") as f:
        next(f)
        total = sum(1 for _ in f)

    if total <= sample_size:
        logger.info("File has %d rows — loading all.", total)
        return pd.read_csv(path, dtype=dtype)

    rng = np.random.default_rng(seed)
    pick = set(rng.choice(total, size=sample_size, replace=False).tolist())

    parts: list[pd.DataFrame] = []
    idx = 0
    for chunk in pd.read_csv(path, dtype=dtype, chunksize=chunksize):
        mask = [idx + i in pick for i in range(len(chunk))]
        idx += len(chunk)
        selected = chunk.iloc[mask]
        if not selected.empty:
            parts.append(selected)

    df = pd.concat(parts, ignore_index=True)
    logger.info("Sampled %d rows from %d total.", len(df), total)
    return df


def resolve_data_dir() -> Path:
    """Find the MovieLens dataset directory."""
    candidates = [
        Path(os.getenv("DATA_DIR", "data")),
        Path(__file__).parent.parent / "data",
        Path("/data"),
        Path("/Users/eduardgabrielyan/Desktop/kursayin/MovieLens Dataset"),
    ]
    for path in candidates:
        if path.exists() and any(path.glob("*.csv")):
            logger.info("Dataset directory found: %s", path)
            return path
    raise FileNotFoundError(
        f"No CSV files found in any candidate directory: {candidates}"
    )


REQUIRED_FILES = {
    "movies":        ("movies.csv",       ["movieId", "title", "genres"]),
    "ratings":       ("ratings.csv",      ["userId", "movieId", "rating", "timestamp"]),
    "tags":          ("tags.csv",         ["userId", "movieId", "tag", "timestamp"]),
    "links":         ("links.csv",        ["movieId", "imdbId", "tmdbId"]),
    "genome_tags":   ("genome-tags.csv",  ["tagId", "tag"]),
    "genome_scores": ("genome-scores.csv",["movieId", "tagId", "relevance"]),
}


def validate_files(data_dir: Path) -> dict:
    """Return a mapping name→Path for each required CSV file."""
    paths = {}
    for name, (filename, _) in REQUIRED_FILES.items():
        fpath = data_dir / filename
        if not fpath.exists():
            raise FileNotFoundError(f"Required file missing: {fpath}")
        paths[name] = fpath
        logger.info("Validated: %s (%s)", filename, fpath)
    return paths


def log_dataframe_info(df, name: str):
    """Log shape, dtypes and missing-value summary for a DataFrame."""
    logger.info(
        "[%s] shape=%s  nulls=%d  dupes=%d",
        name, df.shape, df.isnull().sum().sum(), df.duplicated().sum(),
    )


def timer(func):
    """Decorator that logs execution time of a function."""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info("%s finished in %.2f s", func.__name__, elapsed)
        return result
    return wrapper
