from __future__ import annotations

import pandas as pd
import streamlit as st

from amz_intelligence.config import MARKETS, STRATEGY_PRESETS
from amz_intelligence.engine import apply_strategy_score, prepare_market_data
from amz_intelligence.pages_insight import (
    render_cross_market,
    render_diagnosis,
    render_quality,
    render_trends,
)
from amz_intelligence.pages_market import render_matrix, render_opportunities, render_overview


def synthetic_raw(code: str) -> pd.DataFrame:
    currency = {"JP": "¥", "US": "$", "DE": "€", "UK": "£"}[code]
    return pd.DataFrame(
        {
            "分类ID": ["3.0117754031E10", "1.6416191E7", "21700306031"],
            "中文名称": ["无线耳机", "收纳盒", "手持风扇"],
            "分类名称": ["Wireless Headphones", "Storage Boxes", "Handheld Fans"],
            "根类目": ["electronics", "kitchen", "home-garden"],
            "跳转链接": [
                f"https://www.{MARKETS[code].amazon_domain}/gp/bestsellers/electronics/30117754031",
                f"https://www.{MARKETS[code].amazon_domain}/gp/bestsellers/kitchen/16416191",
                f"https://www.{MARKETS[code].amazon_domain}/gp/bestsellers/home-garden/21700306031",
            ],
            "近12个月销量": ["100000", "20000", "45000"],
            "近12个月净销售额": [f"{currency}12500000", f"{currency}2000000", f"{currency}6750000"],
            "近12个月搜索量": ["4000000", "800000", "1600000"],
            "近12个月点击量": ["200000", "50000", "110000"],
            "近12个月浏览量": ["800000", "150000", "350000"],
            "搜索转化率": ["50", "40", "40.9"],
            "点击率": ["25", "33.33", "31.43"],
            "平均价格": ["125", "100", "150"],
            "最受欢迎关键词": ["wireless headphones", "storage box", "handheld fan"],
            "最受欢迎关键词值": ["500000", "30000", "180000"],
            "ASIN数量": ["1250", "80", "230"],
            "价格转化率最大值": ["100-150", "80-120", "120-180"],
            "4星及以上评分数量": ["800", "50", "130"],
            "3星评分数量": ["100", "20", "40"],
            "2星评分数量": ["30", "5", "15"],
            "1星评分数量": ["20", "5", "10"],
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
scored = apply_strategy_score(all_data, "稳健优先")
market_code = "JP"
filtered = scored.loc[scored["MarketCode"].eq(market_code) & scored["EligiblePhysical"]].copy()

st.title("V3 UI smoke test")
tabs = st.tabs(["overview", "opportunities", "matrix", "cross", "diagnosis", "trends", "quality"])
with tabs[0]:
    render_overview(scored)
with tabs[1]:
    render_opportunities(filtered, market_code, "稳健优先")
with tabs[2]:
    render_matrix(filtered)
with tabs[3]:
    render_cross_market(scored, "storage")
with tabs[4]:
    render_diagnosis(filtered, market_code)
with tabs[5]:
    render_trends(scored)
with tabs[6]:
    render_quality(scored, diagnostics, {}, market_code, STRATEGY_PRESETS["稳健优先"])
