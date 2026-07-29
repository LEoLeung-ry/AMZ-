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
from amz_intelligence.engine import apply_strategy_score, load_all_markets
from amz_intelligence.matrix_v32 import render_matrix_v32
from amz_intelligence.model_v32 import (
    NEUTRAL_PROFILE,
    NEUTRAL_PROFILE_LABEL,
    add_strategy_robustness,
    apply_decision_model_v32,
)
from amz_intelligence.pages_insight import render_quality, render_trends
from amz_intelligence.pages_v32 import (
    render_cross_market_v32,
    render_diagnosis_v32,
    render_entry_research_v32,
    render_opportunities_v32,
    render_overview_v32,
    render_robustness_v32,
)
from amz_intelligence.ui_common import apply_visual_system, text_match_mask


APP_VERSION = "2026.07.29-v3.2.1-beta"

st.set_page_config(
    page_title="Amazon 全球类目机会系统",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_visual_system()


@st.cache_data(ttl=1800, show_spinner="正在读取并标准化日本、美国、德国、英国类目数据…")
def cached_load_all():
    data, diagnostics, errors = load_all_markets(tuple(MARKETS))
    if not data.empty:
        data = enrich_entry_rules(data)
    return data, diagnostics, errors


def data_fingerprint(diagnostics: Mapping[str, Mapping[str, object]]) -> str:
    parts: list[str] = []
    for code in sorted(diagnostics):
        diag = diagnostics[code]
        fetch = diag.get("fetch_metadata", {}) if isinstance(diag, Mapping) else {}
        fetched_at = fetch.get("fetched_at", "") if isinstance(fetch, Mapping) else ""
        parts.append(f"{code}:{diag.get('prepared_rows', 0)}:{fetched_at}")
    return "|".join(parts)


@st.cache_data(ttl=1800, show_spinner="正在计算机会分、准入预警和五策略稳健性…")
def cached_build_model(
    fingerprint: str,
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
    del fingerprint  # cache key only
    custom_weights = dict(custom_weight_items) or None
    capabilities = dict(capability_items)
    fx_rates = dict(fx_items)
    market_scored = apply_strategy_score(
        _data,
        engine_strategy,
        root_blend=root_blend,
        custom_weights=custom_weights,
    )
    decision = apply_decision_model_v32(
        market_scored,
        profile=profile,
        capability_overrides=capabilities,
        fx_rates=fx_rates,
        fx_reference_date=fx_reference_date,
        fx_source=fx_source,
    )
    robust = add_strategy_robustness(_data, decision, root_blend=root_blend)
    return add_actionability_v32(robust)


def custom_weights(strategy: str) -> Mapping[str, float] | None:
    if strategy != "自定义":
        return None
    defaults = STRATEGY_PRESETS["稳健优先"]
    st.sidebar.caption("自定义权重只影响市场机会分；准入预警和公司画像属于后置层。")
    weights = {
        factor: st.sidebar.slider(
            label,
            0,
            50,
            int(defaults.get(factor, 0) * 100),
            1,
            key=f"v32_w_{factor}",
        )
        / 100
        for factor, label in FACTOR_LABELS.items()
    }
    if sum(weights.values()) <= 0:
        st.sidebar.warning("权重不能全部为0，已使用稳健优先。")
        return dict(defaults)
    return weights


def profile_label(profile: str) -> str:
    if profile == NEUTRAL_PROFILE:
        return NEUTRAL_PROFILE_LABEL
    return str(PROFILE_DEFAULTS[profile]["label"])


def capability_controls(profile: str) -> dict[str, bool]:
    if profile == NEUTRAL_PROFILE:
        with st.sidebar.expander("已有能力与资质", expanded=False):
            st.caption("中性模式不读取公司能力，也不使用历史聊天中的目标品类加分。")
        return {key: False for key in CAPABILITY_LABELS}

    defaults = PROFILE_CAPABILITY_DEFAULTS[profile]
    values: dict[str, bool] = {}
    with st.sidebar.expander("已有能力与资质", expanded=False):
        st.caption("以下均为人工声明，会影响公司适配度；不是系统从市场数据中推导出的事实。")
        for key, label in CAPABILITY_LABELS.items():
            values[key] = st.checkbox(
                label,
                value=bool(defaults.get(key, False)),
                key=f"v32_cap_{profile}_{key}",
            )
    return values


def fx_controls() -> tuple[dict[str, float], str, str]:
    reference = DEFAULT_FX_REFERENCE
    with st.sidebar.expander("人民币统一比较汇率", expanded=False):
        st.caption(
            f"默认基准：{reference.reference_date} · {reference.source_name}。仅用于横向比较，不替代结算汇率。"
        )
        jpy_100 = st.number_input(
            "100 JPY = CNY",
            min_value=0.01,
            value=float(reference.cny_per_currency["JPY"] * 100),
            step=0.01,
            format="%.4f",
            key="v32_fx_jpy",
        )
        usd = st.number_input(
            "1 USD = CNY",
            min_value=0.01,
            value=float(reference.cny_per_currency["USD"]),
            step=0.01,
            format="%.4f",
            key="v32_fx_usd",
        )
        eur = st.number_input(
            "1 EUR = CNY",
            min_value=0.01,
            value=float(reference.cny_per_currency["EUR"]),
            step=0.01,
            format="%.4f",
            key="v32_fx_eur",
        )
        gbp = st.number_input(
            "1 GBP = CNY",
            min_value=0.01,
            value=float(reference.cny_per_currency["GBP"]),
            step=0.01,
            format="%.4f",
            key="v32_fx_gbp",
        )
        st.caption("真实时间趋势仍使用本位币，避免汇率变化制造假增长。")
    return (
        {"JPY": jpy_100 / 100, "USD": usd, "EUR": eur, "GBP": gbp, "CNY": 1.0},
        reference.reference_date,
        reference.source_name,
    )


all_data, diagnostics, load_errors = cached_load_all()
if all_data.empty:
    st.error("四个站点均未成功载入。")
    for code, error in load_errors.items():
        st.error(f"{MARKETS[code].name}：{error}")
    st.stop()

with st.sidebar:
    st.markdown("## 🌍 全球类目情报")
    st.caption(f"{APP_VERSION} · 中性默认 + 五策略稳健性")
    market_code = st.selectbox(
        "主分析站点",
        list(MARKETS),
        format_func=lambda code: f"{MARKETS[code].flag} {MARKETS[code].name}",
        key="v32_market",
    )
    strategy = st.selectbox(
        "当前市场机会策略",
        list(STRATEGY_PRESETS) + ["自定义"],
        key="v32_strategy",
    )
    weights = custom_weights(strategy)
    engine_strategy = strategy if strategy != "自定义" else "稳健优先"
    root_blend = st.slider(
        "同大类内部比较权重",
        0,
        60,
        25,
        5,
        help="只改变同大类相对比较的影响，不改变原始数据。",
        key="v32_root_blend",
    ) / 100
    st.divider()
    profiles = [NEUTRAL_PROFILE] + list(PROFILE_DEFAULTS)
    profile = st.selectbox(
        "公司画像影响",
        profiles,
        index=0,
        format_func=profile_label,
        key="v32_profile",
    )
    if profile != NEUTRAL_PROFILE:
        st.warning("已启用人工公司画像。排行榜会受到人工设定和历史品类偏好影响。")

capabilities = capability_controls(profile)
fx_rates, fx_reference_date, fx_source = fx_controls()

scored = cached_build_model(
    data_fingerprint(diagnostics),
    engine_strategy,
    root_blend,
    tuple(sorted((weights or {}).items())),
    profile,
    tuple(sorted(capabilities.items())),
    tuple(sorted(fx_rates.items())),
    fx_reference_date,
    fx_source,
    all_data,
)

with st.sidebar:
    st.divider()
    ranking_mode = st.selectbox(
        "主榜排序逻辑",
        ["当前策略最终分", "五策略中位分", "五策略保守下限"],
        index=1,
        help="默认使用五策略中位分，减少单一权重对结果的影响。",
        key="v32_ranking_mode",
    )
    rank_column = {
        "当前策略最终分": "FinalPriorityScore",
        "五策略中位分": "ConsensusPriorityScore",
        "五策略保守下限": "ConservativePriorityScore",
    }[ranking_mode]
    query = st.text_input(
        "搜索类目 / 关键词",
        placeholder="例如 fan、收纳、rasierer",
        key="v32_sidebar_query",
    )
    raw_market = scored.loc[scored["MarketCode"].eq(market_code)]
    roots = sorted(raw_market["RootStandard"].dropna().astype(str).unique())
    selected_roots = st.multiselect(
        "标准大类目",
        roots,
        default=roots,
        key="v32_roots",
    )
    selected_entry_classes = st.multiselect(
        "主榜规则等级",
        ["A", "B", "C", "D"],
        default=["A", "B"],
        help="A/B只是规则层的低风险与条件预警，不代表已完成合规确认。",
        key="v32_entry_classes",
    )
    only_physical = st.toggle("排除数字商品高风险节点", True, key="v32_only_physical")
    exclude_broad_nodes = st.toggle(
        "排除名称过宽节点",
        True,
        help="默认隐藏如 Systems、Strips、Powders 等难以直接定义产品的聚合名称；关闭后仍可研究。",
        key="v32_exclude_broad",
    )
    min_confidence = st.slider("最低数据置信度", 0, 100, 50, 5, key="v32_min_confidence")
    min_evidence = st.slider("最低证据字段覆盖", 0, 100, 0, 5, key="v32_min_evidence")
    min_rank_score = st.slider("最低排序分", 0, 100, 0, 1, key="v32_min_rank")
    min_strategy_support = st.slider(
        "至少进入多少套策略的Top20%",
        0,
        5,
        0,
        1,
        key="v32_min_support",
    )
    positive_asin = raw_market.loc[raw_market["ASINCount"].gt(0), "ASINCount"]
    max_asin = max(1, int(positive_asin.max())) if not positive_asin.empty else 1
    asin_cap = st.number_input(
        "最多ASIN数量",
        1,
        max_asin,
        max_asin,
        max(1, max_asin // 100),
        key="v32_asin_cap",
    )
    positive_asp = raw_market.loc[raw_market["ASP"].gt(0), "ASP"]
    max_asp = max(1, int(positive_asp.max())) if not positive_asp.empty else 1
    min_asp = st.number_input(
        f"最低平均价格（{MARKETS[market_code].currency_symbol}）",
        0,
        max_asp,
        0,
        max(1, max_asp // 100),
        key="v32_min_asp",
    )
    st.divider()
    if st.button("↻ 强制刷新四站数据", use_container_width=True, key="v32_refresh"):
        cached_load_all.clear()
        cached_build_model.clear()
        st.rerun()

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
config = MARKETS[market_code]

st.markdown(
    f"""
    <section class="hero">
      <div class="hero-kicker">Amazon Multi-Market Category Intelligence</div>
      <h1>全球类目机会、规则预警与稳健性系统</h1>
      <p>默认不使用历史品类偏好。市场机会、规则预警、公司画像、类目可操作性和人民币换算分层展示；五套策略共同检验结果是否依赖单一权重。</p>
      <div class="meta-row">
        <span class="pill">{config.flag} 主站点：{config.name}</span>
        <span class="pill">🧭 当前策略：{strategy}</span>
        <span class="pill">🏢 画像：{profile_label(profile)}</span>
        <span class="pill">📊 排序：{ranking_mode}</span>
        <span class="pill">📦 当前候选：{len(filtered):,}</span>
        <span class="pill">💱 汇率基准：{fx_reference_date}</span>
        <span class="pill">🧪 {APP_VERSION}</span>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)
if load_errors:
    st.warning("部分站点读取失败：" + "、".join(MARKETS[code].name for code in load_errors))
if filtered.empty:
    st.warning("当前筛选没有候选，请降低门槛或扩大范围。")

search_mask = text_match_mask(market_df, query)
diagnosis_pool = market_df.loc[market_df["EligibleCore"].fillna(False) & search_mask].copy()

tabs = st.tabs(
    [
        "🌐 全球总览",
        "🏆 候选排行榜",
        "🧪 策略稳健性",
        "🧭 多维矩阵",
        "🔀 跨站点比较",
        "🔬 单类目诊断",
        "🚧 规则预警研究",
        "📈 趋势中心",
        "🧾 数据质量",
    ]
)
with tabs[0]:
    render_overview_v32(scored)
with tabs[1]:
    render_opportunities_v32(filtered, market_code, strategy, rank_column=rank_column)
with tabs[2]:
    render_robustness_v32(scored, market_code)
with tabs[3]:
    render_matrix_v32(filtered)
with tabs[4]:
    render_cross_market_v32(scored, query)
with tabs[5]:
    render_diagnosis_v32(diagnosis_pool if not diagnosis_pool.empty else market_df, market_code)
with tabs[6]:
    render_entry_research_v32(scored, market_code)
with tabs[7]:
    render_trends(scored)
with tabs[8]:
    render_quality(
        scored,
        diagnostics,
        load_errors,
        market_code,
        weights or STRATEGY_PRESETS[engine_strategy],
    )
