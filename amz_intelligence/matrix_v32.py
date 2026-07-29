from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


def render_matrix_v32(filtered: pd.DataFrame) -> None:
    if filtered.empty:
        st.info("没有可绘制的数据。")
        return

    options = {
        "ASIN数量（供给竞争）": "ASINCount",
        "人民币销售额": "CNYRevenue",
        "市场销量": "Sales",
        "搜索量": "SearchVolume",
        "人民币单ASIN收入": "CNYRevenuePerASIN",
        "单ASIN销量": "UnitsPerASIN",
        "搜索/ASIN": "SearchPerASIN",
        "人民币平均价格": "CNYASP",
        "当前市场机会分": "OpportunityScore",
        "当前策略规则调整分": "FinalPriorityScore",
        "五策略中位规则分": "ConsensusPriorityScore",
        "五策略保守下限": "ConservativePriorityScore",
        "策略一致度": "StrategyAgreementScore",
        "Top20%策略支持数": "StrategySupportCount",
        "证据字段覆盖": "EvidenceCoverageScore",
        "数据置信度": "DataQualityScore",
        "跨境规则友好度": "CrossBorderFriendliness",
    }
    if filtered.get("CompanyFitApplied", pd.Series(False, index=filtered.index)).fillna(False).any():
        options["人工公司适配分"] = "CompanyFitScore"

    a, b, c, d = st.columns(4)
    labels = list(options)
    x_label = a.selectbox("横轴", labels, index=0, key="v32_matrix_x")
    y_label = b.selectbox("纵轴", labels, index=1, key="v32_matrix_y")
    bubble_label = c.selectbox("气泡大小", labels, index=4, key="v32_matrix_size")
    color_label = d.selectbox(
        "颜色",
        ["规则等级", "策略稳健性", "标准大类", "风险类型", "经营决策"],
        key="v32_matrix_color",
    )
    log_axes = st.toggle("正数轴使用对数刻度", True, key="v32_matrix_log")

    x, y, size = options[x_label], options[y_label], options[bubble_label]
    color = {
        "规则等级": "EntryClass",
        "策略稳健性": "StrategyRobustnessLabel",
        "标准大类": "RootStandard",
        "风险类型": "RegulatoryFamily",
        "经营决策": "BusinessDecision",
    }[color_label]
    plot = filtered.dropna(subset=[x, y, size]).copy()
    if log_axes:
        plot = plot.loc[
            pd.to_numeric(plot[x], errors="coerce").gt(0)
            & pd.to_numeric(plot[y], errors="coerce").gt(0)
        ]
    if plot.empty:
        st.info("当前指标组合没有足够有效数据。")
        return

    plot["Bubble"] = pd.to_numeric(plot[size], errors="coerce").clip(lower=0).fillna(0) + 1e-9
    max_labels = min(40, len(plot))
    count = st.slider(
        "显示类目标签数量",
        0,
        max_labels,
        min(12, max_labels),
        key="v32_matrix_label_count",
    )
    label_rank = "ConsensusPriorityScore" if "ConsensusPriorityScore" in plot else "OpportunityScore"
    indexes = plot.nlargest(count, label_rank).index if count else pd.Index([])
    plot["Label"] = np.where(
        plot.index.isin(indexes),
        plot["Category"].astype("string").fillna(""),
        "",
    )

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
            "EntryInterpretation": True,
            "ConsensusPriorityScore": ":.1f",
            "ConservativePriorityScore": ":.1f",
            "StrategyAgreementScore": ":.1f",
            "OpportunityScore": ":.1f",
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
    median_x = float(pd.to_numeric(plot[x], errors="coerce").median())
    median_y = float(pd.to_numeric(plot[y], errors="coerce").median())
    if np.isfinite(median_x) and (median_x > 0 or not log_axes):
        fig.add_vline(x=median_x, line_dash="dot", line_color="#64748b", annotation_text="横轴中位线")
    if np.isfinite(median_y) and (median_y > 0 or not log_axes):
        fig.add_hline(y=median_y, line_dash="dot", line_color="#64748b", annotation_text="纵轴中位线")
    fig.update_traces(textposition="top center", textfont_size=10)
    fig.update_layout(height=760, legend_orientation="h")
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    st.caption("气泡图展示权衡关系，不等同于自动立项。默认标签按五策略中位规则分选择。")
