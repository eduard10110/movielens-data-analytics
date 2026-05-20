import pandas as pd
from pathlib import Path
from typing import Dict

from utils import get_logger, resolve_data_dir, validate_files, log_dataframe_info, timer

logger = get_logger("extract")


@timer
def extract_movies(path: Path) -> pd.DataFrame:
    """Read movies.csv and perform initial validation."""
    logger.info("Extracting movies from %s", path)
    df = pd.read_csv(path, dtype={"movieId": int, "title": str, "genres": str})
    log_dataframe_info(df, "movies")
    assert "movieId" in df.columns, "movies.csv missing 'movieId'"
    assert "title"   in df.columns, "movies.csv missing 'title'"
    assert "genres"  in df.columns, "movies.csv missing 'genres'"
    return df


@timer
def extract_ratings(path: Path, chunksize: int = 500_000) -> pd.DataFrame:
    """
    Read ratings.csv in chunks to handle large files (33 M+ rows).
    Returns a consolidated DataFrame.
    """
    logger.info("Extracting ratings from %s (chunk=%d)", path, chunksize)
    chunks = []
    for chunk in pd.read_csv(
        path,
        dtype={"userId": int, "movieId": int, "rating": float, "timestamp": int},
        chunksize=chunksize,
    ):
        chunks.append(chunk)
    df = pd.concat(chunks, ignore_index=True)
    log_dataframe_info(df, "ratings")
    return df


@timer
def extract_tags(path: Path) -> pd.DataFrame:
    """Read tags.csv."""
    logger.info("Extracting tags from %s", path)
    df = pd.read_csv(
        path,
        dtype={"userId": int, "movieId": int, "tag": str, "timestamp": int},
    )
    log_dataframe_info(df, "tags")
    return df


@timer
def extract_links(path: Path) -> pd.DataFrame:
    """Read links.csv."""
    logger.info("Extracting links from %s", path)
    df = pd.read_csv(path, dtype=str)
    df["movieId"] = pd.to_numeric(df["movieId"], errors="coerce")
    log_dataframe_info(df, "links")
    return df


@timer
def extract_genome_tags(path: Path) -> pd.DataFrame:
    """Read genome-tags.csv."""
    logger.info("Extracting genome-tags from %s", path)
    df = pd.read_csv(path, dtype={"tagId": int, "tag": str})
    log_dataframe_info(df, "genome_tags")
    return df


@timer
def extract_genome_scores(path: Path, chunksize: int = 500_000) -> pd.DataFrame:
    """Read genome-scores.csv in chunks."""
    logger.info("Extracting genome-scores from %s (chunk=%d)", path, chunksize)
    chunks = []
    for chunk in pd.read_csv(
        path,
        dtype={"movieId": int, "tagId": int, "relevance": float},
        chunksize=chunksize,
    ):
        chunks.append(chunk)
    df = pd.concat(chunks, ignore_index=True)
    log_dataframe_info(df, "genome_scores")
    return df


def run_extract() -> Dict[str, pd.DataFrame]:
    """
    Main extraction entry point.
    Returns a dict of raw DataFrames keyed by table name.
    """
    data_dir = resolve_data_dir()
    paths    = validate_files(data_dir)

    raw = {
        "movies":        extract_movies(paths["movies"]),
        "ratings":       extract_ratings(paths["ratings"]),
        "tags":          extract_tags(paths["tags"]),
        "links":         extract_links(paths["links"]),
        "genome_tags":   extract_genome_tags(paths["genome_tags"]),
        "genome_scores": extract_genome_scores(paths["genome_scores"]),
    }

    logger.info("Extraction complete. Tables: %s", list(raw.keys()))
    return raw


if __name__ == "__main__":
    data = run_extract()
    for k, df in data.items():
        print(f"{k}: {df.shape}")
