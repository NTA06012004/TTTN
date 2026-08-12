"""Print a small, read-only health report for the configured MySQL database."""
from pathlib import Path
import sys

from sqlalchemy import create_engine, text

# Allow the documented direct invocation: ``python scripts/verify_mysql.py``.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings


def scalar(connection, sql: str):
    return connection.execute(text(sql)).scalar()


def main() -> None:
    engine = create_engine(get_settings().database_url)
    with engine.connect() as connection:
        print(f"user={scalar(connection, 'SELECT CURRENT_USER()')}")
        database_name = scalar(connection, "SELECT DATABASE()")
        print(f"database={database_name}")
        table_count = connection.execute(
            text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=:schema"),
            {"schema": database_name},
        ).scalar()
        print(f"tables={table_count}")
        print(f"migration={scalar(connection, 'SELECT version_num FROM alembic_version')}")
        for table in ("tournaments", "teams", "players", "matches", "match_events", "news_articles", "etl_rejects"):
            print(f"{table}={scalar(connection, f'SELECT COUNT(*) FROM {table}')}")


if __name__ == "__main__":
    main()
