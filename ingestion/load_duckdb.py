"""Load the Parquet landing zone into the local DuckDB warehouse (schema `raw`)."""
from __future__ import annotations

import json

import duckdb

from .config import DUCKDB_PATH, TPCH_TABLES, raw_dir_for


def load(sf: float) -> dict[str, int]:
    src = raw_dir_for(sf)
    manifest = json.loads((src / "_manifest.json").read_text())
    DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DUCKDB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    loaded: dict[str, int] = {}
    for table in TPCH_TABLES:
        path = (src / f"{table}.parquet").as_posix()
        con.execute(f"CREATE OR REPLACE TABLE raw.{table} AS SELECT * FROM read_parquet('{path}')")
        loaded[table] = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
        expected = manifest["row_counts"][table]
        if loaded[table] != expected:
            raise RuntimeError(f"raw.{table}: loaded {loaded[table]} rows, expected {expected}")
        print(f"[load:duckdb] raw.{table:<9} {loaded[table]:>12,} rows")

    # Audit table so downstream layers (and you) can see what was loaded and when.
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw._load_audit (
            loaded_at TIMESTAMP DEFAULT current_timestamp, scale_factor DOUBLE,
            table_name VARCHAR, row_count BIGINT)
    """)
    con.executemany(
        "INSERT INTO raw._load_audit (scale_factor, table_name, row_count) VALUES (?, ?, ?)",
        [(sf, t, n) for t, n in loaded.items()],
    )
    con.close()
    return loaded
