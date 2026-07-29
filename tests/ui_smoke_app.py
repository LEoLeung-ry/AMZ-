from __future__ import annotations

import pandas as pd
import streamlit as st

from amz_intelligence import MARKETS, STRATEGY_PRESETS, apply_business_model
from amz_intelligence.engine import apply_strategy_score, prepare_market_data
from amz_intelligence.pages_insight import render_cross_market, render_diagnosis, render_quality, render_trends
from amz_intelligence.pages_market import render_entry_research, render_matrix, render_opportunities, render_overview


def synthetic_raw(market_code: str) -> pd.DataFrame:
    symbol = {"JP": "¥", "US": "$", "DE": "€", "UK": "£"}[market_code]
    return pd.DataFrame(
        {
            "分类ID": [f"{market_code}1001", f"{market_code}1002", f"{market_code}1003", f"{market_code}1004"],
            "中文名称": ["日伞", "充电宝", "大豆蛋白粉", "啤酒"],
            "分类名称": ["Parasol", "Power Bank", "Soy Protein Powder", "Beer"],
            "根类目": ["fashion", "electronics", "food-beverage", "food-beverage"],
            "近12个月销量": [80000, 120000, 90000, 100000],
            "近12个月净销售额": [1800000000, 3500000000, 4000000000, 5000000000],
            "近12个月搜索量": [1300000, 2500000, 1800000, 2000000],
            "近12个月点击量": [300000, 600000, 450000, 500000],
            "近12个月浏览量": [700000, 1200000, 900000, 1000000],
            "平均价格": [22500, 29167, 44444, 50000],
            "ASIN数量": [100, 300, 180, 200],
            "最受欢迎关键词": ["parasol", "power bank", "soy protein", "beer"],
            "最受欢迎关键词值": [70000, 120000, 90000, 100000],
            "价格转化率最大值": [f"{symbol}20 - {symbol}40"] * 4,
            "4星及以上评分数量": [70, 220, 140, 150],
            "3星评分数量": [10, 30, 20, 20],
            "2星评分数量": [8, 20, 10, 10],
            "1星评分数量": [5, 10, 5, 5],
        }
    )


frames: list[pd.DataFrame] = []
diagnostics: dict[str, dict[str, object]] = {}
for market_code, config in MARKETS.items():
    prepared, diag = prepare_market_data(
        synthetic_raw(market_code),
        config,
        fetch_metadata={"header_row": 1, "fetched_at": "2026-07-29T00:00:00Z"},
    )
    frames.append(prepared)
    diagnostics[market_code] = diag

all_data = pd.concat(frames, ignore_index=True)
opportunity = apply_strategy_score(all_data, "稳健优先")
scored = apply_business_model(opportunity, profile="当前公司画像")
market_code = "JP"
filtered = scored.loc[
    scored["MarketCode"].eq(market_code)
    & scored["DefaultBusinessEligible"].fillna(False)
].copy()

st.title("UI smoke")
tabs = st.tabs(["overview", "opportunities", "matrix", "compare", "diagnosis", "entry", "trend", "quality"])
with tabs[0]:
    render_overview(scored)
with tabs[1]:
    render_opportunities(filtered, market_code, "稳健优先")
with tabs[2]:
    render_matrix(filtered)
with tabs[3]:
    render_cross_market(scored, "power bank")
with tabs[4]:
    render_diagnosis(scored.loc[scored["MarketCode"].eq(market_code)], market_code)
with tabs[5]:
    render_entry_research(scored, market_code)
with tabs[6]:
    render_trends(scored)
with tabs[7]:
    render_quality(scored, diagnostics, {}, market_code, STRATEGY_PRESETS["稳健优先"])
