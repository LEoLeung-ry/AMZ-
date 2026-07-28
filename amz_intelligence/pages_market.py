from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from .config import FACTOR_LABELS, MARKETS
from .ui_common import factor_long, money, compact_number


def render_overview(scored: pd.DataFrame) -> None:
    st.markdown(
        '<div class="notice">跨站点金额不直接相加。系统保留原币，跨站比较主要使用各站点内部百分位和因子分。</div>',
        unsafe_allow_html=True,
    )
    rows: list[dict[str, object]] = []
    for code, config in MARKETS.items():
        market = scored.loc[scored["MarketCode"].eq(code)]
        if market.empty:
            continue
        physical = market.loc[market["EligiblePhysical"]]
        rows.append(
            {
                "站点": f"{config.flag} {config.name}",
                "总记录": len(market),
                "实体可评分": int(market["EligiblePhysical"].sum()),
                "市场销售额": money(physical["Revenue"].sum(), code),
                "ASIN总量": physical["ASINCount"].sum(),
                "机会分中位数": physical["OpportunityScore"].median(),
                "置信度中位数": market["DataQualityScore"].median(),
                "数据快照": config.snapshot_label,
            }
        )
    summary = pd.DataFrame(rows)
    st.dataframe(
        summary,
        hide_index=True,
        use_container_width=True,
        column_config={
            "总记录": st.column_config.NumberColumn(format="%d"),
            "实体可评分": st.column_config.NumberColumn(format="%d"),
            "ASIN总量": st.column_config.NumberColumn(format="%.0f"),
            "机会分中位数": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "置信度中位数": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
        },
    )

    physical = scored.loc[scored["EligiblePhysical"]]
    market_factor = physical.groupby(
        ["MarketCode", "MarketFlag", "Market"], as_index=False, observed=True
    )[list(FACTOR_LABELS)].median()
    if not market_factor.empty:
        long = factor_long(market_factor, ["MarketCode", "MarketFlag", "Market"])
        long["站点"] = long["MarketFlag"] + " " + long["Market"]
        fig = px.bar(
            long,
            x="FactorLabel",
            y="Score",
            color="站点",
            barmode="group",
            title="四站点因子结构对比（站内标准化中位数）",
            labels={"FactorLabel": "分析因子", "Score": "分数"},
        )
        fig.update_layout(height=470, yaxis_range=[0, 100], legend_orientation="h")
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

    st.markdown("### 每站当前 Top 5")
    top_rows: list[dict[str, object]] = []
    for code, config in MARKETS.items():
        top = scored.loc[scored["MarketCode"].eq(code) & scored["EligiblePhysical"]].nlargest(5, "OpportunityScore")
        for _, row in top.iterrows():
            top_rows.append(
                {
                    "站点": f"{config.flag} {config.name}",
                    "等级": row["OpportunityLevel"],
                    "类目": row["Category"],
                    "当地名称": row["CategoryLocal"],
                    "标准大类": row["RootStandard"],
                    "机会分": row["OpportunityScore"],
                    "市场销售额": money(row["Revenue"], code),
                    "单ASIN收入": money(row["RevenuePerASIN"], code),
                    "置信度": row["DataQualityScore"],
                    "链接": row["Link"],
                }
            )
    st.dataframe(
        pd.DataFrame(top_rows),
        hide_index=True,
        use_container_width=True,
        column_config={
            "机会分": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "置信度": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "链接": st.column_config.LinkColumn(display_text="打开 ↗"),
        },
    )


