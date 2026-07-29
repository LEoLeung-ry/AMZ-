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
    cny_money,
    combine_text_columns,
    compact_number,
    factor_long,
    has_text,
    match_confidence,
    money,
    safe_text,
    text_match_mask,
)


def render_cross_market(scored: pd.DataFrame, default_query: str = "") -> None:
    st.markdown(
        '<div class="notice">跨站点同时显示本位币、人民币和站内标准化分数。名称匹配只产生候选，不会把相似名称强行认定为同一个 Browse Node。</div>',
        unsafe_allow_html=True,
    )
    query = st.text_input(
        "输入产品或类目关键词",
        default_query,
        placeholder="例如 handheld fan、剃须刀、storage box",
        key="compare_query",
    )
    if not query.strip():
        st.info("输入关键词后，系统会同时搜索四站中文名、当地名、热门关键词、Node Path 和监管类型。")
        return
    matched = scored.loc[text_match_mask(scored, query) & scored["EligibleCore"].fillna(False)].copy()
    matched["匹配置信度"] = matched.apply(lambda row: match_confidence(row, query), axis=1)
    matched = matched.sort_values(
        ["MarketCode", "FinalPriorityScore", "OpportunityScore", "DataQualityScore"],
        ascending=[True, False, False, False],
    )
    matched = matched.groupby("MarketCode", as_index=False, group_keys=False, observed=True).head(25)
    if matched.empty:
        st.warning("四站均未找到匹配类目，可尝试英文、当地语言或更短关键词。")
        return
    matched["站点"] = combine_text_columns(matched, ["MarketFlag", "Market"])
    matched["本位币销售额"] = matched.apply(lambda row: money(row["Revenue"], safe_text(row["MarketCode"])), axis=1)
    matched["人民币销售额"] = matched["CNYRevenue"].map(cny_money)
    matched["本位币均价"] = matched.apply(lambda row: money(row["ASP"], safe_text(row["MarketCode"])), axis=1)
    matched["人民币均价"] = matched["CNYASP"].map(cny_money)
    matched["人民币单ASIN"] = matched["CNYRevenuePerASIN"].map(cny_money)
    columns = [
        "站点",
        "匹配置信度",
        "BusinessDecision",
        "EntryLabel",
        "Category",
        "CategoryLocal",
        "RootStandard",
        "RegulatoryFamily",
        "FinalPriorityScore",
        "OpportunityScore",
        "CompanyFitScore",
        "CrossBorderFriendliness",
        "MarketFactor",
        "DemandFactor",
        "AccessFactor",
        "本位币销售额",
        "人民币销售额",
        "本位币均价",
        "人民币均价",
        "人民币单ASIN",
        "ASINCount",
        "BarrierReasons",
        "DataQualityScore",
        "Link",
    ]
    st.dataframe(
        matched[columns],
        hide_index=True,
        use_container_width=True,
        height=650,
        column_config={
            "BusinessDecision": st.column_config.TextColumn("经营决策"),
            "EntryLabel": st.column_config.TextColumn("经营准入"),
            "Category": st.column_config.TextColumn("中文类目", width="medium"),
            "CategoryLocal": st.column_config.TextColumn("当地名称", width="medium"),
            "RootStandard": st.column_config.TextColumn("标准大类"),
            "RegulatoryFamily": st.column_config.TextColumn("监管/经营类型"),
            "FinalPriorityScore": st.column_config.ProgressColumn("最终优先级", min_value=0, max_value=100, format="%.1f"),
            "OpportunityScore": st.column_config.ProgressColumn("市场机会分", min_value=0, max_value=100, format="%.1f"),
            "CompanyFitScore": st.column_config.ProgressColumn("公司适配", min_value=0, max_value=100, format="%.0f"),
            "CrossBorderFriendliness": st.column_config.ProgressColumn("跨境友好度", min_value=0, max_value=100, format="%.0f"),
            "MarketFactor": st.column_config.ProgressColumn("市场", min_value=0, max_value=100, format="%.0f"),
            "DemandFactor": st.column_config.ProgressColumn("需求", min_value=0, max_value=100, format="%.0f"),
            "AccessFactor": st.column_config.ProgressColumn("竞争可进入性", min_value=0, max_value=100, format="%.0f"),
            "ASINCount": st.column_config.NumberColumn("ASIN数", format="%.0f"),
            "BarrierReasons": st.column_config.TextColumn("主要障碍/条件", width="large"),
            "DataQualityScore": st.column_config.ProgressColumn("数据置信度", min_value=0, max_value=100, format="%.0f"),
            "Link": st.column_config.LinkColumn("Amazon", display_text="打开 ↗"),
        },
    )
    best = matched.sort_values("FinalPriorityScore", ascending=False).groupby(
        "MarketCode", as_index=False, observed=True
    ).head(1)
    if not best.empty:
        long = factor_long(best, ["MarketCode", "MarketFlag", "Market", "Category"])
        long["候选"] = (
            combine_text_columns(long, ["MarketFlag", "Market"])
            .str.cat(long["Category"].astype("string").fillna("").str.slice(0, 18), sep="｜")
        )
        fig = px.bar(
            long,
            x="FactorLabel",
            y="Score",
            color="候选",
            barmode="group",
            title="各站点最高可经营候选的市场因子对比",
        )
        fig.update_layout(height=500, yaxis_range=[0, 100], legend_orientation="h")
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


