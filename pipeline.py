"""TPC-H data engineering pipeline: generate -> load -> transform (dbt) -> verify -> bench.

Examples:
    python pipeline.py run --target duckdb --sf 0.1        # everything, locally
    python pipeline.py run --target snowflake --sf 0.1     # land Parquet, load to Snowflake, dbt build
    python pipeline.py run --target snowflake --source sample --sf 1
                                                           # use SNOWFLAKE_SAMPLE_DATA.TPCH_SF1, no load
    python pipeline.py transform --target duckdb --select marts
    python pipeline.py bench --sf 0.1                      # time the 22 official queries in DuckDB
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from decimal import Decimal
from pathlib import Path

from ingestion.config import DBT_DIR, DUCKDB_PATH, DATA_DIR, load_dotenv

SAMPLE_SCALE_FACTORS = {1: "TPCH_SF1", 10: "TPCH_SF10", 100: "TPCH_SF100", 1000: "TPCH_SF1000"}
VERIFIED_QUERIES = {
    1: "tpch_q01_pricing_summary",
    3: "tpch_q03_shipping_priority",
    5: "tpch_q05_local_supplier_volume",
    6: "tpch_q06_forecast_revenue_change",
    12: "tpch_q12_shipping_modes",
}


def step(name: str):
    print(f"\n=== {name} " + "=" * max(0, 60 - len(name)))
    return time.perf_counter()


# --------------------------------------------------------------------------- steps
def do_generate(args) -> None:
    from ingestion.generate import generate

    generate(args.sf, force=args.force)


def do_load(args) -> None:
    if args.target == "duckdb":
        from ingestion.load_duckdb import load
    else:
        from ingestion.load_snowflake import load
    load(args.sf)


def dbt_vars(args) -> dict:
    if args.target == "snowflake" and args.source == "sample":
        sf = int(args.sf) if float(args.sf).is_integer() else None
        if sf not in SAMPLE_SCALE_FACTORS:
            raise SystemExit(f"--source sample needs --sf in {sorted(SAMPLE_SCALE_FACTORS)}")
        return {"raw_database": "SNOWFLAKE_SAMPLE_DATA", "raw_schema": SAMPLE_SCALE_FACTORS[sf]}
    if args.target == "snowflake":
        return {"raw_schema": os.environ.get("SNOWFLAKE_RAW_SCHEMA", "RAW")}
    return {"raw_schema": "raw"}


def dbt_executable() -> str:
    """The dbt CLI installed next to this interpreter (the venv's), else whatever is on PATH."""
    scripts = Path(sys.executable).parent
    for name in ("dbt.exe", "dbt"):
        if (scripts / name).exists():
            return str(scripts / name)
    found = shutil.which("dbt")
    if not found:
        raise SystemExit("dbt not found: pip install -r requirements.txt")
    return found


def run_dbt(args, *cli: str) -> None:
    # dbt runs in its own process: dbt-duckdb keeps the database file open for the
    # life of the process, which would block verify/bench from opening it afterwards.
    os.environ["DBT_TARGET"] = args.target
    os.environ.setdefault("DUCKDB_PATH", str(DUCKDB_PATH))
    command = [
        dbt_executable(),
        *cli,
        "--project-dir", str(DBT_DIR),
        "--profiles-dir", str(DBT_DIR),
        "--target", args.target,
        "--vars", json.dumps(dbt_vars(args)),
    ]
    print("[dbt]", " ".join(command[1:]), flush=True)
    if subprocess.run(command).returncode != 0:
        raise SystemExit(f"dbt {cli[0]} failed")


def do_transform(args) -> None:
    cli = ["build"]
    if args.full_refresh:
        cli.append("--full-refresh")
    if args.select:
        cli += ["--select", args.select]
    run_dbt(args, *cli)


def _close(a, b) -> bool:
    if isinstance(a, (int, float, Decimal)) and isinstance(b, (int, float, Decimal)):
        return math.isclose(float(a), float(b), rel_tol=1e-6, abs_tol=0.01)
    return str(a).strip() == str(b).strip()


def _reference_answers(args) -> dict[int, list[tuple]]:
    """Official TPC-H query results, computed by DuckDB over the raw data.

    duckdb target: the loaded raw schema. snowflake target: the same Parquet files that were
    loaded into Snowflake, so both warehouses are checked against one independent reference.
    """
    import duckdb

    from ingestion.config import TPCH_TABLES, raw_dir_for

    if args.target == "duckdb":
        con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        con.execute("SET search_path = 'raw'")
    else:
        src = raw_dir_for(args.sf)
        if not (src / "_manifest.json").exists():
            raise SystemExit(f"[verify] no Parquet files for SF {args.sf:g} in {src}; run generate first")
        con = duckdb.connect()
        for table in TPCH_TABLES:
            con.execute(f"CREATE VIEW {table} AS SELECT * FROM read_parquet('{(src / f'{table}.parquet').as_posix()}')")
    con.execute("LOAD tpch")
    answers = {q: con.execute(f"PRAGMA tpch({q})").fetchall() for q in VERIFIED_QUERIES}
    con.close()
    return answers


def _model_answers(args) -> dict[int, list[tuple]]:
    """The same questions as answered by the dbt analytics models in the target warehouse."""
    if args.target == "duckdb":
        import duckdb

        con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        answers = {q: con.execute(f"SELECT * FROM analytics.{m}").fetchall() for q, m in VERIFIED_QUERIES.items()}
        con.close()
        return answers
    from ingestion.load_snowflake import connect

    con = connect()
    try:
        cur = con.cursor()
        cur.execute(f"USE DATABASE {os.environ['SNOWFLAKE_DATABASE']}")
        return {q: cur.execute(f"SELECT * FROM analytics.{m}").fetchall() for q, m in VERIFIED_QUERIES.items()}
    finally:
        con.close()


def do_verify(args) -> None:
    """Reconcile the star-schema answers with the official TPC-H reference queries."""
    if args.target == "snowflake" and args.source == "sample":
        print("[verify] skipped: no local copy of SNOWFLAKE_SAMPLE_DATA to compute reference answers from.")
        return
    reference = _reference_answers(args)
    models = _model_answers(args)
    failures = []
    for qnum, model in VERIFIED_QUERIES.items():
        expected, actual = reference[qnum], models[qnum]
        # Compare as sets of rows: a table read back has no guaranteed order.
        ok = len(expected) == len(actual) and all(
            len(e) == len(a) and all(_close(x, y) for x, y in zip(e, a))
            for e, a in zip(sorted(expected), sorted(actual))
        )
        print(f"[verify] Q{qnum:<2} {model:<34} rows={len(actual):<3} {'OK' if ok else 'MISMATCH'}")
        if not ok:
            failures.append(qnum)
            print("         expected:", expected[:3], "\n         actual:  ", actual[:3])
    if failures:
        raise SystemExit(f"verify failed for queries {failures}")


def do_bench(args) -> None:
    """Time the 22 official TPC-H queries against the raw tables in DuckDB."""
    import duckdb

    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    con.execute("LOAD tpch")
    con.execute("SET search_path = 'raw'")
    results = []
    for q in range(1, 23):
        timings = []
        for _ in range(args.runs):
            t0 = time.perf_counter()
            rows = con.execute(f"PRAGMA tpch({q})").fetchall()
            timings.append(time.perf_counter() - t0)
        best = min(timings)
        results.append({"query": q, "best_s": round(best, 4), "rows": len(rows)})
        print(f"[bench] Q{q:<2} best of {args.runs}: {best * 1000:8.1f} ms  ({len(rows)} rows)")
    con.close()
    total = sum(r["best_s"] for r in results)
    print(f"[bench] total {total:.2f}s  geomean {math.exp(sum(math.log(r['best_s']) for r in results) / 22) * 1000:.1f} ms")
    out = DATA_DIR / "bench" / f"duckdb_sf{args.sf:g}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"scale_factor": args.sf, "runs": args.runs, "results": results}, indent=2))
    print(f"[bench] wrote {out}")


def do_run(args) -> None:
    started = time.perf_counter()
    use_sample = args.target == "snowflake" and args.source == "sample"
    if not use_sample:
        t = step("generate"); do_generate(args); print(f"({time.perf_counter() - t:.1f}s)")
        t = step(f"load -> {args.target}"); do_load(args); print(f"({time.perf_counter() - t:.1f}s)")
    t = step("transform (dbt build)"); do_transform(args); print(f"({time.perf_counter() - t:.1f}s)")
    t = step("verify"); do_verify(args); print(f"({time.perf_counter() - t:.1f}s)")
    print(f"\nPipeline finished in {time.perf_counter() - started:.1f}s")


# --------------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> None:
    load_dotenv()
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--target", choices=["duckdb", "snowflake"], default="duckdb")
    common.add_argument("--sf", type=float, default=0.1, help="TPC-H scale factor (default 0.1)")
    common.add_argument("--source", choices=["generated", "sample"], default="generated",
                        help="snowflake only: 'sample' reads SNOWFLAKE_SAMPLE_DATA instead of loading")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("generate", parents=[common], help="dbgen -> Parquet landing zone")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=do_generate)

    sub.add_parser("load", parents=[common], help="Parquet -> warehouse raw schema").set_defaults(func=do_load)

    p = sub.add_parser("transform", parents=[common], help="dbt build (models + tests)")
    p.add_argument("--select")
    p.add_argument("--full-refresh", action="store_true")
    p.set_defaults(func=do_transform)

    sub.add_parser("verify", parents=[common], help="reconcile marts with reference queries").set_defaults(func=do_verify)

    p = sub.add_parser("bench", parents=[common], help="time the 22 TPC-H queries (DuckDB)")
    p.add_argument("--runs", type=int, default=3)
    p.set_defaults(func=do_bench)

    p = sub.add_parser("run", parents=[common], help="generate -> load -> transform -> verify")
    p.add_argument("--force", action="store_true")
    p.add_argument("--full-refresh", action="store_true")
    p.set_defaults(func=do_run, select=None)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
