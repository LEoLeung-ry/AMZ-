from __future__ import annotations

from typing import Mapping

import pandas as pd
import streamlit as st

from amz_intelligence import (
    CAPABILITY_LABELS,
    DEFAULT_FX_REFERENCE,
    FACTOR_LABELS,
    MARKETS,
    PROFILE_CAPABILITY_DEFAULTS,
    PROFILE_DEFAULTS,
    STRATEGY_PRESETS,
    enrich_entry_rules,
)
from amz_intelligence.actionability_v32 import add_actionability_v32
from amz_intelligence.engine import apply_strategy_score, load_market
from amz_intelligence.matrix_v32 import render_matrix_v32
from amz_intelligence.model_v32 import (
    NEUTRAL_PROFILE,
    NEUTRAL_PROFILE_LABEL,
    add_strategy_robustness,
    apply_decision_model_v32,
)
from amz_intelligence.pages_insight import render_quality, render_trends
from amz_intelligence.pages_v32 import (
    render_diagnosis_v32,
    render_entry_research_v32,
    render_opportunities_v32,
    render_overview_v32,
    render_robustness_v32,
)
from amz_intelligence.parallel_loader_v32 import load_all_markets_parallel
from amz_intelligence.ui_common import (
    apply_visual_system,
    combine_text_columns,
    match_confidence,
    text_match_mask,
)


APP_VERSION = "2026.07.29-v3.2.3-responsive"
PAGE_OPTIONS = [
    "🏆 候选排行榜",
    "🧪 策略稳健性",
    "🧭 多维矩阵",
    "🔬 单类目诊断",
    "🚧 规则预警研究",
    "📈 趋势中心",
    "🧾 数据质量",
    "🌐 全球总览",
    "🔀 跨站点比较",
]
GLOBAL_OVERVIEW_PAGE = "🌐 全球总览"
CROSS_MARKET_PAGE = "🔀 跨站点比较"

OVERVIEW_COLUMNS = [
    "MarketCode",
    "MarketFlag",
    "Market",
    "EligiblePhysical",
    "DefaultBusinessEligible",
    "EntryClass",
    "Revenue",
    "CNYRevenue",
    "CNYRevenuePerASIN",
    "ConsensusPriorityScore",
    "ConservativePriorityScore",
    "StrategyAgreementScore",
    "StrategySupportCount",
    "OpportunityScore",
    "DataQualityScore",
    "Category",
    "CategoryLocal",
    "EntryInterpretation",
    "RuleVerificationStatus",
    "Link",
    *list(FACTOR_LABELS),
]

