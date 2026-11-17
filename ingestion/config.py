"""Shared paths, settings and the TPC-H raw schema."""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
DUCKDB_PATH = WAREHOUSE_DIR / "tpch.duckdb"
DBT_DIR = PROJECT_ROOT / "tpch_dbt"

# The eight TPC-H tables, in dependency order (dimensions first).
TPCH_TABLES = ["region", "nation", "supplier", "customer", "part", "partsupp", "orders", "lineitem"]

# Raw DDL for Snowflake, per the TPC-H specification (section 1.4).
SNOWFLAKE_DDL = {
    "region": """
        r_regionkey integer not null, r_name varchar(25) not null, r_comment varchar(152)""",
    "nation": """
        n_nationkey integer not null, n_name varchar(25) not null,
        n_regionkey integer not null, n_comment varchar(152)""",
    "supplier": """
        s_suppkey integer not null, s_name varchar(25) not null, s_address varchar(40) not null,
        s_nationkey integer not null, s_phone varchar(15) not null,
        s_acctbal number(15,2) not null, s_comment varchar(101) not null""",
    "customer": """
        c_custkey integer not null, c_name varchar(25) not null, c_address varchar(40) not null,
        c_nationkey integer not null, c_phone varchar(15) not null, c_acctbal number(15,2) not null,
        c_mktsegment varchar(10) not null, c_comment varchar(117) not null""",
    "part": """
        p_partkey integer not null, p_name varchar(55) not null, p_mfgr varchar(25) not null,
        p_brand varchar(10) not null, p_type varchar(25) not null, p_size integer not null,
        p_container varchar(10) not null, p_retailprice number(15,2) not null,
        p_comment varchar(23) not null""",
    "partsupp": """
        ps_partkey integer not null, ps_suppkey integer not null, ps_availqty integer not null,
        ps_supplycost number(15,2) not null, ps_comment varchar(199) not null""",
    "orders": """
        o_orderkey bigint not null, o_custkey integer not null, o_orderstatus varchar(1) not null,
        o_totalprice number(15,2) not null, o_orderdate date not null,
        o_orderpriority varchar(15) not null, o_clerk varchar(15) not null,
        o_shippriority integer not null, o_comment varchar(79) not null""",
    "lineitem": """
        l_orderkey bigint not null, l_partkey integer not null, l_suppkey integer not null,
        l_linenumber integer not null, l_quantity number(15,2) not null,
        l_extendedprice number(15,2) not null, l_discount number(15,2) not null,
        l_tax number(15,2) not null, l_returnflag varchar(1) not null,
        l_linestatus varchar(1) not null, l_shipdate date not null, l_commitdate date not null,
        l_receiptdate date not null, l_shipinstruct varchar(25) not null,
        l_shipmode varchar(10) not null, l_comment varchar(44) not null""",
}


def sf_label(sf: float) -> str:
    """0.1 -> 'sf0_1', 1 -> 'sf1'."""
    text = f"{sf:g}".replace(".", "_")
    return f"sf{text}"


def raw_dir_for(sf: float) -> Path:
    return RAW_DIR / sf_label(sf)


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env loader (KEY=VALUE lines, # comments). Existing env vars win."""
    path = path or PROJECT_ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.split(" #", 1)[0].strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def require_env(*names: str) -> dict[str, str]:
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise SystemExit(
            f"Missing environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill them in."
        )
    return {n: os.environ[n] for n in names}
