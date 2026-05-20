from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def _sql_path(name: str) -> Path:
    for base in (
        ROOT / "team_member_2_database_design" / "sql",
        ROOT / "team_member_5_sql_analytics" / "sql",
        ROOT / "final_integrated_project" / "sql",
    ):
        p = base / name
        if p.exists():
            return p
    raise FileNotFoundError(name)


def test_schema_has_core_tables():
    text = _sql_path("schema.sql").read_text(encoding="utf-8")
    for table in ("movies", "ratings", "movie_genres", "genres"):
        assert f"dbo.{table}" in text or f"CREATE TABLE dbo.{table}" in text


def test_queries_file_has_analytics():
    text = _sql_path("queries.sql").read_text(encoding="utf-8")
    assert "SELECT" in text
    assert text.count("GO") >= 10


def test_seed_verification():
    text = _sql_path("seed.sql").read_text(encoding="utf-8")
    assert "COUNT(*)" in text
