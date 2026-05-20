from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED_CSV = {
    "movies.csv": ["movieId", "title", "genres"],
    "ratings.csv": ["userId", "movieId", "rating", "timestamp"],
    "tags.csv": ["userId", "movieId", "tag", "timestamp"],
    "links.csv": ["movieId", "imdbId", "tmdbId"],
    "genome-tags.csv": ["tagId", "tag"],
    "genome-scores.csv": ["movieId", "tagId", "relevance"],
}


def _data_dir() -> Path:
    for candidate in (
        ROOT / "project" / "data",
        ROOT / "final_integrated_project" / "data",
        ROOT / "MovieLens Dataset",
    ):
        if (candidate / "movies.csv").exists():
            return candidate
    pytest.skip("MovieLens CSV data directory not found")


def test_required_files_exist():
    data = _data_dir()
    for filename in REQUIRED_CSV:
        assert (data / filename).exists(), f"Missing {filename}"


def test_movies_header():
    import pandas as pd

    data = _data_dir()
    df = pd.read_csv(data / "movies.csv", nrows=5)
    for col in REQUIRED_CSV["movies.csv"]:
        assert col in df.columns
