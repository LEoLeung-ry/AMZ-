from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from .config import FACTOR_LABELS, MARKETS
from .ui_common import cny_money, combine_text_columns, compact_number, factor_long, money


def render_overview(scored: pd.DataFrame) -> None:
    st.markdown(
        '<div class="notice"><b>两套金额同时保留：</b>本位币用于理解当地市场，人民币用于跨站横向比较；跨站最终判断仍需结合本站百分位、经营准入和公司适配。</div>',
        unsafe_allow_html=True,
    )
    rows: list[dict[str, object]] = []
    for code, config in MARKETS.items():
        market = scored.loc[scored["MarketCode"].eq(code)]
        if market.empty:
            continue
        physical = market.loc[market["EligiblePhysical"].fillna(False)]
        business = market.loc[market["DefaultBusinessEligible"].fillna(False)]
        rows.append(
            {
                "站点": f"{config.flag} {config.name}",
                "总记录": len(market),
                "实体类目": int(market["EligiblePhysical"].sum()),
                "默认可经营": int(market["DefaultBusinessEligible"].sum()),
                "C/D研究类目": int(market["EntryClass"].isin(["C", "D"]).sum()),
                "本位币市场销售额": money(physical["Revenue"].sum(), code),
                "折合人民币": cny_money(physical["CNYRevenue"].sum()),
                "最终优先级中位数": business["FinalPriorityScore"].median(),
                "数据置信度中位数": market["DataQualityScore"].median(),
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
            "实体类目": st.column_config.NumberColumn(format="%d"),
            "默认可经营": st.column_config.NumberColumn(format="%d"),
            "C/D研究类目": st.column_config.NumberColumn(format="%d"),
            "最终优先级中位数": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "数据置信度中位数": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
        },
    )

    physical = scored.loc[scored["EligiblePhysical"].fillna(False)]
    market_factor = physical.groupby(
        ["MarketCode", "MarketFlag", "Market"], as_index=False, observed=True
    )[list(FACTOR_LABELS)].median()
    if not market_factor.empty:
        long = factor_long(market_factor, ["MarketCode", "MarketFlag", "Market"])
        long["站点"] = combine_text_columns(long, ["MarketFlag", "Market"])
        fig = px.bar(
            long,
            x="FactorLabel",
            y="Score",
            color="站点",
            barmode="group",
            title="四站点市场结构对比（各站点内部标准化中位数）",
            labels={"FactorLabel": "分析因子", "Score": "分数"},
        )
        fig.update_layout(height=470, yaxis_range=[0, 100], legend_orientation="h")
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

    st.markdown("### 每站当前 Top 5｜可经营机会")
    st.caption("先通过A/B经营准入，再按最终优先级排序。蛋白粉、酒类、药品等C/D类目不会进入此表。")
    top_rows: list[dict[str, object]] = []
    for code, config in MARKETS.items():
        top = scored.loc[
            scored["MarketCode"].eq(code) & scored["DefaultBusinessEligible"].fillna(False)
        ].nlargest(5, "FinalPriorityScore")
        for _, row in top.iterrows():
            top_rows.append(
                {
                    "站点": f"{config.flag} {config.name}",
                    "决策": row["BusinessDecision"],
                    "准入": row["EntryLabel"],
                    "类目": row["Category"],
                    "当地名称": row["CategoryLocal"],
                    "标准大类": row["RootStandard"],
                    "最终优先级": row["FinalPriorityScore"],
                    "市场机会分": row["OpportunityScore"],
                    "公司适配": row["CompanyFitScore"],
                    "本位币销售额": money(row["Revenue"], code),
                    "人民币销售额": cny_money(row["CNYRevenue"]),
                    "单ASIN人民币": cny_money(row["CNYRevenuePerASIN"]),
                    "主要条件": row["BarrierReasons"],
                    "置信度": row["DataQualityScore"],
                    "链接": row["Link"],
                }
            )
    top_frame = pd.DataFrame(top_rows)
    if top_frame.empty:
        st.info("当前经营画像下没有A/B级候选。")
    else:
        st.dataframe(
            top_frame,
            hide_index=True,
            use_container_width=True,
            column_config={
                "最终优先级": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
                "市场机会分": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
                "公司适配": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
                "置信度": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
                "主要条件": st.column_config.TextColumn(width="large"),
                "链接": st.column_config.LinkColumn(display_text="打开 ↗"),
            },
        )


