set -e

SA_PASSWORD="${MSSQL_SA_PASSWORD:-MovieLens@2024}"
SQLCMD="/opt/mssql-tools18/bin/sqlcmd"

echo "[mssql-init] Waiting for SQL Server to be ready..."
for i in $(seq 1 30); do
    $SQLCMD -S localhost -U sa -P "$SA_PASSWORD" -Q "SELECT 1" -b -No 2>/dev/null && break
    echo "[mssql-init] Attempt $i/30 – not ready yet, sleeping 5s..."
    sleep 5
done

echo "[mssql-init] SQL Server is ready. Creating database and schema..."

$SQLCMD -S localhost -U sa -P "$SA_PASSWORD" -i /sql/schema.sql -b -No

echo "[mssql-init] Initialization complete."