def render_diagnosis(pool: pd.DataFrame, market_code: str) -> None:
    if pool.empty:
        st.info("没有可诊断类目。")
        return
    pool = pool.sort_values(["FinalPriorityScore", "OpportunityScore"], ascending=False).copy()
    pool["SelectLabel"] = (
        pool["Category"].astype("string").fillna("")
        .str.cat(pool["CategoryLocal"].astype("string").fillna("").str.slice(0, 32), sep="｜")
        .str.cat(pool["CategoryID"].astype("string").fillna(""), sep="｜ID ")
    )
    selected = st.selectbox("选择一个类目", pool["SelectLabel"].tolist())
    row = pool.loc[pool["SelectLabel"].eq(selected)].iloc[0]
    row_market_code = safe_text(row["MarketCode"])
    st.markdown(f"## {safe_text(row['Category'])}")
    st.caption(
        f"{safe_text(row['MarketFlag'])} {safe_text(row['Market'])} · {safe_text(row['CategoryLocal'])} · "
        f"{safe_text(row['RootStandard'])} · 类目ID {safe_text(row['CategoryID'])}"
    )
    cols = st.columns(7)
    cols[0].metric("最终优先级", f"{row['FinalPriorityScore']:.1f}", delta=safe_text(row["BusinessDecision"]), delta_color="off")
    cols[1].metric("市场机会分", f"{row['OpportunityScore']:.1f}", delta=safe_text(row["OpportunityLevel"]), delta_color="off")
    cols[2].metric("经营准入", safe_text(row["EntryClass"]), delta=safe_text(row["EntryLabel"]), delta_color="off")
    cols[3].metric("公司适配", f"{row['CompanyFitScore']:.0f}")
    cols[4].metric("本位币销售额", money(row["Revenue"], row_market_code))
    cols[5].metric("人民币销售额", cny_money(row["CNYRevenue"]))
    cols[6].metric("数据置信度", f"{row['DataQualityScore']:.0f}")

    if safe_text(row["EntryClass"]) == "D":
        st.markdown(
            f'<div class="danger-note"><b>默认排除：</b>{safe_text(row["BarrierReasons"])}<br><b>若仍研究，需要：</b>{safe_text(row["RequiredResources"])}</div>',
            unsafe_allow_html=True,
        )
    elif safe_text(row["EntryClass"]) == "C":
        st.markdown(
            f'<div class="warning-note"><b>高门槛研究：</b>{safe_text(row["BarrierReasons"])}<br><b>所需资源：</b>{safe_text(row["RequiredResources"])}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="success-note"><b>可经营候选：</b>{safe_text(row["BarrierReasons"])}<br><b>推进条件：</b>{safe_text(row["RequiredResources"])}</div>',
            unsafe_allow_html=True,
        )

    left, right = st.columns(2)
    factors = list(FACTOR_LABELS)
    values = [
        float(pd.to_numeric(pd.Series([row.get(factor, 0)]), errors="coerce").fillna(0).iloc[0])
        for factor in factors
    ]
    with left:
        fig = go.Figure(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=[FACTOR_LABELS[f] for f in factors] + [FACTOR_LABELS[factors[0]]],
                fill="toself",
            )
        )
        fig.update_layout(
            polar={"radialaxis": {"visible": True, "range": [0, 100]}},
            showlegend=False,
            height=470,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    with right:
        st.markdown("### 市场与经营诊断")
        for note in explain_category(row):
            st.markdown(f"- {note}")
        st.markdown(f"- 监管/经营类型：**{safe_text(row['RegulatoryFamily'])}**")
        st.markdown(f"- 跨境友好度：**{row['CrossBorderFriendliness']:.0f}/100**")
        st.markdown(f"- 公司适配度：**{row['CompanyFitScore']:.0f}/100**")
        st.markdown(f"- 准入判断置信度：**{safe_text(row['BarrierRuleConfidence'])}**")
        if has_text(row.get("TopKeyword")):
            suffix = (
                f"｜头部关键词占搜索量约 {row['TopKeywordShare']:.2%}"
                if pd.notna(row.get("TopKeywordShare"))
                else ""
            )
            st.info(f"热门关键词：{safe_text(row['TopKeyword'])}{suffix}")
        if has_text(row.get("PriceBand")):
            st.caption(f"源数据高转化价格区间：{safe_text(row['PriceBand'])}")
        if has_text(row.get("Link")):
            st.link_button("打开 Amazon 类目页 ↗", safe_text(row["Link"]), use_container_width=True)

    metrics = pd.DataFrame(
        {
            "指标": [
                "近12个月销量",
                "近12个月搜索量",
                "近12个月点击量",
                "近12个月浏览量",
                "点击产出效率",
                "点击率",
                "搜索/ASIN",
                "单ASIN销量",
                "本位币单ASIN收入",
                "人民币单ASIN收入",
                "低评分结构",
                "高评分结构",
                "数字商品风险",
                "数据异常",
            ],
            "值": [
                compact_number(row["Sales"]),
                compact_number(row["SearchVolume"]),
                compact_number(row["Clicks"]),
                compact_number(row["Views"]),
                f"{row['ClickYieldPct']:.2f}%" if pd.notna(row["ClickYieldPct"]) else "—",
                f"{row['CTRPct']:.2f}%" if pd.notna(row["CTRPct"]) else "—",
                compact_number(row["SearchPerASIN"]),
                compact_number(row["UnitsPerASIN"]),
                money(row["RevenuePerASIN"], row_market_code),
                cny_money(row["CNYRevenuePerASIN"]),
                f"{row['LowRatingShare']:.2%}" if pd.notna(row["LowRatingShare"]) else "—",
                f"{row['HighRatingShare']:.2%}" if pd.notna(row["HighRatingShare"]) else "—",
                safe_text(row["DigitalRisk"]),
                safe_text(row["DataFlags"]),
            ],
        }
    )
    st.dataframe(metrics, hide_index=True, use_container_width=True)


def render_trends(scored: pd.DataFrame) -> None:
    trends = compute_trend_metrics(scored)
    if not trends.empty:
        st.success("检测到多个时间快照，已启用真实趋势计算。趋势使用本位币，避免汇率变化伪造成市场增长。")
        st.dataframe(
            trends.sort_values("OpportunityMomentum", ascending=False),
            hide_index=True,
            use_container_width=True,
        )
        return
    st.markdown(
        '<div class="warning-note"><b>目前还没有真实时间趋势。</b> 四站当前各只有一个近12个月汇总快照，不能诚实地计算月环比、增长加速度或趋势反转。</div>',
        unsafe_allow_html=True,
    )
    st.markdown("### 当前可用：结构性需求机会信号")
    st.caption("该信号衡量当前需求强度、供给竞争与流量效率；只展示A/B经营准入类目，不代表最近几个月正在上涨。")
    structural = scored.loc[scored["DefaultBusinessEligible"].fillna(False)].sort_values(
        ["DemandSupplySignal", "FinalPriorityScore", "DataQualityScore"], ascending=False
    ).copy()
    structural["站点"] = combine_text_columns(structural, ["MarketFlag", "Market"])
    structural["本位币销售额"] = structural.apply(
        lambda row: money(row["Revenue"], safe_text(row["MarketCode"])), axis=1
    )
    structural["人民币销售额"] = structural["CNYRevenue"].map(cny_money)
    st.dataframe(
        structural[
            [
                "站点",
                "BusinessDecision",
                "EntryLabel",
                "Category",
                "CategoryLocal",
                "RootStandard",
                "DemandSupplySignal",
                "FinalPriorityScore",
                "DemandFactor",
                "AccessFactor",
                "EfficiencyFactor",
                "本位币销售额",
                "人民币销售额",
                "ASINCount",
                "DataQualityScore",
                "Link",
            ]
        ].head(300),
        hide_index=True,
        use_container_width=True,
        height=620,
        column_config={
            "BusinessDecision": st.column_config.TextColumn("经营决策"),
            "EntryLabel": st.column_config.TextColumn("经营准入"),
            "DemandSupplySignal": st.column_config.ProgressColumn("结构性信号", min_value=0, max_value=100, format="%.1f"),
            "FinalPriorityScore": st.column_config.ProgressColumn("最终优先级", min_value=0, max_value=100, format="%.1f"),
            "DemandFactor": st.column_config.ProgressColumn("需求", min_value=0, max_value=100, format="%.0f"),
            "AccessFactor": st.column_config.ProgressColumn("竞争可进入性", min_value=0, max_value=100, format="%.0f"),
            "EfficiencyFactor": st.column_config.ProgressColumn("效率", min_value=0, max_value=100, format="%.0f"),
            "ASINCount": st.column_config.NumberColumn("ASIN数", format="%.0f"),
            "DataQualityScore": st.column_config.ProgressColumn("置信度", min_value=0, max_value=100, format="%.0f"),
            "Link": st.column_config.LinkColumn("Amazon", display_text="打开 ↗"),
        },
    )
    export = [
        "MarketCode",
        "Market",
        "SnapshotLabel",
        "SnapshotDate",
        "CategoryKey",
        "CategoryID",
        "CategoryCN",
        "CategoryLocal",
        "RootRaw",
        "RootStandard",
        "Revenue",
        "CNYRevenue",
        "Sales",
        "SearchVolume",
        "Clicks",
        "Views",
        "ASINCount",
        "ASP",
        "CNYASP",
        "RevenuePerASIN",
        "CNYRevenuePerASIN",
        "EntryClass",
        "CompanyFitScore",
        "FinalPriorityScore",
        "DataQualityScore",
    ]
    st.download_button(
        "下载四站标准化快照（用于未来趋势对比）",
        scored[export].to_csv(index=False).encode("utf-8-sig"),
        f"amazon_multimarket_snapshot_{datetime.now():%Y%m%d}.csv",
        "text/csv",
        use_container_width=True,
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
        market_scored = scored.loc[scored["MarketCode"].eq(code)]
        rows.append(
            {
                "站点": f"{config.flag} {config.name}",
                "源数据行": diag.get("source_rows", 0),
                "标准化行": diag.get("prepared_rows", 0),
                "去重行": diag.get("duplicates_removed", 0),
                "实体可评分": diag.get("eligible_physical_rows", 0),
                "基础A": int(market_scored["BaseEntryClass"].eq("A").sum()),
                "基础B": int(market_scored["BaseEntryClass"].eq("B").sum()),
                "基础C": int(market_scored["BaseEntryClass"].eq("C").sum()),
                "基础D": int(market_scored["BaseEntryClass"].eq("D").sum()),
                "名称同时缺失": diag.get("missing_both_names", 0),
                "负销售额": diag.get("negative_revenue_rows", 0),
                "零销量": diag.get("zero_sales_rows", 0),
                "ASIN非正": diag.get("zero_asin_rows", 0),
                "数字高风险": diag.get("digital_high_risk_rows", 0),
                "置信度中位数": diag.get("quality_median", np.nan),
                "识别表头行": diag.get("fetch_metadata", {}).get("header_row", "—"),
                "抓取时间": diag.get("fetch_metadata", {}).get("fetched_at", "—"),
            }
        )
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
        column_config={
            "置信度中位数": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f")
        },
    )

    market = scored.loc[scored["MarketCode"].eq(market_code)].copy()
    gate_counts = market.groupby(["EntryClass", "EntryLabel"], as_index=False, observed=True).size()
    family_counts = (
        market.groupby(["RegulatoryFamily", "EntryClass"], as_index=False, observed=True)
        .size()
        .sort_values("size", ascending=False)
    )
    left, right = st.columns(2)
    with left:
        st.markdown(f"### {MARKETS[market_code].name} 经营准入分布")
        st.dataframe(
            gate_counts.rename(columns={"EntryClass": "等级", "EntryLabel": "说明", "size": "记录数"}),
            hide_index=True,
            use_container_width=True,
        )
    with right:
        st.markdown("### 监管/经营类型 Top 20")
        st.dataframe(
            family_counts.head(20).rename(
                columns={"RegulatoryFamily": "类型", "EntryClass": "准入", "size": "记录数"}
            ),
            hide_index=True,
            use_container_width=True,
        )

    counts = (
        market.assign(Flag=market["DataFlags"].astype("string").fillna("正常").str.split("；"))
        .explode("Flag")
        .loc[lambda frame: frame["Flag"].ne("正常")]
        .groupby("Flag", as_index=False)
        .size()
        .sort_values("size", ascending=False)
    )
    left, right = st.columns([0.8, 1.2])
    with left:
        st.markdown("### 数据异常类型")
        st.dataframe(
            counts.rename(columns={"Flag": "异常类型", "size": "记录数"}),
            hide_index=True,
            use_container_width=True,
        )
    with right:
        st.markdown("### 当前站点低置信度记录")
        low = market.nsmallest(200, "DataQualityScore")
        st.dataframe(
            low[
                [
                    "Category",
                    "CategoryLocal",
                    "EntryLabel",
                    "RegulatoryFamily",
                    "DataQualityScore",
                    "DataFlags",
                    "CategoryID",
                ]
            ],
            hide_index=True,
            use_container_width=True,
            height=420,
            column_config={
                "DataQualityScore": st.column_config.ProgressColumn(
                    "置信度", min_value=0, max_value=100, format="%.0f"
                ),
                "DataFlags": st.column_config.TextColumn("数据提示", width="large"),
            },
        )

    st.markdown("### 当前机会模型权重")
    weight_rows = [
        {"因子": FACTOR_LABELS.get(factor, factor), "权重": float(weight)}
        for factor, weight in selected_weights.items()
    ]
    st.dataframe(
        pd.DataFrame(weight_rows),
        hide_index=True,
        use_container_width=True,
        column_config={"权重": st.column_config.NumberColumn(format="percent")},
    )
    st.caption("经营准入不是普通机会权重：它在市场机会分之后作为门槛系数参与最终优先级。")
