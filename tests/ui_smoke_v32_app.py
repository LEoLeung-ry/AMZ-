from __future__ import annotations

import pandas as pd
import streamlit as st

from amz_intelligence import MARKETS, STRATEGY_PRESETS, enrich_entry_rules
from amz_intelligence.engine import apply_strategy_score, prepare_market_data
from amz_intelligence.model_v32 import (
    NEUTRAL_PROFILE,
    add_strategy_robustness,
    apply_decision_model_v32,
)
from amz_intelligence.pages_insight import render_quality, render_trends
from amz_intelligence.pages_market import render_matrix
from amz_intelligence.pages_v32 import (
    render_cross_market_v32,
    render_diagnosis_v32,
    render_entry_research_v32,
    render_opportunities_v32,
    render_overview_v32,
    render_robustness_v32,
)


def synthetic_raw(market_code: str) -> pd.DataFrame:
    symbol = {"JP": "¥", "US": "$", "DE": "€", "UK": "£"}[market_code]
    return pd.DataFrame(
        {
            "分类ID": [f"100{index + 1}" for index in range(8)],
            "中文名称": ["日伞", "充电宝", "垃圾袋", "收纳箱", "大豆蛋白粉", "啤酒", "塔扇", "电动剃须刀"],
            "分类名称": [
                "Parasol",
                "Power Bank",
                "Trash Bags",
                "Storage Boxes",
                "Soy Protein Powder",
                "Beer",
                "Tower Fans",
                "Electric Shaver",
            ],
            "根类目": ["fashion", "electronics", "home", "home", "food-beverage", "food-beverage", "home", "beauty"],
            "Node Path": [
                "root > fashion > parasol",
                "root > electronics > power bank",
                "root > home > trash bags",
                "root > home > storage boxes",
                "root > food > soy protein",
                "root > food > beer",
                "root > home > tower fans",
                "root > beauty > electric shaver",
            ],
            "近12个月销量": [80000, 120000, 130000, 90000, 90000, 100000, 140000, 110000],
            "近12个月净销售额": [1800000000, 3500000000, 3200000000, 2100000000, 4000000000, 5000000000, 3800000000, 2900000000],
            "近12个月搜索量": [1300000, 2500000, 2800000, 1700000, 1800000, 2000000, 3000000, 2200000],
            "近12个月点击量": [300000, 600000, 650000, 350000, 450000, 500000, 700000, 520000],
            "近12个月浏览量": [700000, 1200000, 1300000, 800000, 900000, 1000000, 1400000, 1050000],
            "平均价格": [22500, 29167, 24615, 23333, 44444, 50000, 27143, 26364],
            "ASIN数量": [100, 300, 220, 180, 180, 200, 260, 210],
            "最受欢迎关键词": ["parasol", "power bank", "trash bags", "storage boxes", "soy protein", "beer", "tower fan", "shaver"],
            "最受欢迎关键词值": [70000, 120000, 140000, 80000, 90000, 100000, 150000, 110000],
            "价格转化率最大值": [f"{symbol}20 - {symbol}40"] * 8,
            "4星及以上评分数量": [70, 220, 180, 140, 140, 150, 200, 170],
            "3星评分数量": [10, 30, 25, 20, 20, 20, 28, 22],
            "2星评分数量": [8, 20, 15, 10, 10, 10, 18, 12],
            "1星评分数量": [5, 10, 8, 5, 5, 5, 9, 6],
        }
    )


frames: list[pd.DataFrame] = []
diagnostics: dict[str, dict[str, object]] = {}
for market_code, config in MARKETS.items():
    prepared, diag = prepare_market_data(
        synthetic_raw(market_code),
        config,
        fetch_metadata={"header_row": 1, "fetched_at": "2026-07-29 00:00:00"},
    )
    frames.append(prepared)
    diagnostics[market_code] = diag

all_data = enrich_entry_rules(pd.concat(frames, ignore_index=True))
opportunity = apply_strategy_score(all_data, "稳健优先")
decision = apply_decision_model_v32(opportunity, profile=NEUTRAL_PROFILE)
scored = add_strategy_robustness(all_data, decision)
market_code = "JP"
filtered = scored.loc[
    scored["MarketCode"].eq(market_code)
    & scored["DefaultBusinessEligible"].fillna(False)
].copy()

st.title("V3.2 UI smoke")
tabs = st.tabs(
    ["overview", "opportunities", "robustness", "matrix", "compare", "diagnosis", "entry", "trend", "quality"]
)
with tabs[0]:
    render_overview_v32(scored)
with tabs[1]:
    render_opportunities_v32(filtered, market_code, "稳健优先", rank_column="ConsensusPriorityScore")
with tabs[2]:
    render_robustness_v32(scored, market_code)
with tabs[3]:
    render_matrix(filtered)
with tabs[4]:
    render_cross_market_v32(scored, "power bank")
with tabs[5]:
    render_diagnosis_v32(scored.loc[scored["MarketCode"].eq(market_code)], market_code)
with tabs[6]:
    render_entry_research_v32(scored, market_code)
with tabs[7]:
    render_trends(scored)
with tabs[8]:
    render_quality(scored, diagnostics, {}, market_code, STRATEGY_PRESETS["稳健优先"])
