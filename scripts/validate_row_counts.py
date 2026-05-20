import os
import sys

try:
    import pymssql
except ImportError:
    print("Install pymssql: pip install pymssql")
    sys.exit(1)

MIN_ROWS = {
    "movies": 80_000,
    "genres": 15,
    "movie_genres": 150_000,
    "ratings": 1_000_000,
    "tags": 1_000_000,
    "links": 80_000,
    "genome_tags": 1_000,
    "genome_scores": 1_000_000,
}


def main() -> None:
    host = os.getenv("MSSQL_HOST", "localhost")
    user = os.getenv("MSSQL_USER", "sa")
    password = os.getenv("MSSQL_PASSWORD", "MovieLens@2024")
    database = os.getenv("MSSQL_DB", "MovieLensDB")

    conn = pymssql.connect(server=host, user=user, password=password, database=database)
    cur = conn.cursor()

    failed = False
    for table, minimum in MIN_ROWS.items():
        cur.execute(f"SELECT COUNT(*) FROM dbo.{table}")
        count = cur.fetchone()[0]
        status = "OK" if count >= minimum else "FAIL"
        if status == "FAIL":
            failed = True
        print(f"  [{status}] {table}: {count:,} (min {minimum:,})")

    conn.close()
    if failed:
        print("\nValidation FAILED — check ETL load or lower MIN_ROWS for sample runs.")
        sys.exit(1)
    print("\nValidation PASSED")


if __name__ == "__main__":
    main()