def render_opportunities(filtered: pd.DataFrame, market_code: str, strategy: str) -> None:
    if filtered.empty:
        st.info("没有符合当前筛选条件的类目。")
        return
    config = MARKETS[market_code]
    best = filtered.nlargest(1, "OpportunityScore").iloc[0]
    cols = st.columns(6)
    cols[0].metric("候选类目", f"{len(filtered):,}")
    cols[1].metric("销售额合计", money(filtered["Revenue"].sum(), market_code))
    cols[2].metric("单ASIN收入中位数", money(filtered["RevenuePerASIN"].median(), market_code))
    cols[3].metric("搜索/ASIN中位数", compact_number(filtered["SearchPerASIN"].median()))
    cols[4].metric("置信度中位数", f"{filtered['DataQualityScore'].median():.1f}")
    cols[5].metric("最高机会分", f"{best['OpportunityScore']:.1f}", delta=str(best["Category"])[:18], delta_color="off")
    st.markdown(
        '<div class="notice">机会分先在本站内做百分位，再混合全站比较与同大类内部比较，并由数据置信度折减。它是选品筛选器，不是利润承诺。</div>',
        unsafe_allow_html=True,
    )

    ranked = filtered.sort_values(["OpportunityScore", "DataQualityScore", "Revenue"], ascending=False).reset_index(drop=True)
    ranked.insert(0, "Rank", np.arange(1, len(ranked) + 1))
    columns = [
        "Rank", "OpportunityLevel", "Category", "CategoryLocal", "RootStandard", "OpportunityZone",
        "OpportunityScore", "MarketFactor", "DemandFactor", "AccessFactor", "MonetizationFactor",
        "EfficiencyFactor", "PainFactor", "DataQualityScore", "Revenue", "Sales", "ASP", "ASINCount",
        "RevenuePerASIN", "SearchPerASIN", "ClickYieldPct", "LowRatingShare", "TopKeyword", "DataFlags", "Link",
    ]
    st.dataframe(
        ranked[columns],
        hide_index=True,
        use_container_width=True,
        height=680,
        column_config={
            "Rank": st.column_config.NumberColumn("排名", format="%d"),
            "OpportunityLevel": st.column_config.TextColumn("等级"),
            "Category": st.column_config.TextColumn("中文类目", width="medium"),
            "CategoryLocal": st.column_config.TextColumn("当地名称", width="medium"),
            "RootStandard": st.column_config.TextColumn("标准大类"),
            "OpportunityZone": st.column_config.TextColumn("机会象限"),
            "OpportunityScore": st.column_config.ProgressColumn("机会分", min_value=0, max_value=100, format="%.1f"),
            "MarketFactor": st.column_config.ProgressColumn("市场", min_value=0, max_value=100, format="%.0f"),
            "DemandFactor": st.column_config.ProgressColumn("需求", min_value=0, max_value=100, format="%.0f"),
            "AccessFactor": st.column_config.ProgressColumn("可进入性", min_value=0, max_value=100, format="%.0f"),
            "MonetizationFactor": st.column_config.ProgressColumn("变现", min_value=0, max_value=100, format="%.0f"),
            "EfficiencyFactor": st.column_config.ProgressColumn("效率", min_value=0, max_value=100, format="%.0f"),
            "PainFactor": st.column_config.ProgressColumn("痛点", min_value=0, max_value=100, format="%.0f"),
            "DataQualityScore": st.column_config.ProgressColumn("置信度", min_value=0, max_value=100, format="%.0f"),
            "Revenue": st.column_config.NumberColumn("销售额", format=f"{config.currency_symbol}%.0f"),
            "Sales": st.column_config.NumberColumn("销量", format="%.0f"),
            "ASP": st.column_config.NumberColumn("平均价格", format=f"{config.currency_symbol}%.2f"),
            "ASINCount": st.column_config.NumberColumn("ASIN数", format="%.0f"),
            "RevenuePerASIN": st.column_config.NumberColumn("单ASIN收入", format=f"{config.currency_symbol}%.0f"),
            "SearchPerASIN": st.column_config.NumberColumn("搜索/ASIN", format="%.1f"),
            "ClickYieldPct": st.column_config.NumberColumn("点击产出效率", format="%.2f%%"),
            "LowRatingShare": st.column_config.NumberColumn("低评分结构", format="percent"),
            "DataFlags": st.column_config.TextColumn("数据提示", width="large"),
            "Link": st.column_config.LinkColumn("Amazon", display_text="打开 ↗"),
        },
    )
    export_columns = [c for c in columns if c != "Rank"]
    st.download_button(
        "下载当前候选 CSV",
        ranked[export_columns].to_csv(index=False).encode("utf-8-sig"),
        f"{market_code}_{strategy}_opportunities_{datetime.now():%Y%m%d_%H%M}.csv",
        "text/csv",
        use_container_width=True,
    )


def render_matrix(filtered: pd.DataFrame) -> None:
    if filtered.empty:
        st.info("没有可绘制的数据。")
        return
    options = {
        "ASIN数量（供给竞争）": "ASINCount", "市场销售额": "Revenue", "市场销量": "Sales",
        "搜索量": "SearchVolume", "单ASIN收入": "RevenuePerASIN", "单ASIN销量": "UnitsPerASIN",
        "搜索/ASIN": "SearchPerASIN", "平均价格": "ASP", "点击产出效率": "ClickYieldPct",
        "低评分结构": "LowRatingShare", "机会分": "OpportunityScore",
    }
    a, b, c, d = st.columns(4)
    x_label = a.selectbox("横轴", list(options), index=0)
    y_label = b.selectbox("纵轴", list(options), index=1)
    bubble_label = c.selectbox("气泡大小", list(options), index=4)
    color_label = d.selectbox("颜色", ["机会象限", "标准大类", "数据风险"])
    log_axes = st.toggle("正数轴使用对数刻度", True)
    x, y, size = options[x_label], options[y_label], options[bubble_label]
    color = {"机会象限": "OpportunityZone", "标准大类": "RootStandard", "数据风险": "DigitalRisk"}[color_label]
    plot = filtered.dropna(subset=[x, y, size]).copy()
    if log_axes:
        plot = plot.loc[plot[x].gt(0) & plot[y].gt(0)]
    if plot.empty:
        st.info("当前指标组合没有足够有效数据。")
        return
    plot["Bubble"] = plot[size].clip(lower=0).fillna(0) + 1e-9
    count = st.slider("显示类目标签数量", 0, min(40, len(plot)), min(12, len(plot)))
    indexes = plot.nlargest(count, "OpportunityScore").index if count else pd.Index([])
    plot["Label"] = np.where(plot.index.isin(indexes), plot["Category"], "")
    fig = px.scatter(
        plot, x=x, y=y, size="Bubble", color=color, text="Label", hover_name="Category",
        hover_data={"CategoryLocal": True, "OpportunityScore": ":.1f", "ASINCount": ":,.0f", "DataQualityScore": ":.0f", "Bubble": False, "Label": False},
        log_x=log_axes, log_y=log_axes, size_max=58,
        labels={x: x_label, y: y_label, color: color_label},
    )
    median_x, median_y = float(plot[x].median()), float(plot[y].median())
    if median_x > 0 or not log_axes:
        fig.add_vline(x=median_x, line_dash="dot", line_color="#64748b", annotation_text="横轴中位线")
    if median_y > 0 or not log_axes:
        fig.add_hline(y=median_y, line_dash="dot", line_color="#64748b", annotation_text="纵轴中位线")
    fig.update_traces(textposition="top center", textfont_size=10)
    fig.update_layout(height=760, legend_orientation="h")
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
