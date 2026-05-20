import os
import logging
import time
from datetime import datetime
from pathlib import Path

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
def get_connection_string() -> str:
    """Build MSSQL connection string from environment variables."""
    server   = os.getenv("MSSQL_HOST", "mssql")
    port     = os.getenv("MSSQL_PORT", "1433")
    user     = os.getenv("MSSQL_USER", "sa")
    password = os.getenv("MSSQL_PASSWORD", "MovieLens@2024")
    database = os.getenv("MSSQL_DB",   "MovieLensDB")
    driver   = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")

    return (
        f"mssql+pyodbc://{user}:{password}@{server}:{port}/{database}"
        f"?driver={driver.replace(' ', '+')}"
        f"&TrustServerCertificate=yes"
        f"&Encrypt=yes"
    )


def get_engine(retries: int = 10, delay: int = 6):
    """Return a SQLAlchemy engine, retrying until MSSQL is ready."""
    conn_str = get_connection_string()
    for attempt in range(1, retries + 1):
        try:
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
