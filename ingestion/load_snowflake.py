"""Load the Parquet landing zone into Snowflake.

Flow per table: PUT file -> internal stage, then COPY INTO a typed raw table
(MATCH_BY_COLUMN_NAME), then row-count reconciliation against the manifest.
"""
from __future__ import annotations

import json
import os

from .config import SNOWFLAKE_DDL, TPCH_TABLES, raw_dir_for, require_env


def connect():
    import snowflake.connector  # imported lazily so DuckDB-only users don't need it configured

    env = require_env("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE")
    kwargs = dict(
        account=env["SNOWFLAKE_ACCOUNT"],
        user=env["SNOWFLAKE_USER"],
        warehouse=env["SNOWFLAKE_WAREHOUSE"],
        role=os.environ.get("SNOWFLAKE_ROLE") or None,
        application="tpch-data-engineering",
    )
    key_path = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH")
    authenticator = os.environ.get("SNOWFLAKE_AUTHENTICATOR", "snowflake")
    if key_path:
        kwargs["private_key_file"] = key_path
        if os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"):
            kwargs["private_key_file_pwd"] = os.environ["SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"]
    elif authenticator.lower() != "snowflake":
        kwargs["authenticator"] = authenticator
    else:
        kwargs["password"] = require_env("SNOWFLAKE_PASSWORD")["SNOWFLAKE_PASSWORD"]
    return snowflake.connector.connect(**kwargs)


def load(sf: float) -> dict[str, int]:
    src = raw_dir_for(sf)
    manifest = json.loads((src / "_manifest.json").read_text())
    database = os.environ["SNOWFLAKE_DATABASE"]
    raw_schema = os.environ.get("SNOWFLAKE_RAW_SCHEMA", "RAW")

    con = connect()
    cur = con.cursor()
    try:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
        cur.execute(f"USE DATABASE {database}")
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {raw_schema}")
        cur.execute(f"USE SCHEMA {raw_schema}")
        cur.execute("CREATE FILE FORMAT IF NOT EXISTS tpch_parquet TYPE = PARQUET")
        cur.execute("CREATE STAGE IF NOT EXISTS tpch_landing FILE_FORMAT = tpch_parquet")

        loaded: dict[str, int] = {}
        for table in TPCH_TABLES:
            local = (src / f"{table}.parquet").as_posix()
            stage_path = f"@tpch_landing/{src.name}/{table}/"
            print(f"[load:snowflake] PUT {table}.parquet -> {stage_path}")
            cur.execute(f"PUT 'file://{local}' {stage_path} AUTO_COMPRESS = FALSE OVERWRITE = TRUE")
            cur.execute(f"CREATE OR REPLACE TABLE {table} ({SNOWFLAKE_DDL[table]})")
            cur.execute(f"""
                COPY INTO {table} FROM {stage_path}
                FILE_FORMAT = (FORMAT_NAME = tpch_parquet)
                MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
                ON_ERROR = ABORT_STATEMENT
            """)
            loaded[table] = cur.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            expected = manifest["row_counts"][table]
            if loaded[table] != expected:
                raise RuntimeError(f"{raw_schema}.{table}: loaded {loaded[table]}, expected {expected}")
            print(f"[load:snowflake] {raw_schema}.{table:<9} {loaded[table]:>12,} rows")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS _load_audit (
                loaded_at TIMESTAMP_NTZ DEFAULT current_timestamp(), scale_factor FLOAT,
                table_name VARCHAR, row_count NUMBER)
        """)
        cur.executemany(
            "INSERT INTO _load_audit (scale_factor, table_name, row_count) VALUES (%s, %s, %s)",
            [(sf, t, n) for t, n in loaded.items()],
        )
        return loaded
    finally:
        cur.close()
        con.close()
