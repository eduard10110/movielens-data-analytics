import pandas as pd
from sqlalchemy import text
from typing import Dict

from utils import get_logger, get_engine, timer

logger = get_logger("load")

LOAD_ORDER = [
    "movies",
    "genres",
    "movie_genres",
    "links",
    "genome_tags",
    "genome_scores",
    "ratings",
    "tags",
]

CHUNK_SIZE = 5_000


@timer
def ensure_schema(engine) -> None:
    """Execute schema.sql DDL to create tables if they don't exist."""
    from pathlib import Path

    schema_candidates = [
        Path(__file__).parent.parent / "sql" / "schema.sql",
        Path(__file__).parent.parent.parent / "team_member_2_database_design" / "sql" / "schema.sql",
        Path(__file__).parent.parent.parent / "final_integrated_project" / "sql" / "schema.sql",
        Path("/sql/schema.sql"),
        Path("/app/sql/schema.sql"),
    ]
    schema_path = None
    for p in schema_candidates:
        if p.exists():
            schema_path = p
            break

    if schema_path is None:
        logger.warning("schema.sql not found – skipping DDL creation.")
        return

    logger.info("Executing schema DDL from %s", schema_path)
    ddl = schema_path.read_text(encoding="utf-8")

    statements = [s.strip() for s in ddl.split("GO") if s.strip()]
    with engine.begin() as conn:
        for stmt in statements:
            if stmt:
                try:
                    conn.execute(text(stmt))
                except Exception as exc:
                    logger.warning("DDL statement warning (may be OK): %s", exc)

    logger.info("Schema DDL executed successfully.")


@timer
def truncate_tables(engine) -> None:
    """Truncate all target tables (respecting FK order)."""
    truncate_order = list(reversed(LOAD_ORDER))
    with engine.begin() as conn:
        conn.execute(text("EXEC sp_MSforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL'"))
        for table in truncate_order:
            try:
                conn.execute(text(f"TRUNCATE TABLE dbo.{table}"))
                logger.info("Truncated table: %s", table)
            except Exception as exc:
                logger.warning("Could not truncate %s: %s", table, exc)
        conn.execute(text("EXEC sp_MSforeachtable 'ALTER TABLE ? CHECK CONSTRAINT ALL'"))


@timer
def load_table(engine, table_name: str, df: pd.DataFrame) -> None:
    """Bulk-insert a DataFrame into an MSSQL table using pandas to_sql."""
    if df.empty:
        logger.warning("DataFrame for '%s' is empty – skipping.", table_name)
        return

    total = len(df)
    logger.info("Loading %d rows into [dbo].[%s]...", total, table_name)

    df.to_sql(
        name=table_name,
        con=engine,
        schema="dbo",
        if_exists="append",
        index=False,
        chunksize=CHUNK_SIZE,
    )

    logger.info("Loaded [dbo].[%s]: %d rows.", table_name, total)


def run_load(transformed: Dict[str, pd.DataFrame]) -> None:
    """Create schema, truncate tables, and bulk-insert all transformed data."""
    logger.info("=== Load phase started ===")
    engine = get_engine()

    ensure_schema(engine)
    truncate_tables(engine)

    for table_name in LOAD_ORDER:
        if table_name in transformed:
            load_table(engine, table_name, transformed[table_name])
        else:
            logger.warning("No data found for table '%s'", table_name)

    logger.info("=== Load phase complete ===")


if __name__ == "__main__":
    from extract import run_extract
    from transform import run_transform

    raw         = run_extract()
    transformed = run_transform(raw)
    run_load(transformed)
