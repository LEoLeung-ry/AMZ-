from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .config import FACTOR_LABELS, MARKETS
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


def _quantile(series: pd.Series, value: float) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return float(numeric.quantile(value)) if not numeric.empty else np.nan


def _rank_column_label(column: str) -> str:
    return {
        "FinalPriorityScore": "当前策略最终分",
        "ConsensusPriorityScore": "五策略中位分",
        "ConservativePriorityScore": "五策略保守下限",
    }.get(column, column)


def render_overview_v32(scored: pd.DataFrame) -> None:
    st.markdown(
        '<div class="notice"><b>重要：</b>类目节点可能存在父子层级重叠，因此本页不再把所有类目销售额直接相加。跨站比较使用类目中位数、P90、站内分位和人民币折算，避免制造虚假的“市场总量”。</div>',
        unsafe_allow_html=True,
    )
    rows: list[dict[str, object]] = []
    for code, config in MARKETS.items():
        market = scored.loc[scored["MarketCode"].eq(code)].copy()
        if market.empty:
            continue
        physical = market.loc[market["EligiblePhysical"].fillna(False)]
        business = market.loc[market["DefaultBusinessEligible"].fillna(False)]
        rows.append(
            {
                "站点": f"{config.flag} {config.name}",
                "总记录": len(market),
                "默认主榜候选": int(market["DefaultBusinessEligible"].sum()),
                "C/D规则预警": int(market["EntryClass"].isin(["C", "D"]).sum()),
                "类目销售额中位数": money(physical["Revenue"].median(), code),
                "人民币中位数": cny_money(physical["CNYRevenue"].median()),
                "人民币P90": cny_money(_quantile(physical["CNYRevenue"], 0.90)),
                "单ASIN人民币中位数": cny_money(physical["CNYRevenuePerASIN"].median()),
                "五策略共识中位数": business["ConsensusPriorityScore"].median(),
                "策略一致度中位数": business["StrategyAgreementScore"].median(),
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
            "默认主榜候选": st.column_config.NumberColumn(format="%d"),
            "C/D规则预警": st.column_config.NumberColumn(format="%d"),
            "五策略共识中位数": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "策略一致度中位数": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
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

    st.markdown("### 每站当前 Top 5｜五策略共识候选")
    st.caption("这里使用五种标准市场策略的中位分排序，不依赖某一个权重方案；仍然只展示A/B规则等级。")
    rows = []
    for code, config in MARKETS.items():
        top = scored.loc[
            scored["MarketCode"].eq(code) & scored["DefaultBusinessEligible"].fillna(False)
        ].nlargest(5, "ConsensusPriorityScore")
        for _, row in top.iterrows():
            rows.append(
                {
                    "站点": f"{config.flag} {config.name}",
                    "类目": row["Category"],
                    "当地名称": row["CategoryLocal"],
                    "准入解释": row["EntryInterpretation"],
                    "五策略中位分": row["ConsensusPriorityScore"],
                    "保守下限": row["ConservativePriorityScore"],
                    "策略一致度": row["StrategyAgreementScore"],
                    "Top20%支持数": row["StrategySupportCount"],
                    "市场机会分": row["OpportunityScore"],
                    "本位币销售额": money(row["Revenue"], code),
                    "人民币销售额": cny_money(row["CNYRevenue"]),
                    "规则核验状态": row["RuleVerificationStatus"],
                    "数据置信度": row["DataQualityScore"],
                    "链接": row["Link"],
                }
            )
    top_frame = pd.DataFrame(rows)
    if top_frame.empty:
        st.info("当前没有A/B规则等级候选。")
        return
    st.dataframe(
        top_frame,
        hide_index=True,
        use_container_width=True,
        column_config={
            "五策略中位分": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "保守下限": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "策略一致度": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "Top20%支持数": st.column_config.NumberColumn(format="%d"),
            "市场机会分": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "数据置信度": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "准入解释": st.column_config.TextColumn(width="large"),
            "规则核验状态": st.column_config.TextColumn(width="large"),
            "链接": st.column_config.LinkColumn(display_text="打开 ↗"),
        },
    )


def render_opportunities_v32(
    filtered: pd.DataFrame,
    market_code: str,
    strategy: str,
    *,
    rank_column: str = "FinalPriorityScore",
) -> None:
    if filtered.empty:
        st.info("没有符合当前筛选条件的候选类目。")
        return
    config = MARKETS[market_code]
    rank_label = _rank_column_label(rank_column)
    ranked = filtered.sort_values(
        [rank_column, "StrategyAgreementScore", "DataQualityScore", "Revenue"],
        ascending=False,
    ).reset_index(drop=True)
    ranked.insert(0, "Rank", np.arange(1, len(ranked) + 1))
    ranked["RankScore"] = ranked[rank_column]

    cols = st.columns(6)
    cols[0].metric("候选类目", f"{len(ranked):,}")
    cols[1].metric("类目销售额中位数", money(ranked["Revenue"].median(), market_code))
    cols[2].metric("人民币销售额P90", cny_money(_quantile(ranked["CNYRevenue"], 0.90)))
    cols[3].metric("单ASIN人民币中位数", cny_money(ranked["CNYRevenuePerASIN"].median()))
    cols[4].metric("策略一致度中位数", f"{ranked['StrategyAgreementScore'].median():.1f}")
    cols[5].metric("高/中共识候选", f"{ranked['StrategyRobustnessLabel'].isin(['高共识', '中共识']).sum():,}")
    st.markdown(
        f'<div class="notice"><b>当前排序：</b>{rank_label}。页面不汇总重叠类目销售额；“策略一致度”只表示换权重后结果是否稳定，不是成功概率。</div>',
        unsafe_allow_html=True,
    )

    view_mode = st.radio("表格视图", ["核心决策", "完整审计"], horizontal=True, key="v32_table_view")
    core_columns = [
        "Rank",
        "Category",
        "CategoryLocal",
        "RootStandard",
        "BusinessDecision",
        "EntryInterpretation",
        "RankScore",
        "FinalPriorityScore",
        "ConsensusPriorityScore",
        "ConservativePriorityScore",
        "StrategyAgreementScore",
        "StrategySupportCount",
        "StrategyRobustnessLabel",
        "OpportunityScore",
        "DataQualityScore",
        "EvidenceCoverageScore",
        "Revenue",
        "CNYRevenue",
        "ASP",
        "CNYASP",
        "ASINCount",
        "CNYRevenuePerASIN",
        "SearchPerASIN",
        "RuleVerificationStatus",
        "ProfileInfluence",
        "Link",
    ]
    audit_columns = core_columns[:-1] + [
        "MarketFactor",
        "DemandFactor",
        "AccessFactor",
        "MonetizationFactor",
        "EfficiencyFactor",
        "PainFactor",
        "CrossBorderFriendliness",
        "CompanyFitScore",
        "RegulatoryFamily",
        "BarrierRuleCode",
        "BarrierReasons",
        "RequiredResources",
        "BarrierRuleConfidence",
        "SourceMetricAgreementScore",
        "TopKeyword",
        "TopKeywordConcentrationPct",
        "NodePath",
        "DataFlags",
        "Link",
    ]
    columns = core_columns if view_mode == "核心决策" else audit_columns

    st.dataframe(
        ranked[columns],
        hide_index=True,
        use_container_width=True,
        height=720,
        column_config={
            "Rank": st.column_config.NumberColumn("排名", format="%d"),
            "Category": st.column_config.TextColumn("中文类目", width="medium"),
            "CategoryLocal": st.column_config.TextColumn("当地名称", width="medium"),
            "RootStandard": st.column_config.TextColumn("标准大类"),
            "BusinessDecision": st.column_config.TextColumn("经营决策"),
            "EntryInterpretation": st.column_config.TextColumn("准入解释", width="large"),
            "RankScore": st.column_config.ProgressColumn(rank_label, min_value=0, max_value=100, format="%.1f"),
            "FinalPriorityScore": st.column_config.ProgressColumn("当前策略最终分", min_value=0, max_value=100, format="%.1f"),
            "ConsensusPriorityScore": st.column_config.ProgressColumn("五策略中位分", min_value=0, max_value=100, format="%.1f"),
            "ConservativePriorityScore": st.column_config.ProgressColumn("保守下限", min_value=0, max_value=100, format="%.1f"),
            "StrategyAgreementScore": st.column_config.ProgressColumn("策略一致度", min_value=0, max_value=100, format="%.1f"),
            "StrategySupportCount": st.column_config.NumberColumn("Top20%支持数", format="%d"),
            "OpportunityScore": st.column_config.ProgressColumn("市场机会分", min_value=0, max_value=100, format="%.1f"),
            "DataQualityScore": st.column_config.ProgressColumn("数据置信度", min_value=0, max_value=100, format="%.0f"),
            "EvidenceCoverageScore": st.column_config.ProgressColumn("证据字段覆盖", min_value=0, max_value=100, format="%.0f"),
            "SourceMetricAgreementScore": st.column_config.ProgressColumn("源指标一致性", min_value=0, max_value=100, format="%.0f"),
            "Revenue": st.column_config.NumberColumn("本位币销售额", format=f"{config.currency_symbol}%.0f"),
            "CNYRevenue": st.column_config.NumberColumn("人民币销售额", format="CN¥%.0f"),
            "ASP": st.column_config.NumberColumn("本位币均价", format=f"{config.currency_symbol}%.2f"),
            "CNYASP": st.column_config.NumberColumn("人民币均价", format="CN¥%.2f"),
            "ASINCount": st.column_config.NumberColumn("ASIN数", format="%.0f"),
            "CNYRevenuePerASIN": st.column_config.NumberColumn("人民币单ASIN", format="CN¥%.0f"),
            "SearchPerASIN": st.column_config.NumberColumn("搜索/ASIN", format="%.1f"),
            "RuleVerificationStatus": st.column_config.TextColumn("规则核验状态", width="large"),
            "ProfileInfluence": st.column_config.TextColumn("画像影响", width="large"),
            "BarrierReasons": st.column_config.TextColumn("规则触发原因", width="large"),
            "RequiredResources": st.column_config.TextColumn("推进所需资源", width="large"),
            "NodePath": st.column_config.TextColumn("Node Path", width="large"),
            "DataFlags": st.column_config.TextColumn("数据提示", width="large"),
            "Link": st.column_config.LinkColumn("Amazon", display_text="打开 ↗"),
        },
    )
    export_columns = [column for column in audit_columns if column != "Rank"]
    st.download_button(
        "下载当前候选 CSV",
        ranked[export_columns].to_csv(index=False).encode("utf-8-sig"),
        f"{market_code}_{strategy}_v32_candidates_{datetime.now():%Y%m%d_%H%M}.csv",
        "text/csv",
        use_container_width=True,
    )


def render_robustness_v32(scored: pd.DataFrame, market_code: str) -> None:
    market = scored.loc[
        scored["MarketCode"].eq(market_code) & scored["DefaultBusinessEligible"].fillna(False)
    ].copy()
    st.markdown(
        '<div class="notice"><b>策略稳健性：</b>同一类目分别套用大单品、蓝海、高客单、结构性需求、稳健优先五套权重。分数区间越小、进入各策略Top20%的次数越多，说明结果越不依赖单一权重。</div>',
        unsafe_allow_html=True,
    )
    if market.empty:
        st.info("当前站点没有可计算的A/B候选。")
        return

    cols = st.columns(5)
    cols[0].metric("A/B候选", f"{len(market):,}")
    cols[1].metric("高共识", f"{market['StrategyRobustnessLabel'].eq('高共识').sum():,}")
    cols[2].metric("中共识", f"{market['StrategyRobustnessLabel'].eq('中共识').sum():,}")
    cols[3].metric("策略敏感", f"{market['StrategyRobustnessLabel'].eq('策略敏感').sum():,}")
    cols[4].metric("分数区间中位数", f"{market['StrategyPriorityRange'].median():.1f}")

    plot = market.dropna(
        subset=["ConsensusPriorityScore", "StrategyAgreementScore", "CNYRevenuePerASIN"]
    ).copy()
    if not plot.empty:
        plot["Bubble"] = pd.to_numeric(plot["CNYRevenuePerASIN"], errors="coerce").clip(lower=0).fillna(0) + 1
        fig = px.scatter(
            plot,
            x="ConsensusPriorityScore",
            y="StrategyAgreementScore",
            size="Bubble",
            color="StrategyRobustnessLabel",
            hover_name="Category",
            hover_data={
                "CategoryLocal": True,
                "StrategySupportCount": True,
                "ConservativePriorityScore": ":.1f",
                "OptimisticPriorityScore": ":.1f",
                "CNYRevenuePerASIN": ":,.0f",
                "Bubble": False,
            },
            labels={
                "ConsensusPriorityScore": "五策略中位分",
                "StrategyAgreementScore": "策略一致度",
                "StrategyRobustnessLabel": "稳健性",
            },
            title="候选的权重敏感性",
            size_max=55,
        )
        fig.update_layout(height=620, yaxis_range=[0, 100], xaxis_range=[0, 100])
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

    ranked = market.sort_values(
        ["ConsensusPriorityScore", "StrategyAgreementScore", "DataQualityScore"], ascending=False
    )
    columns = [
        "Category",
        "CategoryLocal",
        "EntryInterpretation",
        "ConsensusPriorityScore",
        "ConservativePriorityScore",
        "OptimisticPriorityScore",
        "StrategyPriorityRange",
        "StrategyAgreementScore",
        "StrategySupportCount",
        "StrategyRobustnessLabel",
        "OpportunityScore",
        "DataQualityScore",
        "EvidenceCoverageScore",
        "CNYRevenue",
        "CNYRevenuePerASIN",
        "RuleVerificationStatus",
        "Link",
    ]
    st.dataframe(
        ranked[columns].head(1000),
        hide_index=True,
        use_container_width=True,
        height=680,
        column_config={
            "Category": st.column_config.TextColumn("中文类目", width="medium"),
            "CategoryLocal": st.column_config.TextColumn("当地名称", width="medium"),
            "EntryInterpretation": st.column_config.TextColumn("准入解释", width="large"),
            "ConsensusPriorityScore": st.column_config.ProgressColumn("五策略中位分", min_value=0, max_value=100, format="%.1f"),
            "ConservativePriorityScore": st.column_config.ProgressColumn("保守下限", min_value=0, max_value=100, format="%.1f"),
            "OptimisticPriorityScore": st.column_config.ProgressColumn("乐观上限", min_value=0, max_value=100, format="%.1f"),
            "StrategyPriorityRange": st.column_config.NumberColumn("分数区间", format="%.1f"),
            "StrategyAgreementScore": st.column_config.ProgressColumn("策略一致度", min_value=0, max_value=100, format="%.1f"),
            "StrategySupportCount": st.column_config.NumberColumn("Top20%支持数", format="%d"),
            "OpportunityScore": st.column_config.ProgressColumn("当前市场机会分", min_value=0, max_value=100, format="%.1f"),
            "DataQualityScore": st.column_config.ProgressColumn("数据置信度", min_value=0, max_value=100, format="%.0f"),
            "EvidenceCoverageScore": st.column_config.ProgressColumn("证据字段覆盖", min_value=0, max_value=100, format="%.0f"),
            "CNYRevenue": st.column_config.NumberColumn("人民币销售额", format="CN¥%.0f"),
            "CNYRevenuePerASIN": st.column_config.NumberColumn("人民币单ASIN", format="CN¥%.0f"),
            "RuleVerificationStatus": st.column_config.TextColumn("规则核验状态", width="large"),
            "Link": st.column_config.LinkColumn("Amazon", display_text="打开 ↗"),
        },
    )


def render_entry_research_v32(scored: pd.DataFrame, market_code: str) -> None:
    config = MARKETS[market_code]
    market = scored.loc[
        scored["MarketCode"].eq(market_code)
        & scored["EligibleCore"].fillna(False)
        & scored["EntryClass"].isin(["C", "D"])
    ].copy()
    st.markdown(
        '<div class="warning-note"><b>这里是规则预警区，不是法规结论。</b> C/D来自内部关键词与根类目规则，只用于阻止明显高门槛类目挤入普通选品榜；具体产品仍需按目标国、成分、用途、宣称和平台政策核验。</div>',
        unsafe_allow_html=True,
    )
    if market.empty:
        st.info("当前站点没有C/D规则预警。")
        return
    levels = st.multiselect("规则等级", ["C", "D"], default=["C", "D"], key="v32_entry_levels")
    families = sorted(market["RegulatoryFamily"].astype("string").dropna().unique().tolist())
    selected_families = st.multiselect(
        "风险类型", families, default=families, key="v32_entry_families"
    )
    view = market.loc[
        market["EntryClass"].isin(levels) & market["RegulatoryFamily"].isin(selected_families)
    ].copy()
    if view.empty:
        st.info("当前筛选没有记录。")
        return

    cols = st.columns(5)
    cols[0].metric("规则预警类目", f"{len(view):,}")
    cols[1].metric("C级", f"{view['EntryClass'].eq('C').sum():,}")
    cols[2].metric("D级", f"{view['EntryClass'].eq('D').sum():,}")
    cols[3].metric("市场机会分中位数", f"{view['OpportunityScore'].median():.1f}")
    cols[4].metric("人民币销售额P90", cny_money(_quantile(view["CNYRevenue"], 0.90)))

    ranked = view.sort_values(["OpportunityScore", "CNYRevenue", "DataQualityScore"], ascending=False)
    columns = [
        "EntryInterpretation",
        "Category",
        "CategoryLocal",
        "RootStandard",
        "RegulatoryFamily",
        "OpportunityScore",
        "ConsensusPriorityScore",
        "Revenue",
        "CNYRevenue",
        "BarrierRuleCode",
        "BarrierReasons",
        "RequiredResources",
        "BarrierRuleConfidence",
        "RuleNature",
        "RuleVerificationStatus",
        "EvidenceCoverageScore",
        "DataQualityScore",
        "NodePath",
        "Link",
    ]
    st.dataframe(
        ranked[columns].head(1000),
        hide_index=True,
        use_container_width=True,
        height=700,
        column_config={
            "EntryInterpretation": st.column_config.TextColumn("规则解释", width="large"),
            "Category": st.column_config.TextColumn("中文类目", width="medium"),
            "CategoryLocal": st.column_config.TextColumn("当地名称", width="medium"),
            "OpportunityScore": st.column_config.ProgressColumn("市场机会分", min_value=0, max_value=100, format="%.1f"),
            "ConsensusPriorityScore": st.column_config.ProgressColumn("五策略中位分", min_value=0, max_value=100, format="%.1f"),
            "Revenue": st.column_config.NumberColumn("本位币销售额", format=f"{config.currency_symbol}%.0f"),
            "CNYRevenue": st.column_config.NumberColumn("人民币销售额", format="CN¥%.0f"),
            "BarrierReasons": st.column_config.TextColumn("规则触发原因", width="large"),
            "RequiredResources": st.column_config.TextColumn("可能需要的资源", width="large"),
            "RuleVerificationStatus": st.column_config.TextColumn("核验状态", width="large"),
            "EvidenceCoverageScore": st.column_config.ProgressColumn("证据字段覆盖", min_value=0, max_value=100, format="%.0f"),
            "DataQualityScore": st.column_config.ProgressColumn("数据置信度", min_value=0, max_value=100, format="%.0f"),
            "NodePath": st.column_config.TextColumn("Node Path", width="large"),
            "Link": st.column_config.LinkColumn("Amazon", display_text="打开 ↗"),
        },
    )


def render_cross_market_v32(scored: pd.DataFrame, default_query: str = "") -> None:
    st.markdown(
        '<div class="notice">跨站点匹配仍然只是名称和关键词候选。人民币解决金额量纲问题，五策略中位分解决单一权重问题，但都不能证明不同站点Browse Node完全等价。</div>',
        unsafe_allow_html=True,
    )
    query = st.text_input(
        "输入产品或类目关键词",
        default_query,
        placeholder="例如 handheld fan、剃须刀、storage box",
        key="v32_compare_query",
    )
    if not query.strip():
        st.info("输入关键词后，同时搜索四站中文名、当地名、热门关键词和Node Path。")
        return
    matched = scored.loc[
        text_match_mask(scored, query) & scored["EligibleCore"].fillna(False)
    ].copy()
    if matched.empty:
        st.warning("四站均未找到匹配类目。")
        return
    matched["匹配置信度"] = matched.apply(lambda row: match_confidence(row, query), axis=1)
    matched = matched.sort_values(
        ["MarketCode", "ConsensusPriorityScore", "StrategyAgreementScore", "DataQualityScore"],
        ascending=[True, False, False, False],
    )
    matched = matched.groupby("MarketCode", as_index=False, group_keys=False, observed=True).head(25)
    matched["站点"] = combine_text_columns(matched, ["MarketFlag", "Market"])
    columns = [
        "站点",
        "匹配置信度",
        "Category",
        "CategoryLocal",
        "RootStandard",
        "EntryInterpretation",
        "ConsensusPriorityScore",
        "ConservativePriorityScore",
        "StrategyAgreementScore",
        "StrategySupportCount",
        "OpportunityScore",
        "CNYRevenue",
        "CNYASP",
        "CNYRevenuePerASIN",
        "ASINCount",
        "SnapshotLabel",
        "RuleVerificationStatus",
        "DataQualityScore",
        "Link",
    ]
    st.dataframe(
        matched[columns],
        hide_index=True,
        use_container_width=True,
        height=680,
        column_config={
            "Category": st.column_config.TextColumn("中文类目", width="medium"),
            "CategoryLocal": st.column_config.TextColumn("当地名称", width="medium"),
            "EntryInterpretation": st.column_config.TextColumn("准入解释", width="large"),
            "ConsensusPriorityScore": st.column_config.ProgressColumn("五策略中位分", min_value=0, max_value=100, format="%.1f"),
            "ConservativePriorityScore": st.column_config.ProgressColumn("保守下限", min_value=0, max_value=100, format="%.1f"),
            "StrategyAgreementScore": st.column_config.ProgressColumn("策略一致度", min_value=0, max_value=100, format="%.1f"),
            "StrategySupportCount": st.column_config.NumberColumn("Top20%支持数", format="%d"),
            "OpportunityScore": st.column_config.ProgressColumn("当前市场机会分", min_value=0, max_value=100, format="%.1f"),
            "CNYRevenue": st.column_config.NumberColumn("人民币销售额", format="CN¥%.0f"),
            "CNYASP": st.column_config.NumberColumn("人民币均价", format="CN¥%.2f"),
            "CNYRevenuePerASIN": st.column_config.NumberColumn("人民币单ASIN", format="CN¥%.0f"),
            "ASINCount": st.column_config.NumberColumn("ASIN数", format="%.0f"),
            "RuleVerificationStatus": st.column_config.TextColumn("规则核验状态", width="large"),
            "DataQualityScore": st.column_config.ProgressColumn("数据置信度", min_value=0, max_value=100, format="%.0f"),
            "Link": st.column_config.LinkColumn("Amazon", display_text="打开 ↗"),
        },
    )


def render_diagnosis_v32(pool: pd.DataFrame, market_code: str) -> None:
    if pool.empty:
        st.info("没有可诊断类目。")
        return
    pool = pool.sort_values(["ConsensusPriorityScore", "OpportunityScore"], ascending=False).copy()
    pool["SelectLabel"] = (
        pool["Category"].astype("string").fillna("")
        .str.cat(pool["CategoryLocal"].astype("string").fillna("").str.slice(0, 32), sep="｜")
        .str.cat(pool["CategoryID"].astype("string").fillna(""), sep="｜ID ")
    )
    selected = st.selectbox("选择一个类目", pool["SelectLabel"].tolist(), key="v32_diagnosis_select")
    row = pool.loc[pool["SelectLabel"].eq(selected)].iloc[0]
    code = safe_text(row["MarketCode"])
    st.markdown(f"## {safe_text(row['Category'])}")
    st.caption(
        f"{safe_text(row['MarketFlag'])} {safe_text(row['Market'])} · {safe_text(row['CategoryLocal'])} · "
        f"{safe_text(row['RootStandard'])} · 类目ID {safe_text(row['CategoryID'])}"
    )
    cols = st.columns(7)
    cols[0].metric("五策略中位分", f"{row['ConsensusPriorityScore']:.1f}")
    cols[1].metric("保守下限", f"{row['ConservativePriorityScore']:.1f}")
    cols[2].metric("策略一致度", f"{row['StrategyAgreementScore']:.1f}")
    cols[3].metric("当前市场机会分", f"{row['OpportunityScore']:.1f}")
    cols[4].metric("规则等级", safe_text(row["EntryClass"]))
    cols[5].metric("人民币销售额", cny_money(row["CNYRevenue"]))
    cols[6].metric("数据置信度", f"{row['DataQualityScore']:.0f}")

    st.markdown(
        f'<div class="warning-note"><b>规则解释：</b>{safe_text(row["EntryInterpretation"])}<br>'
        f'<b>触发原因：</b>{safe_text(row["BarrierReasons"])}<br>'
        f'<b>核验状态：</b>{safe_text(row["RuleVerificationStatus"])}<br>'
        f'<b>画像影响：</b>{safe_text(row["ProfileInfluence"])}</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    factors = list(FACTOR_LABELS)
    values = [float(pd.to_numeric(pd.Series([row.get(factor, 0)]), errors="coerce").fillna(0).iloc[0]) for factor in factors]
    with left:
        fig = go.Figure(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=[FACTOR_LABELS[factor] for factor in factors] + [FACTOR_LABELS[factors[0]]],
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
        st.markdown("### 判断边界")
        st.markdown(f"- 本位币销售额：**{money(row['Revenue'], code)}**")
        st.markdown(f"- 人民币单ASIN收入：**{cny_money(row['CNYRevenuePerASIN'])}**")
        st.markdown(f"- 五策略Top20%支持数：**{int(row['StrategySupportCount'])}/5**")
        st.markdown(f"- 证据字段覆盖：**{row['EvidenceCoverageScore']:.0f}/100**")
        agreement = row.get("SourceMetricAgreementScore")
        st.markdown(
            f"- 源指标与重算一致性：**{agreement:.0f}/100**"
            if pd.notna(agreement)
            else "- 源指标与重算一致性：**无可比源字段**"
        )
        st.markdown("- 该结果仍缺少采购价、物流、广告、退货和产品级法规资料，不能直接替代立项。")
        if has_text(row.get("TopKeyword")):
            st.info(f"热门关键词：{safe_text(row['TopKeyword'])}")
        if has_text(row.get("Link")):
            st.link_button("打开 Amazon 类目页 ↗", safe_text(row["Link"]), use_container_width=True)

    metrics = pd.DataFrame(
        {
            "指标": [
                "近12个月销量",
                "近12个月搜索量",
                "近12个月点击量",
                "近12个月浏览量",
                "ASIN数量",
                "搜索/ASIN",
                "本位币平均价格",
                "人民币平均价格",
                "本位币单ASIN收入",
                "人民币单ASIN收入",
                "头部关键词集中度",
                "低评分结构",
                "高评分结构",
                "Node Path",
                "数据异常",
            ],
            "值": [
                compact_number(row["Sales"]),
                compact_number(row["SearchVolume"]),
                compact_number(row["Clicks"]),
                compact_number(row["Views"]),
                compact_number(row["ASINCount"]),
                compact_number(row["SearchPerASIN"]),
                money(row["ASP"], code),
                cny_money(row["CNYASP"]),
                money(row["RevenuePerASIN"], code),
                cny_money(row["CNYRevenuePerASIN"]),
                f"{row['TopKeywordConcentrationPct']:.2f}%" if pd.notna(row["TopKeywordConcentrationPct"]) else "—",
                f"{row['LowRatingShare']:.2%}" if pd.notna(row["LowRatingShare"]) else "—",
                f"{row['HighRatingShare']:.2%}" if pd.notna(row["HighRatingShare"]) else "—",
                safe_text(row["NodePath"]),
                safe_text(row["DataFlags"]),
            ],
        }
    )
    st.dataframe(metrics, hide_index=True, use_container_width=True)
