"""Streamlit dashboard over the TPC-H marts.

    streamlit run dashboard/app.py                 # local DuckDB warehouse
    streamlit run dashboard/app.py -- --snowflake  # Snowflake (credentials from .env)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ingestion.config import DUCKDB_PATH, load_dotenv  # noqa: E402

load_dotenv()
USE_SNOWFLAKE = "--snowflake" in sys.argv

st.set_page_config(page_title="TPC-H Sales Analytics", layout="wide")


@st.cache_data(ttl=600)
def query(sql: str) -> pd.DataFrame:
    if USE_SNOWFLAKE:
        from ingestion.load_snowflake import connect

        con = connect()
        try:
            cur = con.cursor()
            cur.execute(f"USE DATABASE {os.environ['SNOWFLAKE_DATABASE']}")
            df = cur.execute(sql).fetch_pandas_all()
        finally:
            con.close()
        df.columns = [c.lower() for c in df.columns]
        # Snowflake returns NUMBER columns as the smallest numpy int that fits (e.g. int8);
        # widen them so aggregations in pandas cannot overflow.
        for col in df.select_dtypes("integer").columns:
            df[col] = df[col].astype("int64")
        return df
    import duckdb

    with duckdb.connect(str(DUCKDB_PATH), read_only=True) as con:
        return con.execute(sql).df()


st.title("TPC-H Sales Analytics")
st.caption(f"Source: {'Snowflake' if USE_SNOWFLAKE else f'DuckDB ({DUCKDB_PATH.name})'} · "
           "marts built by dbt from the TPC-H benchmark dataset")

monthly = query("select * from analytics.agg_revenue_monthly")
monthly["month_start"] = pd.to_datetime(monthly["month_start"])

regions = sorted(monthly["region_name"].unique())
segments = sorted(monthly["market_segment"].unique())
with st.sidebar:
    st.header("Filters")
    picked_regions = st.multiselect("Customer region", regions, default=regions)
    picked_segments = st.multiselect("Market segment", segments, default=segments)
view = monthly[monthly["region_name"].isin(picked_regions) & monthly["market_segment"].isin(picked_segments)]

if view.empty:
    st.warning("No data for the selected filters.")
    st.stop()

def money(value: float) -> str:
    for size, unit in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= size:
            return f"${value / size:,.2f}{unit}"
    return f"${value:,.0f}"


k1, k2, k3, k4 = st.columns(4)
k1.metric("Net revenue", money(float(view["net_revenue"].sum())))
k2.metric("Gross margin", f"{view['gross_margin'].sum() / view['net_revenue'].sum():.1%}")
# Each order has one customer and one order month, so per-group distinct counts add up.
k3.metric("Orders", f"{int(view['order_count'].sum()):,}")
late = (view["late_delivery_rate"] * view["units"]).sum() / view["units"].sum()
k4.metric("Late deliveries", f"{late:.1%}", help="Share of units received after the commit date")

st.subheader("Net revenue by month and region")
st.caption("TPC-H orders end on 1998-08-02, so the last month is partial.")
trend = view.pivot_table(index="month_start", columns="region_name", values="net_revenue", aggfunc="sum")
st.line_chart(trend)

left, right = st.columns(2)
with left:
    st.subheader("Revenue by market segment")
    st.bar_chart(view.groupby("market_segment")["net_revenue"].sum().sort_values(ascending=False))
with right:
    st.subheader("Revenue by year")
    st.bar_chart(view.groupby("year_number")["net_revenue"].sum())

st.divider()
st.header("TPC-H benchmark questions, answered from the star schema")
tabs = st.tabs(["Q1 Pricing summary", "Q3 Shipping priority", "Q5 Local supplier volume",
                "Q6 Revenue change", "Q12 Shipping modes"])
models = ["tpch_q01_pricing_summary", "tpch_q03_shipping_priority", "tpch_q05_local_supplier_volume",
          "tpch_q06_forecast_revenue_change", "tpch_q12_shipping_modes"]
for tab, model in zip(tabs, models):
    with tab:
        st.dataframe(query(f"select * from analytics.{model}"), width="stretch", hide_index=True)
