"""Load seed/tickets.csv and seed/customers.csv into app.db.

Usage: uv run python load_seed.py
Running it again rebuilds the same tables, so a second run gives the same database.
"""

import csv
import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEED_DIR = ROOT / "seed"
DB_PATH = ROOT / "app.db"

# One entry per table, with its columns in CSV header order. mcp/triage_server.py reads these names.
TABLES: dict[str, dict[str, str]] = {
    "tickets": {"ticket_id": "TEXT PRIMARY KEY", "customer_id": "TEXT NOT NULL", "created_at": "TEXT", "text": "TEXT"},
    # open_tickets is an INTEGER: TRIAGE_POLICY.md's Enterprise rule compares it to 3.
    "customers": {"customer_id": "TEXT PRIMARY KEY", "name": "TEXT", "plan": "TEXT", "open_tickets": "INTEGER"},
}


def _read_rows(csv_path: Path, schema: dict[str, str]) -> list[tuple]:
    columns = list(schema)
    # utf-8-sig also accepts a file saved with a byte-order mark, as Excel does.
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != columns:
            raise ValueError(f"{csv_path.name} has columns {reader.fieldnames}, expected {columns}")
        rows = []
        for row in reader:
            where = f"{csv_path.name} line {reader.line_num}"
            if None in row or None in row.values():
                raise ValueError(f"{where}: expected {len(columns)} fields")
            values = []
            for column in columns:
                if schema[column] == "INTEGER":
                    try:
                        values.append(int(row[column]))
                    except ValueError:
                        raise ValueError(f"{where}: {column} must be a whole number, not {row[column]!r}") from None
                else:
                    values.append(row[column])
            rows.append(tuple(values))
        return rows


def load(db_path: Path = DB_PATH, seed_dir: Path = SEED_DIR) -> dict[str, int]:
    """Rebuild every table from its CSV in one transaction and return the row count per table."""
    # Read and check every CSV before touching the database, so a bad file leaves app.db as it was.
    data = {table: _read_rows(seed_dir / f"{table}.csv", schema) for table, schema in TABLES.items()}
    with closing(sqlite3.connect(db_path, isolation_level=None)) as conn:
        conn.execute("BEGIN")
        try:
            for table, schema in TABLES.items():
                conn.execute(f"DROP TABLE IF EXISTS {table}")
                conn.execute(f"CREATE TABLE {table} ({', '.join(f'{name} {kind}' for name, kind in schema.items())})")
                conn.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(schema))})", data[table])
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    return {table: len(rows) for table, rows in data.items()}


if __name__ == "__main__":
    for table, count in load().items():
        print(f"{table}: {count} rows")
    print(f"Wrote {DB_PATH.name}")
