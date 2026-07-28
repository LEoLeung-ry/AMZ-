from __future__ import annotations

import re
from typing import Iterable

import pandas as pd
import streamlit as st

from .config import FACTOR_LABELS, MARKETS


def apply_visual_system() -> None:
    st.markdown(
        """
        <style>
        :root { --ink:#0f172a; --muted:#64748b; --line:#dbe4ef; --panel:rgba(255,255,255,.95); }
        [data-testid="stAppViewContainer"] { background:radial-gradient(circle at 10% -8%,rgba(37,99,235,.12),transparent 32%),#f6f8fc; }
        [data-testid="stHeader"] { background:rgba(246,248,252,.86); }
        [data-testid="stSidebar"] { background:linear-gradient(180deg,#0f172a,#111827); border-right:1px solid rgba(255,255,255,.08); }
        [data-testid="stSidebar"] * { color:#e5e7eb; }
        [data-testid="stSidebar"] [data-baseweb="select"]>div,
        [data-testid="stSidebar"] [data-baseweb="input"]>div,
        [data-testid="stSidebar"] input { background-color:rgba(255,255,255,.08); }
        .block-container { max-width:1760px; padding-top:1.2rem; padding-bottom:3rem; }
        .hero { padding:1.45rem 1.65rem; border-radius:24px; border:1px solid rgba(37,99,235,.16); background:linear-gradient(130deg,#fff,#f7fbff 60%,#eaf3ff); box-shadow:0 18px 50px rgba(15,23,42,.07); margin-bottom:1rem; }
        .hero-kicker { color:#2563eb; font-size:.76rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; margin-bottom:.4rem; }
        .hero h1 { color:var(--ink); font-size:clamp(1.75rem,3vw,2.65rem); line-height:1.1; margin:0 0 .45rem; }
        .hero p { color:var(--muted); max-width:1100px; margin:0; }
        .meta-row { display:flex; flex-wrap:wrap; gap:.5rem; margin-top:1rem; }
        .pill { display:inline-flex; padding:.36rem .68rem; border-radius:999px; background:rgba(255,255,255,.88); border:1px solid #dbeafe; color:#334155; font-size:.78rem; font-weight:650; }
        [data-testid="stMetric"] { background:var(--panel); border:1px solid var(--line); border-radius:17px; padding:.82rem 1rem; box-shadow:0 7px 22px rgba(15,23,42,.04); }
        .notice { border-left:4px solid #2563eb; background:#eff6ff; color:#334155; padding:.72rem .9rem; border-radius:10px; margin:.35rem 0 1rem; }
        .warning-note { border:1px solid #fde68a; background:#fffbeb; color:#854d0e; padding:.75rem .9rem; border-radius:12px; margin:.4rem 0 1rem; }
        div[data-testid="stTabs"] button { font-weight:700; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def compact_number(value: float, market_code: str | None = None) -> str:
    if value is None or pd.isna(value):
        return "—"
    value = float(value)
    absolute = abs(value)
    if market_code == "JP":
        if absolute >= 100_000_000:
            return f"{value / 100_000_000:,.1f}亿"
        if absolute >= 10_000:
            return f"{value / 10_000:,.1f}万"
        return f"{value:,.0f}"
    if absolute >= 1_000_000_000:
        return f"{value / 1_000_000_000:,.2f}B"
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:,.1f}M"
    if absolute >= 1_000:
        return f"{value / 1_000:,.1f}K"
    return f"{value:,.0f}"


def money(value: float, market_code: str) -> str:
    config = MARKETS[market_code]
    return "—" if value is None or pd.isna(value) else f"{config.currency_symbol}{compact_number(value, market_code)}"


def text_match_mask(df: pd.DataFrame, query: str) -> pd.Series:
    if not query.strip():
        return pd.Series(True, index=df.index, dtype=bool)
    pattern = re.escape(query.strip().casefold())
    columns = ["Category", "CategoryCN", "CategoryLocal", "TopKeyword", "NodePath", "CategoryID"]
    mask = pd.Series(False, index=df.index, dtype=bool)
    for column in columns:
        if column in df:
            mask |= df[column].fillna("").astype(str).str.casefold().str.contains(pattern, regex=True, na=False)
    return mask


def match_confidence(row: pd.Series, query: str) -> str:
    q = query.strip().casefold()
    if not q:
        return "—"
    cn = str(row.get("CategoryCN", "")).casefold()
    local = str(row.get("CategoryLocal", "")).casefold()
    keyword = str(row.get("TopKeyword", "")).casefold()
    if q == cn or q == local or cn.startswith(q) or local.startswith(q):
        return "高"
    if q in cn or q in local:
        return "中高"
    if q in keyword:
        return "中"
    return "低"


def factor_long(df: pd.DataFrame, id_columns: Iterable[str]) -> pd.DataFrame:
    factors = list(FACTOR_LABELS)
    long = df[list(id_columns) + factors].melt(
        id_vars=list(id_columns), value_vars=factors, var_name="Factor", value_name="Score"
    )
    long["FactorLabel"] = long["Factor"].map(FACTOR_LABELS)
    return long
