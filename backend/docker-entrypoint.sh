#!/bin/sh
set -e

echo "Waiting for PostgreSQL at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
python - <<'PYEOF'
import os
import time
import psycopg2

host = os.getenv("POSTGRES_HOST", "db")
port = os.getenv("POSTGRES_PORT", "5432")
user = os.getenv("POSTGRES_USER", "honeypot_admin")
password = os.getenv("POSTGRES_PASSWORD", "changeme")
dbname = os.getenv("POSTGRES_DB", "honeypot_platform")

for attempt in range(30):
    try:
        conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
        conn.close()
        print("PostgreSQL is ready.")
        break
    except psycopg2.OperationalError:
        print(f"DB not ready yet (attempt {attempt + 1}/30), retrying in 2s...")
        time.sleep(2)
else:
    raise SystemExit("Could not connect to PostgreSQL after 30 attempts.")
PYEOF

echo "Running Alembic migrations..."
alembic upgrade head

echo "Seeding default admin user (if needed)..."
python -m app.bootstrap

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