def render_opportunities(filtered: pd.DataFrame, market_code: str, strategy: str) -> None:
    if filtered.empty:
        st.info("没有符合当前筛选条件的可经营类目。")
        return
    config = MARKETS[market_code]
    best = filtered.nlargest(1, "FinalPriorityScore").iloc[0]
    cols = st.columns(6)
    cols[0].metric("可经营候选", f"{len(filtered):,}")
    cols[1].metric("本位币销售额合计", money(filtered["Revenue"].sum(), market_code))
    cols[2].metric("折合人民币合计", cny_money(filtered["CNYRevenue"].sum()))
    cols[3].metric("单ASIN人民币中位数", cny_money(filtered["CNYRevenuePerASIN"].median()))
    cols[4].metric("公司适配中位数", f"{filtered['CompanyFitScore'].median():.1f}")
    cols[5].metric(
        "最高最终优先级",
        f"{best['FinalPriorityScore']:.1f}",
        delta=str(best["Category"])[:18],
        delta_color="off",
    )
    st.markdown(
        '<div class="notice"><b>最终优先级</b> = 市场机会分 × 经营准入系数 × 公司适配度。市场很大但普通跨境卖家无法合法、稳定经营的类目，不会因为“数据蓝海”进入前列。</div>',
        unsafe_allow_html=True,
    )

    ranked = filtered.sort_values(
        ["FinalPriorityScore", "OpportunityScore", "DataQualityScore", "Revenue"],
        ascending=False,
    ).reset_index(drop=True)
    ranked.insert(0, "Rank", np.arange(1, len(ranked) + 1))
    columns = [
        "Rank",
        "BusinessDecision",
        "EntryLabel",
        "FinalPriorityLevel",
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
        "MonetizationFactor",
        "EfficiencyFactor",
        "PainFactor",
        "DataQualityScore",
        "Revenue",
        "CNYRevenue",
        "Sales",
        "ASP",
        "CNYASP",
        "ASINCount",
        "RevenuePerASIN",
        "CNYRevenuePerASIN",
        "SearchPerASIN",
        "BarrierReasons",
        "RequiredResources",
        "BarrierRuleConfidence",
        "TopKeyword",
        "DataFlags",
        "Link",
    ]
    st.dataframe(
        ranked[columns],
        hide_index=True,
        use_container_width=True,
        height=700,
        column_config={
            "Rank": st.column_config.NumberColumn("排名", format="%d"),
            "BusinessDecision": st.column_config.TextColumn("经营决策"),
            "EntryLabel": st.column_config.TextColumn("经营准入"),
            "FinalPriorityLevel": st.column_config.TextColumn("最终等级"),
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
            "MonetizationFactor": st.column_config.ProgressColumn("变现", min_value=0, max_value=100, format="%.0f"),
            "EfficiencyFactor": st.column_config.ProgressColumn("效率", min_value=0, max_value=100, format="%.0f"),
            "PainFactor": st.column_config.ProgressColumn("痛点", min_value=0, max_value=100, format="%.0f"),
            "DataQualityScore": st.column_config.ProgressColumn("数据置信度", min_value=0, max_value=100, format="%.0f"),
            "Revenue": st.column_config.NumberColumn("本位币销售额", format=f"{config.currency_symbol}%.0f"),
            "CNYRevenue": st.column_config.NumberColumn("人民币销售额", format="CN¥%.0f"),
            "Sales": st.column_config.NumberColumn("销量", format="%.0f"),
            "ASP": st.column_config.NumberColumn("本位币均价", format=f"{config.currency_symbol}%.2f"),
            "CNYASP": st.column_config.NumberColumn("人民币均价", format="CN¥%.2f"),
            "ASINCount": st.column_config.NumberColumn("ASIN数", format="%.0f"),
            "RevenuePerASIN": st.column_config.NumberColumn("本位币单ASIN", format=f"{config.currency_symbol}%.0f"),
            "CNYRevenuePerASIN": st.column_config.NumberColumn("人民币单ASIN", format="CN¥%.0f"),
            "SearchPerASIN": st.column_config.NumberColumn("搜索/ASIN", format="%.1f"),
            "BarrierReasons": st.column_config.TextColumn("主要障碍/条件", width="large"),
            "RequiredResources": st.column_config.TextColumn("所需资源", width="large"),
            "BarrierRuleConfidence": st.column_config.TextColumn("准入判断置信度"),
            "DataFlags": st.column_config.TextColumn("数据提示", width="large"),
            "Link": st.column_config.LinkColumn("Amazon", display_text="打开 ↗"),
        },
    )
    export_columns = [c for c in columns if c != "Rank"]
    st.download_button(
        "下载当前可经营候选 CSV",
        ranked[export_columns].to_csv(index=False).encode("utf-8-sig"),
        f"{market_code}_{strategy}_business_opportunities_{datetime.now():%Y%m%d_%H%M}.csv",
        "text/csv",
        use_container_width=True,
    )


