from __future__ import annotations

from datetime import datetime
from typing import Mapping

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .config import FACTOR_LABELS, MARKETS
from .engine import compute_trend_metrics, explain_category
from .ui_common import (
    compact_number,
    concat_text,
    factor_long,
    match_confidence,
    money,
    scalar_text,
    text_match_mask,
    text_values,
)


def render_cross_market(scored: pd.DataFrame, default_query: str = "") -> None:
    st.markdown(
        '<div class="notice">跨站点使用站内标准化分数比较。名称匹配只产生候选，不会把相似名称强行认定为同一个Browse Node。</div>',
        unsafe_allow_html=True,
    )
    query = st.text_input(
        "输入产品或类目关键词", default_query, placeholder="例如 handheld fan、剃须刀、storage box", key="compare_query"
    )
    if not query.strip():
        st.info("输入关键词后，系统会同时搜索四站中文名、当地名、热门关键词和Node Path。")
        return
    matched = scored.loc[text_match_mask(scored, query) & scored["EligibleCore"]].copy()
    matched["匹配置信度"] = matched.apply(lambda row: match_confidence(row, query), axis=1)
    matched = matched.sort_values(["MarketCode", "OpportunityScore", "DataQualityScore"], ascending=[True, False, False])
    matched = matched.groupby("MarketCode", as_index=False, group_keys=False, observed=True).head(20)
    if matched.empty:
        st.warning("四站均未找到匹配类目，可尝试英文、当地语言或更短关键词。")
        return
    matched["站点"] = concat_text(matched["MarketFlag"], matched["Market"], sep=" ")
    matched["市场销售额"] = matched.apply(lambda row: money(row["Revenue"], row["MarketCode"]), axis=1)
    matched["平均价格显示"] = matched.apply(lambda row: money(row["ASP"], row["MarketCode"]), axis=1)
    matched["单ASIN收入显示"] = matched.apply(lambda row: money(row["RevenuePerASIN"], row["MarketCode"]), axis=1)
    columns = [
        "站点", "匹配置信度", "Category", "CategoryLocal", "RootStandard", "OpportunityScore",
        "MarketFactor", "DemandFactor", "AccessFactor", "市场销售额", "平均价格显示",
        "单ASIN收入显示", "ASINCount", "DataQualityScore", "Link",
    ]
    st.dataframe(
        matched[columns], hide_index=True, use_container_width=True, height=620,
        column_config={
            "OpportunityScore": st.column_config.ProgressColumn("机会分", min_value=0, max_value=100, format="%.1f"),
            "MarketFactor": st.column_config.ProgressColumn("市场", min_value=0, max_value=100, format="%.0f"),
            "DemandFactor": st.column_config.ProgressColumn("需求", min_value=0, max_value=100, format="%.0f"),
            "AccessFactor": st.column_config.ProgressColumn("可进入性", min_value=0, max_value=100, format="%.0f"),
            "ASINCount": st.column_config.NumberColumn("ASIN数", format="%.0f"),
            "DataQualityScore": st.column_config.ProgressColumn("置信度", min_value=0, max_value=100, format="%.0f"),
            "Link": st.column_config.LinkColumn("Amazon", display_text="打开 ↗"),
        },
    )
    best = matched.sort_values("OpportunityScore", ascending=False).groupby("MarketCode", as_index=False, observed=True).head(1)
    if not best.empty:
        long = factor_long(best, ["MarketCode", "MarketFlag", "Market", "Category"])
        market_label = concat_text(long["MarketFlag"], long["Market"], sep=" ")
        long["候选"] = concat_text(market_label, text_values(long["Category"]).str.slice(0, 18), sep="｜")
        fig = px.bar(long, x="FactorLabel", y="Score", color="候选", barmode="group", title="各站点最高匹配候选的因子对比")
        fig.update_layout(height=500, yaxis_range=[0, 100], legend_orientation="h")
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


