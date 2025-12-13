import argparse
import sys
from pathlib import Path

import psycopg


def execute_sql_file(conn, sql_file: Path) -> None:
    """Execute a SQL file against the provided database connection."""
    print(f"Executing {sql_file.name}...")
    sql_content = sql_file.read_text()

    with conn.cursor() as cur:
        cur.execute(sql_content)

    conn.commit()
    print(f"Successfully executed {sql_file.name}")


def initialize_users(connection_string: str) -> None:
    """Initialize database users by executing all SQL files in the sql directory."""
    sql_dir = Path(__file__).parent / "sql"

    sql_files = [
        sql_dir / "init_datadog_user.sql",
        sql_dir / "init_compass_bot_migrations.sql",
        sql_dir / "init_compass_bot_user.sql",
        sql_dir / "init_pganalyze_user.sql",
        sql_dir / "init_compass_bot_readonly_user.sql",
    ]

    for sql_file in sql_files:
        if not sql_file.exists():
            print(f"Error: SQL file not found: {sql_file}", file=sys.stderr)
            sys.exit(1)

    try:
        with psycopg.connect(connection_string) as conn:
            for sql_file in sql_files:
                execute_sql_file(conn, sql_file)

        print("\nAll users initialized successfully!")

    except psycopg.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize database users by executing SQL files")
    parser.add_argument(
        "connection_string",
        help="Full PostgreSQL connection string (e.g., postgresql://user:pass@host:port/db)",
    )

    args = parser.parse_args()
    initialize_users(args.connection_string)


if __name__ == "__main__":
    main()