CROSS_COLUMNS = [
    "MarketCode",
    "MarketFlag",
    "Market",
    "EligibleCore",
    "Category",
    "CategoryCN",
    "CategoryLocal",
    "CategoryID",
    "RootStandard",
    "TopKeyword",
    "NodePath",
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


st.set_page_config(
    page_title="Amazon 全球类目机会系统",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_visual_system()


@st.cache_resource(ttl=1800, show_spinner=False, max_entries=8)
def cached_load_market(market_code: str) -> tuple[pd.DataFrame, dict[str, object]]:
    frame, diagnostics = load_market(market_code)
    return enrich_entry_rules(frame), diagnostics


@st.cache_resource(ttl=1800, show_spinner=False, max_entries=2)
def cached_load_all() -> tuple[pd.DataFrame, dict[str, dict[str, object]], dict[str, str]]:
    frame, diagnostics, errors = load_all_markets_parallel(tuple(MARKETS))
    if not frame.empty:
        frame = enrich_entry_rules(frame)
    return frame, diagnostics, errors


def _fingerprint(market_code: str, diagnostics: Mapping[str, object]) -> str:
    fetch = diagnostics.get("fetch_metadata", {}) if isinstance(diagnostics, Mapping) else {}
    fetched_at = fetch.get("fetched_at", "") if isinstance(fetch, Mapping) else ""
    return f"{market_code}:{diagnostics.get('prepared_rows', 0)}:{fetched_at}"


def _existing_columns(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    return [column for column in columns if column in frame.columns]


@st.cache_resource(ttl=1800, show_spinner=False, max_entries=48)
def cached_build_market_view(
    market_code: str,
    fingerprint: str,
    view_mode: str,
    query: str,
    engine_strategy: str,
    root_blend: float,
    custom_weight_items: tuple[tuple[str, float], ...],
    profile: str,
    capability_items: tuple[tuple[str, bool], ...],
    fx_items: tuple[tuple[str, float], ...],
    fx_reference_date: str,
    fx_source: str,
    _data: pd.DataFrame,
) -> pd.DataFrame:
    del market_code, fingerprint
    market_scored = apply_strategy_score(
        _data,
        engine_strategy,
        root_blend=root_blend,
        custom_weights=dict(custom_weight_items) or None,
    )
    decision = apply_decision_model_v32(
        market_scored,
        profile=profile,
        capability_overrides=dict(capability_items),
        fx_rates=dict(fx_items),
        fx_reference_date=fx_reference_date,
        fx_source=fx_source,
    )
    scored = add_actionability_v32(
        add_strategy_robustness(_data, decision, root_blend=root_blend)
    )

    if view_mode == "overview":
        return scored.loc[:, _existing_columns(scored, OVERVIEW_COLUMNS)].copy()
    if view_mode == "cross":
        matched = scored.loc[
            text_match_mask(scored, query) & scored["EligibleCore"].fillna(False)
        ].copy()
        if matched.empty:
            return matched.loc[:, _existing_columns(matched, CROSS_COLUMNS)]
        matched = matched.sort_values(
            ["ConsensusPriorityScore", "StrategyAgreementScore", "DataQualityScore"],
            ascending=False,
        ).head(250)
        return matched.loc[:, _existing_columns(matched, CROSS_COLUMNS)].copy()
    return scored


def profile_label(profile: str) -> str:
    if profile == NEUTRAL_PROFILE:
        return NEUTRAL_PROFILE_LABEL
    return str(PROFILE_DEFAULTS[profile]["label"])


def custom_weights_control(strategy: str) -> Mapping[str, float] | None:
    if strategy != "自定义":
        return None
    defaults = STRATEGY_PRESETS["稳健优先"]
    st.sidebar.caption("自定义权重只改变市场模型，不改变原始数据和规则预警。")
    weights = {
        factor: st.sidebar.slider(
            label,
            0,
            50,
            int(defaults.get(factor, 0) * 100),
            1,
            key=f"responsive_weight_{factor}",
        )
        / 100
        for factor, label in FACTOR_LABELS.items()
    }
    if sum(weights.values()) <= 0:
        st.sidebar.warning("权重不能全部为0，已使用稳健优先。")
        return dict(defaults)
    return weights


def capability_controls(profile: str) -> dict[str, bool]:
    if profile == NEUTRAL_PROFILE:
        with st.sidebar.expander("已有能力与资质", expanded=False):
            st.caption("中性模式不读取公司能力，也不使用历史聊天中的目标品类偏好。")
        return {key: False for key in CAPABILITY_LABELS}

    defaults = PROFILE_CAPABILITY_DEFAULTS[profile]
    values: dict[str, bool] = {}
    with st.sidebar.expander("已有能力与资质", expanded=False):
        st.caption("这些是人工输入，会影响公司适配度，不是市场数据事实。")
        for key, label in CAPABILITY_LABELS.items():
            values[key] = st.checkbox(
                label,
                value=bool(defaults.get(key, False)),
                key=f"responsive_cap_{profile}_{key}",
            )
    return values


def fx_controls() -> tuple[dict[str, float], str, str]:
    reference = DEFAULT_FX_REFERENCE
    with st.sidebar.expander("人民币统一比较汇率", expanded=False):
        st.caption(
            f"默认基准：{reference.reference_date} · {reference.source_name}。仅用于横向比较。"
        )
        jpy_100 = st.number_input(
            "100 JPY = CNY",
            min_value=0.01,
            value=float(reference.cny_per_currency["JPY"] * 100),
            step=0.01,
            format="%.4f",
            key="responsive_fx_jpy",
        )
        usd = st.number_input(
            "1 USD = CNY",
            min_value=0.01,
            value=float(reference.cny_per_currency["USD"]),
            step=0.01,
            format="%.4f",
            key="responsive_fx_usd",
        )
        eur = st.number_input(
            "1 EUR = CNY",
            min_value=0.01,
            value=float(reference.cny_per_currency["EUR"]),
            step=0.01,
            format="%.4f",
            key="responsive_fx_eur",
        )
        gbp = st.number_input(
            "1 GBP = CNY",
            min_value=0.01,
            value=float(reference.cny_per_currency["GBP"]),
            step=0.01,
            format="%.4f",
            key="responsive_fx_gbp",
        )
        st.caption("真实趋势仍使用本位币，避免汇率变化制造假增长。")
    return (
        {"JPY": jpy_100 / 100, "USD": usd, "EUR": eur, "GBP": gbp, "CNY": 1.0},
        reference.reference_date,
        reference.source_name,
    )


def render_hero(
    holder: st.delta_generator.DeltaGenerator,
    *,
    page: str,
    market_code: str,
    strategy: str,
    profile: str,
    candidate_label: str,
    fx_reference_date: str,
) -> None:
    config = MARKETS[market_code]
    holder.markdown(
        f"""
        <section class="hero">
          <div class="hero-kicker">Amazon Multi-Market Category Intelligence</div>
          <h1>全球类目机会、规则预警与稳健性系统</h1>
          <p>页面外壳先显示，再按当前页面加载必要数据。默认只读取一个站点，避免四站计算阻塞整个页面。</p>
          <div class="meta-row">
            <span class="pill">{config.flag} 主站点：{config.name}</span>
            <span class="pill">📄 页面：{page}</span>
            <span class="pill">🧭 当前策略：{strategy}</span>
            <span class="pill">🏢 画像：{profile_label(profile)}</span>
            <span class="pill">📦 {candidate_label}</span>
            <span class="pill">💱 汇率基准：{fx_reference_date}</span>
            <span class="pill">🧪 {APP_VERSION}</span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_cross_market_results(scored: pd.DataFrame, query: str) -> None:
    st.markdown(
        '<div class="notice">跨站点匹配仍然只是名称和关键词候选。人民币解决金额量纲问题，五策略中位分解决单一权重问题，但都不能证明不同站点Browse Node完全等价。</div>',
        unsafe_allow_html=True,
    )
    if scored.empty:
        st.warning("四站均未找到匹配类目，可尝试英文、当地语言或更短关键词。")
        return

    matched = scored.copy()
    matched["匹配置信度"] = matched.apply(lambda row: match_confidence(row, query), axis=1)
    matched = matched.sort_values(
        ["MarketCode", "ConsensusPriorityScore", "StrategyAgreementScore", "DataQualityScore"],
        ascending=[True, False, False, False],
    )
    matched = matched.groupby(
        "MarketCode", as_index=False, group_keys=False, observed=True
    ).head(25)
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
            "ConsensusPriorityScore": st.column_config.ProgressColumn(
                "五策略中位分", min_value=0, max_value=100, format="%.1f"
            ),
            "ConservativePriorityScore": st.column_config.ProgressColumn(
                "保守下限", min_value=0, max_value=100, format="%.1f"
            ),
            "StrategyAgreementScore": st.column_config.ProgressColumn(
                "策略一致度", min_value=0, max_value=100, format="%.1f"
            ),
            "StrategySupportCount": st.column_config.NumberColumn("Top20%支持数", format="%d"),
            "OpportunityScore": st.column_config.ProgressColumn(
                "当前市场机会分", min_value=0, max_value=100, format="%.1f"
            ),
            "CNYRevenue": st.column_config.NumberColumn("人民币销售额", format="CN¥%.0f"),
            "CNYASP": st.column_config.NumberColumn("人民币均价", format="CN¥%.2f"),
            "CNYRevenuePerASIN": st.column_config.NumberColumn(
                "人民币单ASIN", format="CN¥%.0f"
            ),
            "ASINCount": st.column_config.NumberColumn("ASIN数", format="%.0f"),
            "RuleVerificationStatus": st.column_config.TextColumn(
                "规则核验状态", width="large"
            ),
            "DataQualityScore": st.column_config.ProgressColumn(
                "数据置信度", min_value=0, max_value=100, format="%.0f"
            ),
            "Link": st.column_config.LinkColumn("Amazon", display_text="打开 ↗"),
        },
    )


with st.sidebar:
    st.markdown("## 🌍 全球类目情报")
    st.caption(f"{APP_VERSION} · 首屏优先")
    page = st.radio("功能页面", PAGE_OPTIONS, index=0, key="responsive_page")
    st.divider()
    market_code = st.selectbox(
        "主分析站点",
        list(MARKETS),
        format_func=lambda code: f"{MARKETS[code].flag} {MARKETS[code].name}",
        key="responsive_market",
    )
    strategy = st.selectbox(
        "当前市场机会策略",
        list(STRATEGY_PRESETS) + ["自定义"],
        key="responsive_strategy",
    )
    weights = custom_weights_control(strategy)
    engine_strategy = strategy if strategy != "自定义" else "稳健优先"
    root_blend = st.slider(
        "同大类内部比较权重",
        0,
        60,
        25,
        5,
        help="只改变同大类相对比较的影响。",
        key="responsive_root_blend",
    ) / 100
    st.divider()
    profiles = [NEUTRAL_PROFILE] + list(PROFILE_DEFAULTS)
    profile = st.selectbox(
        "公司画像影响",
        profiles,
        index=0,
        format_func=profile_label,
        key="responsive_profile",
    )
    if profile != NEUTRAL_PROFILE:
        st.warning("已启用人工公司画像，结果会受到人工设定影响。")

capabilities = capability_controls(profile)
fx_rates, fx_reference_date, fx_source = fx_controls()

cross_query = ""
if page == CROSS_MARKET_PAGE:
    with st.sidebar:
        cross_query = st.text_input(
            "跨站点搜索词",
            placeholder="例如 handheld fan、剃须刀、storage box",
            key="responsive_cross_query",
        )

with st.sidebar:
    st.divider()
    if st.button("↻ 清缓存并重新加载", use_container_width=True, key="responsive_refresh"):
        cached_load_market.clear()
        cached_load_all.clear()
        cached_build_market_view.clear()
        st.rerun()

hero_holder = st.empty()
render_hero(
    hero_holder,
    page=page,
    market_code=market_code,
    strategy=strategy,
    profile=profile,
    candidate_label="等待数据",
    fx_reference_date=fx_reference_date,
)

if page == CROSS_MARKET_PAGE and not cross_query.strip():
    st.info("先在左侧输入搜索词。未输入前不会读取四站数据，因此页面可以立即打开。")
    st.stop()

load_errors: dict[str, str] = {}
diagnostics: dict[str, dict[str, object]] = {}
status_label = (
    "正在读取四站数据并逐站计算……"
    if page in {GLOBAL_OVERVIEW_PAGE, CROSS_MARKET_PAGE}
    else f"正在读取并计算{MARKETS[market_code].name}……"
)
load_status = st.status(status_label, expanded=False)

try:
    if page in {GLOBAL_OVERVIEW_PAGE, CROSS_MARKET_PAGE}:
        base_data, diagnostics, load_errors = cached_load_all()
        if base_data.empty:
            raise RuntimeError("四个站点均未成功载入。")
        view_mode = "overview" if page == GLOBAL_OVERVIEW_PAGE else "cross"
        parts: list[pd.DataFrame] = []
        for code in MARKETS:
            market_base = base_data.loc[base_data["MarketCode"].eq(code)]
            if market_base.empty or code not in diagnostics:
                continue
            load_status.update(label=f"正在计算{MARKETS[code].name}……")
            parts.append(
                cached_build_market_view(
                    code,
                    _fingerprint(code, diagnostics[code]),
                    view_mode,
                    cross_query,
                    engine_strategy,
                    root_blend,
                    tuple(sorted((weights or {}).items())),
                    profile,
                    tuple(sorted(capabilities.items())),
                    tuple(sorted(fx_rates.items())),
                    fx_reference_date,
                    fx_source,
                    market_base,
                )
            )
        scored = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    else:
        base_data, market_diagnostics = cached_load_market(market_code)
        diagnostics = {market_code: market_diagnostics}
        load_status.update(label=f"正在计算{MARKETS[market_code].name}五策略稳健性……")
        scored = cached_build_market_view(
            market_code,
            _fingerprint(market_code, market_diagnostics),
            "local",
            "",
            engine_strategy,
            root_blend,
            tuple(sorted((weights or {}).items())),
            profile,
            tuple(sorted(capabilities.items())),
            tuple(sorted(fx_rates.items())),
            fx_reference_date,
            fx_source,
            base_data,
        )
except Exception as exc:
    load_status.update(label="加载失败", state="error")
    st.error(f"数据加载或计算失败：{exc}")
    st.caption("可点击左侧“清缓存并重新加载”；若仍失败，需要检查Streamlit日志中的内存或网络错误。")
    st.stop()

load_status.update(label="数据已就绪", state="complete")

if scored.empty and page != CROSS_MARKET_PAGE:
    st.warning("当前页面没有可用记录。")
    st.stop()

if load_errors:
    st.warning("部分站点读取失败：" + "、".join(MARKETS[code].name for code in load_errors))

if page == GLOBAL_OVERVIEW_PAGE:
    candidate_count = int(scored.get("DefaultBusinessEligible", pd.Series(dtype=bool)).sum())
    render_hero(
        hero_holder,
        page=page,
        market_code=market_code,
        strategy=strategy,
        profile=profile,
        candidate_label=f"四站候选：{candidate_count:,}",
        fx_reference_date=fx_reference_date,
    )
    render_overview_v32(scored)
    st.stop()

if page == CROSS_MARKET_PAGE:
    render_hero(
        hero_holder,
        page=page,
        market_code=market_code,
        strategy=strategy,
        profile=profile,
        candidate_label=f"匹配记录：{len(scored):,}",
        fx_reference_date=fx_reference_date,
    )
    render_cross_market_results(scored, cross_query)
    st.stop()

with st.sidebar:
    st.divider()
    ranking_mode = st.selectbox(
        "主榜排序逻辑",
        ["当前策略最终分", "五策略中位分", "五策略保守下限"],
        index=1,
        help="默认使用五策略中位分，降低单一权重影响。",
        key="responsive_ranking_mode",
    )
    rank_column = {
        "当前策略最终分": "FinalPriorityScore",
        "五策略中位分": "ConsensusPriorityScore",
        "五策略保守下限": "ConservativePriorityScore",
    }[ranking_mode]
    query = st.text_input(
        "搜索类目 / 关键词",
        placeholder="例如 fan、收纳、rasierer",
        key="responsive_query",
    )
    raw_market = scored.loc[scored["MarketCode"].eq(market_code)]
    roots = sorted(raw_market["RootStandard"].dropna().astype(str).unique())
    selected_roots = st.multiselect(
        "标准大类目",
        roots,
        default=roots,
        key="responsive_roots",
    )
    selected_entry_classes = st.multiselect(
        "主榜规则等级",
        ["A", "B", "C", "D"],
        default=["A", "B"],
        help="A/B只是内部规则预警等级，不代表已完成合规确认。",
        key="responsive_entry_classes",
    )
    only_physical = st.toggle(
        "排除数字商品高风险节点", True, key="responsive_only_physical"
    )
    exclude_broad_nodes = st.toggle(
        "排除名称过宽节点",
        True,
        help="隐藏Systems、Strips、Powders等难以直接定义产品的聚合名称。",
        key="responsive_exclude_broad",
    )
    min_confidence = st.slider(
        "最低数据置信度", 0, 100, 50, 5, key="responsive_min_confidence"
    )
    min_evidence = st.slider(
        "最低证据字段覆盖", 0, 100, 0, 5, key="responsive_min_evidence"
    )
    min_rank_score = st.slider(
        "最低排序分", 0, 100, 0, 1, key="responsive_min_rank"
    )
    min_strategy_support = st.slider(
        "至少进入多少套策略的Top20%",
        0,
        5,
        0,
        1,
        key="responsive_min_support",
    )
    positive_asin = raw_market.loc[raw_market["ASINCount"].gt(0), "ASINCount"]
    max_asin = max(1, int(positive_asin.max())) if not positive_asin.empty else 1
    asin_cap = st.number_input(
        "最多ASIN数量",
        1,
        max_asin,
        max_asin,
        max(1, max_asin // 100),
        key="responsive_asin_cap",
    )
    positive_asp = raw_market.loc[raw_market["ASP"].gt(0), "ASP"]
    max_asp = max(1, int(positive_asp.max())) if not positive_asp.empty else 1
    min_asp = st.number_input(
        f"最低平均价格（{MARKETS[market_code].currency_symbol}）",
        0,
        max_asp,
        0,
        max(1, max_asp // 100),
        key="responsive_min_asp",
    )

market_df = scored.loc[scored["MarketCode"].eq(market_code)].copy()
mask = market_df["EligibleCore"].fillna(False).astype(bool)
mask &= market_df["RootStandard"].isin(selected_roots) if selected_roots else False
mask &= market_df["EntryClass"].isin(selected_entry_classes) if selected_entry_classes else False
if only_physical:
    mask &= market_df["DigitalRisk"].ne("高")
if exclude_broad_nodes:
    mask &= ~market_df["BroadNodeWarning"].fillna(False)
mask &= market_df["DataQualityScore"].ge(min_confidence)
mask &= market_df["EvidenceCoverageScore"].ge(min_evidence)
mask &= market_df[rank_column].ge(min_rank_score)
mask &= market_df["StrategySupportCount"].ge(min_strategy_support)
mask &= market_df["ASINCount"].le(float(asin_cap))
mask &= market_df["ASP"].ge(float(min_asp))
mask &= text_match_mask(market_df, query)
filtered = market_df.loc[mask.fillna(False)].copy()

render_hero(
    hero_holder,
    page=page,
    market_code=market_code,
    strategy=strategy,
    profile=profile,
    candidate_label=f"当前候选：{len(filtered):,}",
    fx_reference_date=fx_reference_date,
)

if filtered.empty and page in {"🏆 候选排行榜", "🧭 多维矩阵"}:
    st.warning("当前筛选没有候选，请降低门槛或扩大范围。")

search_mask = text_match_mask(market_df, query)
diagnosis_pool = market_df.loc[
    market_df["EligibleCore"].fillna(False) & search_mask
].copy()

if page == "🏆 候选排行榜":
    render_opportunities_v32(filtered, market_code, strategy, rank_column=rank_column)
elif page == "🧪 策略稳健性":
    render_robustness_v32(scored, market_code)
elif page == "🧭 多维矩阵":
    render_matrix_v32(filtered)
elif page == "🔬 单类目诊断":
    render_diagnosis_v32(diagnosis_pool if not diagnosis_pool.empty else market_df, market_code)
elif page == "🚧 规则预警研究":
    render_entry_research_v32(scored, market_code)
elif page == "📈 趋势中心":
    render_trends(scored)
else:
    render_quality(
        scored,
        diagnostics,
        load_errors,
        market_code,
        weights or STRATEGY_PRESETS[engine_strategy],
    )