def render_diagnosis(pool: pd.DataFrame, market_code: str) -> None:
    if pool.empty:
        st.info("没有可诊断类目。")
        return
    pool = pool.sort_values("OpportunityScore", ascending=False).copy()
    pool["SelectLabel"] = (
        pool["Category"].astype(str) + "｜" + pool["CategoryLocal"].astype(str).str.slice(0, 32) + "｜ID " + pool["CategoryID"].astype(str)
    )
    selected = st.selectbox("选择一个类目", pool["SelectLabel"].tolist())
    row = pool.loc[pool["SelectLabel"].eq(selected)].iloc[0]
    row_market_code = str(row["MarketCode"])
    st.markdown(f"## {row['Category']}")
    st.caption(f"{row['MarketFlag']} {row['Market']} · {row['CategoryLocal']} · {row['RootStandard']} · 类目ID {row['CategoryID']}")
    cols = st.columns(6)
    cols[0].metric("机会分", f"{row['OpportunityScore']:.1f}", delta=row["OpportunityLevel"], delta_color="off")
    cols[1].metric("销售额", money(row["Revenue"], row_market_code))
    cols[2].metric("平均价格", money(row["ASP"], row_market_code))
    cols[3].metric("ASIN数量", compact_number(row["ASINCount"]))
    cols[4].metric("单ASIN收入", money(row["RevenuePerASIN"], row_market_code))
    cols[5].metric("置信度", f"{row['DataQualityScore']:.0f}")

    left, right = st.columns(2)
    factors = list(FACTOR_LABELS)
    values = [float(row.get(factor, 0)) for factor in factors]
    with left:
        fig = go.Figure(go.Scatterpolar(
            r=values + [values[0]], theta=[FACTOR_LABELS[f] for f in factors] + [FACTOR_LABELS[factors[0]]], fill="toself"
        ))
        fig.update_layout(polar={"radialaxis": {"visible": True, "range": [0, 100]}}, showlegend=False, height=470)
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    with right:
        st.markdown("### 系统诊断")
        for note in explain_category(row):
            st.markdown(f"- {note}")
        if scalar_text(row["TopKeyword"]):
            suffix = f"｜头部关键词占搜索量约 {row['TopKeywordShare']:.2%}" if pd.notna(row["TopKeywordShare"]) else ""
            st.info(f"热门关键词：{row['TopKeyword']}{suffix}")
        if scalar_text(row["PriceBand"]):
            st.caption(f"源数据高转化价格区间：{row['PriceBand']}")
        if scalar_text(row["Link"]):
            st.link_button("打开 Amazon 类目页 ↗", row["Link"], use_container_width=True)

    metrics = pd.DataFrame({
        "指标": ["近12个月销量", "近12个月搜索量", "近12个月点击量", "近12个月浏览量", "点击产出效率", "点击率", "搜索/ASIN", "单ASIN销量", "低评分结构", "高评分结构", "数字商品风险", "数据异常"],
        "值": [
            compact_number(row["Sales"]), compact_number(row["SearchVolume"]), compact_number(row["Clicks"]),
            compact_number(row["Views"]), f"{row['ClickYieldPct']:.2f}%" if pd.notna(row["ClickYieldPct"]) else "—",
            f"{row['CTRPct']:.2f}%" if pd.notna(row["CTRPct"]) else "—", compact_number(row["SearchPerASIN"]),
            compact_number(row["UnitsPerASIN"]), f"{row['LowRatingShare']:.2%}" if pd.notna(row["LowRatingShare"]) else "—",
            f"{row['HighRatingShare']:.2%}" if pd.notna(row["HighRatingShare"]) else "—", row["DigitalRisk"], row["DataFlags"],
        ],
    })
    st.dataframe(metrics, hide_index=True, use_container_width=True)


def render_trends(scored: pd.DataFrame) -> None:
    trends = compute_trend_metrics(scored)
    if not trends.empty:
        st.success("检测到多个时间快照，已启用真实趋势计算。")
        st.dataframe(trends.sort_values("OpportunityMomentum", ascending=False), hide_index=True, use_container_width=True)
        return
    st.markdown(
        '<div class="warning-note"><b>目前还没有真实时间趋势。</b> 四站当前各只有一个近12个月汇总快照，不能诚实地计算月环比、增长加速度或趋势反转。</div>',
        unsafe_allow_html=True,
    )
    st.markdown("### 当前可用：结构性需求机会信号")
    st.caption("该信号衡量当前需求强度、供给可进入性与流量效率，不代表最近几个月正在上涨。")
    structural = scored.loc[scored["EligiblePhysical"]].sort_values(["DemandSupplySignal", "DataQualityScore"], ascending=False).copy()
    structural["站点"] = concat_text(structural["MarketFlag"], structural["Market"], sep=" ")
    structural["销售额显示"] = structural.apply(lambda row: money(row["Revenue"], row["MarketCode"]), axis=1)
    st.dataframe(
        structural[["站点", "Category", "CategoryLocal", "RootStandard", "DemandSupplySignal", "DemandFactor", "AccessFactor", "EfficiencyFactor", "销售额显示", "ASINCount", "DataQualityScore", "Link"]].head(300),
        hide_index=True, use_container_width=True, height=620,
        column_config={
            "DemandSupplySignal": st.column_config.ProgressColumn("结构性信号", min_value=0, max_value=100, format="%.1f"),
            "DemandFactor": st.column_config.ProgressColumn("需求", min_value=0, max_value=100, format="%.0f"),
            "AccessFactor": st.column_config.ProgressColumn("可进入性", min_value=0, max_value=100, format="%.0f"),
            "EfficiencyFactor": st.column_config.ProgressColumn("效率", min_value=0, max_value=100, format="%.0f"),
            "ASINCount": st.column_config.NumberColumn("ASIN数", format="%.0f"),
            "DataQualityScore": st.column_config.ProgressColumn("置信度", min_value=0, max_value=100, format="%.0f"),
            "Link": st.column_config.LinkColumn("Amazon", display_text="打开 ↗"),
        },
    )
    export = ["MarketCode", "Market", "SnapshotLabel", "SnapshotDate", "CategoryKey", "CategoryID", "CategoryCN", "CategoryLocal", "RootRaw", "RootStandard", "Revenue", "Sales", "SearchVolume", "Clicks", "Views", "ASINCount", "ASP", "RevenuePerASIN", "UnitsPerASIN", "DataQualityScore"]
    st.download_button(
        "下载四站标准化快照（用于未来趋势对比）",
        scored[export].to_csv(index=False).encode("utf-8-sig"),
        f"amazon_multimarket_snapshot_{datetime.now():%Y%m%d}.csv",
        "text/csv", use_container_width=True,
    )


