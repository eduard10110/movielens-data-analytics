import re
import pandas as pd
from typing import Dict
from utils import get_logger, log_dataframe_info, timer

logger = get_logger("transform")

# Constants
KNOWN_GENRES = {
    "Action", "Adventure", "Animation", "Children", "Comedy", "Crime",
    "Documentary", "Drama", "Fantasy", "Film-Noir", "Horror", "Musical",
    "Mystery", "Romance", "Sci-Fi", "Thriller", "War", "Western", "IMAX",
    "(no genres listed)",
}

RATING_MIN = 0.5
RATING_MAX = 5.0


# Movies
def _extract_year(title: str) -> int | None:
    """Parse the 4-digit year from the movie title string, e.g. 'Toy Story (1995)'."""
    match = re.search(r"\((\d{4})\)\s*$", str(title))
    if match:
        year = int(match.group(1))
        if 1888 <= year <= 2030:
            return year
    return None


def _clean_title(title: str) -> str:
    """Strip trailing year and extra whitespace from title."""
    return re.sub(r"\s*\(\d{4}\)\s*$", "", str(title)).strip()


@timer
def transform_movies(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    logger.info("Transforming movies (%d rows)...", len(df))

    df = df.drop_duplicates(subset=["movieId"])
    df["title"]        = df["title"].str.strip()
    df["genres"]       = df["genres"].fillna("(no genres listed)").str.strip()
    df["release_year"] = df["title"].apply(_extract_year)
    df["clean_title"]  = df["title"].apply(_clean_title)

    genre_rows = []
    for _, row in df.iterrows():
        for genre in row["genres"].split("|"):
            genre = genre.strip()
            if genre:
                genre_rows.append({"movieId": row["movieId"], "genre": genre})

    movie_genres = pd.DataFrame(genre_rows).drop_duplicates()
    movie_genres = movie_genres[movie_genres["genre"].isin(KNOWN_GENRES)]

    movies_clean = df[["movieId", "clean_title", "release_year"]].rename(
        columns={"clean_title": "title"}
    )

    log_dataframe_info(movies_clean, "movies_clean")
    log_dataframe_info(movie_genres, "movie_genres")
    return movies_clean, movie_genres


# Genres master table
def build_genres_table(movie_genres: pd.DataFrame) -> pd.DataFrame:
    """Create a distinct genres lookup table with surrogate keys."""
    genres = (
        movie_genres["genre"]
        .drop_duplicates()
        .reset_index(drop=True)
        .reset_index()
        .rename(columns={"index": "genreId", "genre": "genreName"})
    )
    genres["genreId"] = genres["genreId"] + 1  # 1-based PK
    logger.info("Genres master table: %d genres", len(genres))
    return genres


# Ratings
def transform_ratings_chunk(df: pd.DataFrame, valid_movie_ids: set) -> pd.DataFrame:
    """Clean and validate one ratings chunk."""
    df = df.drop_duplicates(subset=["userId", "movieId", "timestamp"])
    df = df.dropna(subset=["userId", "movieId", "rating", "timestamp"])

    # Domain validation
    df = df[(df["rating"] >= RATING_MIN) & (df["rating"] <= RATING_MAX)]

    # Remove ratings for movies not in movies table
    df = df[df["movieId"].isin(valid_movie_ids)]

    # Convert Unix timestamp → datetime
    df["rating_date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_localize(None)

    return df[["userId", "movieId", "rating", "rating_date"]].copy()


@timer
def transform_ratings(df: pd.DataFrame, valid_movie_ids: set) -> pd.DataFrame:
    """Clean and validate ratings (full DataFrame)."""
    logger.info("Transforming ratings (%d rows)...", len(df))
    out = transform_ratings_chunk(df, valid_movie_ids)
    log_dataframe_info(out, "ratings_clean")
    return out


# Tags
@timer
def transform_tags(df: pd.DataFrame, valid_movie_ids: set) -> pd.DataFrame:
    """Clean tags."""
    logger.info("Transforming tags (%d rows)...", len(df))

    df = df.drop_duplicates()
    df = df.dropna(subset=["userId", "movieId", "tag"])

    df["tag"] = df["tag"].str.strip().str.lower()
    df = df[df["tag"].str.len() > 0]
    df = df[df["movieId"].isin(valid_movie_ids)]

    df["tag_date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_localize(None)
    df = df[["userId", "movieId", "tag", "tag_date"]].copy()

    log_dataframe_info(df, "tags_clean")
    return df


# Links
@timer
def transform_links(df: pd.DataFrame, valid_movie_ids: set) -> pd.DataFrame:
    """Clean links table."""
    logger.info("Transforming links (%d rows)...", len(df))

    df = df.drop_duplicates(subset=["movieId"])
    df = df.dropna(subset=["movieId"])
    df["movieId"] = pd.to_numeric(df["movieId"], errors="coerce")
    df = df.dropna(subset=["movieId"])
    df["movieId"] = df["movieId"].astype(int)
    df = df[df["movieId"].isin(valid_movie_ids)]

    df["imdbId"] = df["imdbId"].fillna("").astype(str).str.strip()
    df["tmdbId"] = df["tmdbId"].fillna("").astype(str).str.strip()

    log_dataframe_info(df, "links_clean")
    return df[["movieId", "imdbId", "tmdbId"]]


# Genome
@timer
def transform_genome_tags(df: pd.DataFrame) -> pd.DataFrame:
    """Clean genome tags."""
    df = df.drop_duplicates(subset=["tagId"])
    df["tag"] = df["tag"].str.strip()
    log_dataframe_info(df, "genome_tags_clean")
    return df


def transform_genome_scores_chunk(
    df: pd.DataFrame, valid_movie_ids: set, valid_tag_ids: set
) -> pd.DataFrame:
    """Clean one genome-scores chunk."""
    df = df.drop_duplicates()
    df = df[(df["relevance"] >= 0.0) & (df["relevance"] <= 1.0)]
    df = df[df["movieId"].isin(valid_movie_ids)]
    return df[df["tagId"].isin(valid_tag_ids)]


@timer
def transform_genome_scores(df: pd.DataFrame, valid_movie_ids: set, valid_tag_ids: set) -> pd.DataFrame:
    """Clean genome scores (full DataFrame)."""
    logger.info("Transforming genome scores (%d rows)...", len(df))
    out = transform_genome_scores_chunk(df, valid_movie_ids, valid_tag_ids)
    log_dataframe_info(out, "genome_scores_clean")
    return out


# Main entry point
def run_transform(raw: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Execute all transform steps and return cleaned DataFrames.
    """
    logger.info("=== Transform phase started ===")

    movies_clean, movie_genres_raw = transform_movies(raw["movies"])
    valid_movie_ids = set(movies_clean["movieId"])

    genres_master = build_genres_table(movie_genres_raw)

    genre_name_to_id = dict(zip(genres_master["genreName"], genres_master["genreId"]))
    movie_genres_raw["genreId"] = movie_genres_raw["genre"].map(genre_name_to_id)
    movie_genres_clean = movie_genres_raw[["movieId", "genreId"]].dropna().astype(int)

    ratings_clean = transform_ratings(raw["ratings"], valid_movie_ids)
    tags_clean    = transform_tags(raw["tags"],    valid_movie_ids)
    links_clean   = transform_links(raw["links"],  valid_movie_ids)

    genome_tags_clean   = transform_genome_tags(raw["genome_tags"])
    valid_tag_ids       = set(genome_tags_clean["tagId"])
    genome_scores_clean = transform_genome_scores(
        raw["genome_scores"], valid_movie_ids, valid_tag_ids
    )

    transformed = {
        "movies":        movies_clean,
        "genres":        genres_master,
        "movie_genres":  movie_genres_clean,
        "ratings":       ratings_clean,
        "tags":          tags_clean,
        "links":         links_clean,
        "genome_tags":   genome_tags_clean,
        "genome_scores": genome_scores_clean,
    }

    logger.info("=== Transform phase complete. Tables: %s ===", list(transformed.keys()))
    for name, df in transformed.items():
        logger.info("  %s: %s rows", name, len(df))

    return transformed


if __name__ == "__main__":
    from extract import run_extract
    raw = run_extract()
    cleaned = run_transform(raw)
    for k, df in cleaned.items():
        print(f"{k}: {df.shape}")