def render_matrix(filtered: pd.DataFrame) -> None:
    if filtered.empty:
        st.info("没有可绘制的数据。")
        return
    options = {
        "ASIN数量（供给竞争）": "ASINCount",
        "本位币销售额": "Revenue",
        "人民币销售额": "CNYRevenue",
        "市场销量": "Sales",
        "搜索量": "SearchVolume",
        "人民币单ASIN收入": "CNYRevenuePerASIN",
        "单ASIN销量": "UnitsPerASIN",
        "搜索/ASIN": "SearchPerASIN",
        "人民币平均价格": "CNYASP",
        "市场机会分": "OpportunityScore",
        "最终优先级": "FinalPriorityScore",
        "公司适配": "CompanyFitScore",
        "跨境友好度": "CrossBorderFriendliness",
    }
    a, b, c, d = st.columns(4)
    x_label = a.selectbox("横轴", list(options), index=0)
    y_label = b.selectbox("纵轴", list(options), index=2)
    bubble_label = c.selectbox("气泡大小", list(options), index=5)
    color_label = d.selectbox("颜色", ["经营准入", "经营决策", "标准大类", "监管类型"])
    log_axes = st.toggle("正数轴使用对数刻度", True)
    x, y, size = options[x_label], options[y_label], options[bubble_label]
    color = {
        "经营准入": "EntryLabel",
        "经营决策": "BusinessDecision",
        "标准大类": "RootStandard",
        "监管类型": "RegulatoryFamily",
    }[color_label]
    plot = filtered.dropna(subset=[x, y, size]).copy()
    if log_axes:
        plot = plot.loc[plot[x].gt(0) & plot[y].gt(0)]
    if plot.empty:
        st.info("当前指标组合没有足够有效数据。")
        return
    plot["Bubble"] = pd.to_numeric(plot[size], errors="coerce").clip(lower=0).fillna(0) + 1e-9
    max_labels = min(40, len(plot))
    count = st.slider("显示类目标签数量", 0, max_labels, min(12, max_labels))
    indexes = plot.nlargest(count, "FinalPriorityScore").index if count else pd.Index([])
    plot["Label"] = np.where(plot.index.isin(indexes), plot["Category"].astype("string").fillna(""), "")
    fig = px.scatter(
        plot,
        x=x,
        y=y,
        size="Bubble",
        color=color,
        text="Label",
        hover_name="Category",
        hover_data={
            "CategoryLocal": True,
            "EntryLabel": True,
            "FinalPriorityScore": ":.1f",
            "OpportunityScore": ":.1f",
            "CompanyFitScore": ":.0f",
            "ASINCount": ":,.0f",
            "DataQualityScore": ":.0f",
            "Bubble": False,
            "Label": False,
        },
        log_x=log_axes,
        log_y=log_axes,
        size_max=58,
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


def render_entry_research(scored: pd.DataFrame, market_code: str) -> None:
    config = MARKETS[market_code]
    market = scored.loc[
        scored["MarketCode"].eq(market_code)
        & scored["EligibleCore"].fillna(False)
        & scored["EntryClass"].isin(["C", "D"])
    ].copy()
    st.markdown(
        '<div class="warning-note"><b>受监管市场研究区：</b>这里保留市场很大但普通跨境卖家难以进入的类目。它们可用于行业研究、寻找当地合作商或评估未来能力建设，但默认不进入选品推荐。</div>',
        unsafe_allow_html=True,
    )
    if market.empty:
        st.info("当前站点没有C/D类目。")
        return
    selected = st.multiselect("查看准入等级", ["C", "D"], default=["C", "D"], key="entry_research_levels")
    families = sorted(market["RegulatoryFamily"].astype("string").dropna().unique().tolist())
    selected_families = st.multiselect("监管/经营类型", families, default=families, key="entry_research_families")
    view = market.loc[market["EntryClass"].isin(selected) & market["RegulatoryFamily"].isin(selected_families)].copy()
    if view.empty:
        st.info("当前筛选没有记录。")
        return
    cols = st.columns(5)
    cols[0].metric("研究类目", f"{len(view):,}")
    cols[1].metric("C级", f"{view['EntryClass'].eq('C').sum():,}")
    cols[2].metric("D级", f"{view['EntryClass'].eq('D').sum():,}")
    cols[3].metric("市场机会分中位数", f"{view['OpportunityScore'].median():.1f}")
    cols[4].metric("折合人民币规模", cny_money(view["CNYRevenue"].sum()))

    ranked = view.sort_values(["OpportunityScore", "CNYRevenue", "DataQualityScore"], ascending=False)
    columns = [
        "EntryLabel",
        "BusinessDecision",
        "Category",
        "CategoryLocal",
        "RootStandard",
        "RegulatoryFamily",
        "OpportunityScore",
        "FinalPriorityScore",
        "Revenue",
        "CNYRevenue",
        "CompanyFitScore",
        "BarrierReasons",
        "RequiredResources",
        "RequiredCapability",
        "CapabilityMatched",
        "BarrierRuleConfidence",
        "DataQualityScore",
        "Link",
    ]
    st.dataframe(
        ranked[columns].head(1000),
        hide_index=True,
        use_container_width=True,
        height=690,
        column_config={
            "EntryLabel": st.column_config.TextColumn("准入等级"),
            "BusinessDecision": st.column_config.TextColumn("默认决策"),
            "Category": st.column_config.TextColumn("中文类目", width="medium"),
            "CategoryLocal": st.column_config.TextColumn("当地名称", width="medium"),
            "RootStandard": st.column_config.TextColumn("标准大类"),
            "RegulatoryFamily": st.column_config.TextColumn("监管/经营类型"),
            "OpportunityScore": st.column_config.ProgressColumn("市场机会分", min_value=0, max_value=100, format="%.1f"),
            "FinalPriorityScore": st.column_config.ProgressColumn("最终优先级", min_value=0, max_value=100, format="%.1f"),
            "Revenue": st.column_config.NumberColumn("本位币销售额", format=f"{config.currency_symbol}%.0f"),
            "CNYRevenue": st.column_config.NumberColumn("人民币销售额", format="CN¥%.0f"),
            "CompanyFitScore": st.column_config.ProgressColumn("公司适配", min_value=0, max_value=100, format="%.0f"),
            "BarrierReasons": st.column_config.TextColumn("为什么被拦截", width="large"),
            "RequiredResources": st.column_config.TextColumn("需要什么才能做", width="large"),
            "RequiredCapability": st.column_config.TextColumn("所需能力代码"),
            "CapabilityMatched": st.column_config.CheckboxColumn("已声明具备"),
            "BarrierRuleConfidence": st.column_config.TextColumn("判断置信度"),
            "DataQualityScore": st.column_config.ProgressColumn("数据置信度", min_value=0, max_value=100, format="%.0f"),
            "Link": st.column_config.LinkColumn("Amazon", display_text="打开 ↗"),
        },
    )