def render_quality(
    scored: pd.DataFrame,
    diagnostics: Mapping[str, Mapping[str, object]],
    load_errors: Mapping[str, str],
    market_code: str,
    selected_weights: Mapping[str, float],
) -> None:
    if load_errors:
        st.markdown("### 数据源读取错误")
        for code, error in load_errors.items():
            st.error(f"{MARKETS[code].flag} {MARKETS[code].name}：{error}")
    rows = []
    for code, diag in diagnostics.items():
        config = MARKETS[code]
        rows.append({
            "站点": f"{config.flag} {config.name}", "源数据行": diag.get("source_rows", 0),
            "标准化行": diag.get("prepared_rows", 0), "去重行": diag.get("duplicates_removed", 0),
            "核心可评分": diag.get("eligible_core_rows", 0), "实体可评分": diag.get("eligible_physical_rows", 0),
            "名称同时缺失": diag.get("missing_both_names", 0), "负销售额": diag.get("negative_revenue_rows", 0),
            "零销量": diag.get("zero_sales_rows", 0), "ASIN非正": diag.get("zero_asin_rows", 0),
            "数字高风险": diag.get("digital_high_risk_rows", 0), "置信度中位数": diag.get("quality_median", np.nan),
            "识别表头行": diag.get("fetch_metadata", {}).get("header_row", "—"),
            "抓取时间": diag.get("fetch_metadata", {}).get("fetched_at", "—"),
        })
    st.dataframe(
        pd.DataFrame(rows), hide_index=True, use_container_width=True,
        column_config={"置信度中位数": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f")},
    )

    market = scored.loc[scored["MarketCode"].eq(market_code)].copy()
    counts = (
        market.assign(Flag=market["DataFlags"].str.split("；")).explode("Flag")
        .loc[lambda frame: frame["Flag"].ne("正常")].groupby("Flag", as_index=False).size().sort_values("size", ascending=False)
    )
    left, right = st.columns([0.8, 1.2])
    with left:
        st.markdown(f"### {MARKETS[market_code].name} 异常类型")
        st.dataframe(counts.rename(columns={"Flag": "异常类型", "size": "记录数"}), hide_index=True, use_container_width=True)
    with right:
        st.markdown("### 当前站点低置信度记录")
        low = market.nsmallest(200, "DataQualityScore")
        st.dataframe(
            low[["Category", "CategoryLocal", "CategoryID", "RootRaw", "DataQualityScore", "DataFlags", "Revenue", "Sales", "ASINCount", "Link"]],
            hide_index=True, use_container_width=True, height=520,
            column_config={
                "DataQualityScore": st.column_config.ProgressColumn("置信度", min_value=0, max_value=100, format="%.0f"),
                "Revenue": st.column_config.NumberColumn("销售额", format=f"{MARKETS[market_code].currency_symbol}%.0f"),
                "Link": st.column_config.LinkColumn("Amazon", display_text="打开 ↗"),
            },
        )
    with st.expander("字段识别详情"):
        for code, diag in diagnostics.items():
            st.markdown(f"#### {MARKETS[code].flag} {MARKETS[code].name}")
            st.json({k: v for k, v in diag.get("resolved_columns", {}).items() if v is not None})
    with st.expander("机会模型说明"):
        table = pd.DataFrame({"因子": [FACTOR_LABELS[k] for k in selected_weights], "当前权重": list(selected_weights.values())})
        st.dataframe(
            table, hide_index=True, use_container_width=True,
            column_config={"当前权重": st.column_config.ProgressColumn(min_value=0, max_value=max(selected_weights.values()), format="percent")},
        )
        st.markdown(
            """
            - 原始指标先转换为各站点内部百分位，降低货币差异和极端值影响。
            - 市场、需求、竞争、变现、流量效率、痛点分别成因子，避免同一概念重复计权。
            - 最终机会分由数据置信度折减；分母过小、名称缺失和数字商品风险都会明确显示。
            - 当前源是近12个月汇总快照，不能直接证明时间上的增长趋势。
            """
        )
