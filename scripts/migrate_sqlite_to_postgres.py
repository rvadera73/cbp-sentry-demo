#!/usr/bin/env python3
"""One-time migration from SQLite seed data into PostgreSQL."""

import json
import os
import sqlite3
from pathlib import Path

import psycopg2
import psycopg2.extras
from psycopg2 import sql

DEFAULT_DATABASE_URL = "postgresql://sentry:sentry-secret@localhost:5433/sentry"
DEFAULT_SQLITE_PATH = Path(__file__).resolve().parent.parent / "data" / "cbp_sentry.db"
BOOLEAN_COLUMNS = {
    "element9_is_mismatch",
    "ad_cvd_applicable",
    "ofac_match",
    "isf_element_mismatch",
    "isf_late_filing",
}
JSONB_COLUMNS = {"audit_trail", "risk_breakdown", "ai_synthesis", "isf_data"}
TABLES = (
    ("shipments", "id"),
    ("corridors", "id"),
    ("corridor_duties", "id"),
)


def resolve_sqlite_path() -> Path:
    env_path = os.environ.get("SQLITE_PATH")
    if env_path:
        return Path(env_path)
    app_path = Path("/app/data/cbp_sentry.db")
    return app_path if app_path.exists() else DEFAULT_SQLITE_PATH


def get_pg_conn():
    return psycopg2.connect(
        os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
        options="-c search_path=cbp_sentry",
    )


def get_pg_columns(cursor, table_name: str) -> list[str]:
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'cbp_sentry' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )
    return [row[0] for row in cursor.fetchall()]


def get_sqlite_columns(cursor, table_name: str) -> list[str]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def transform_row(row: sqlite3.Row, columns: list[str]) -> tuple:
    values = []
    for column in columns:
        value = row[column]
        if column in BOOLEAN_COLUMNS and value is not None:
            value = bool(value)
        elif column in JSONB_COLUMNS and isinstance(value, str):
            value = psycopg2.extras.Json(json.loads(value)) if value.strip() else None
        values.append(value)
    return tuple(values)


def migrate_table(sqlite_conn, pg_conn, table_name: str, conflict_column: str) -> int:
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()

    sqlite_columns = get_sqlite_columns(sqlite_cursor, table_name)
    pg_columns = get_pg_columns(pg_cursor, table_name)
    common_columns = [column for column in sqlite_columns if column in pg_columns]
    if not common_columns:
        raise RuntimeError(f"No shared columns found for table {table_name}")

    sqlite_cursor.execute(f"SELECT {', '.join(common_columns)} FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    if not rows:
        print(f"{table_name}: 0 rows")
        return 0

    values = [transform_row(row, common_columns) for row in rows]
    update_columns = [column for column in common_columns if column != conflict_column]
    if update_columns:
        update_sql = ", ".join(f"{column} = EXCLUDED.{column}" for column in update_columns)
        conflict_sql = f"ON CONFLICT ({conflict_column}) DO UPDATE SET {update_sql}"
    else:
        conflict_sql = f"ON CONFLICT ({conflict_column}) DO NOTHING"

    insert_sql = sql.SQL("INSERT INTO {} ({}) VALUES %s {}")
    query = insert_sql.format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(map(sql.Identifier, common_columns)),
        sql.SQL(conflict_sql),
    )
    psycopg2.extras.execute_values(pg_cursor, query.as_string(pg_conn), values, page_size=500)
    pg_conn.commit()
    print(f"{table_name}: migrated {len(values)} rows")
    return len(values)


def reset_sequence(pg_conn, table_name: str, column_name: str = "id") -> None:
    cursor = pg_conn.cursor()
    cursor.execute(
        sql.SQL(
            "SELECT setval(pg_get_serial_sequence(%s, %s), COALESCE(MAX({column}), 1), TRUE) FROM {table}"
        ).format(table=sql.Identifier(table_name), column=sql.Identifier(column_name)),
        (f"cbp_sentry.{table_name}", column_name),
    )
    pg_conn.commit()


def main() -> None:
    sqlite_path = resolve_sqlite_path()
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = get_pg_conn()

    try:
        migrated = {}
        for table_name, conflict_column in TABLES:
            migrated[table_name] = migrate_table(sqlite_conn, pg_conn, table_name, conflict_column)

        reset_sequence(pg_conn, "corridor_duties")

        cursor = pg_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM shipments")
        shipment_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM corridors")
        corridor_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM corridor_duties")
        duty_count = cursor.fetchone()[0]
        print(
            f"Done. shipments={shipment_count}, corridors={corridor_count}, corridor_duties={duty_count}"
        )
    finally:
        pg_conn.close()
        sqlite_conn.close()


if __name__ == "__main__":
    main()
