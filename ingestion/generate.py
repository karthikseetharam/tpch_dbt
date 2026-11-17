"""Generate TPC-H data with DuckDB's dbgen and export one Parquet file per table.

This plays the role of the "source system extract": a landing zone of files
that the load step then ingests into a warehouse.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import duckdb

from .config import TPCH_TABLES, raw_dir_for


def generate(sf: float, force: bool = False) -> dict[str, int]:
    out_dir = raw_dir_for(sf)
    manifest_path = out_dir / "_manifest.json"
    if manifest_path.exists() and not force:
        manifest = json.loads(manifest_path.read_text())
        print(f"[generate] SF {sf:g} already in {out_dir} (use --force to regenerate)")
        return manifest["row_counts"]

    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    con = duckdb.connect()  # in-memory: dbgen output is only staged here
    con.execute("INSTALL tpch; LOAD tpch;")
    print(f"[generate] running dbgen(sf={sf:g}) ...")
    con.execute(f"CALL dbgen(sf = {sf})")

    row_counts: dict[str, int] = {}
    for table in TPCH_TABLES:
        target = (out_dir / f"{table}.parquet").as_posix()
        con.execute(f"COPY {table} TO '{target}' (FORMAT parquet, COMPRESSION zstd)")
        row_counts[table] = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        print(f"[generate]   {table:<9} {row_counts[table]:>12,} rows")
    con.close()

    manifest = {
        "scale_factor": sf,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duckdb_version": duckdb.__version__,
        "row_counts": row_counts,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"[generate] done in {time.perf_counter() - started:.1f}s -> {out_dir}")
    return row_counts
