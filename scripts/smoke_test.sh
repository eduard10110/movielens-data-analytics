#!/usr/bin/env bash
# smoke_test.sh — Quick health check after docker compose up
set -euo pipefail

MSSQL_PASSWORD="${MSSQL_PASSWORD:-MovieLens@2024}"
SQLCMD="docker exec movielens_mssql /opt/mssql-tools18/bin/sqlcmd"

echo "==> MSSQL ping"
$SQLCMD -S localhost -U sa -P "$MSSQL_PASSWORD" -Q "SELECT 1" -b -No

echo "==> Database exists"
$SQLCMD -S localhost -U sa -P "$MSSQL_PASSWORD" -Q \
  "SELECT name FROM sys.databases WHERE name = 'MovieLensDB'" -b -No

echo "==> Table row counts (top 3)"
$SQLCMD -S localhost -U sa -P "$MSSQL_PASSWORD" -d MovieLensDB -Q \
  "SELECT TOP 3 'movies' AS t, COUNT(*) AS c FROM dbo.movies
   UNION ALL SELECT 'ratings', COUNT(*) FROM dbo.ratings
   UNION ALL SELECT 'tags', COUNT(*) FROM dbo.tags" -b -No

echo "==> Airflow webserver (optional)"
if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
  echo "Airflow: OK"
else
  echo "Airflow: not reachable (start stack or ignore for local ETL-only test)"
fi

echo "==> Smoke test finished OK"
