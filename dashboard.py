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
    apply_business_model,
    enrich_entry_rules,
)
from amz_intelligence.engine import apply_strategy_score, load_all_markets
from amz_intelligence.pages_insight import (
    render_cross_market,
    render_diagnosis,
    render_quality,
    render_trends,
)
from amz_intelligence.pages_market import (
    render_entry_research,
    render_matrix,
    render_opportunities,
    render_overview,
)
from amz_intelligence.ui_common import apply_visual_system, text_match_mask

APP_VERSION = "2026.07.29-v3.1-beta"

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


def custom_weights(strategy: str) -> Mapping[str, float] | None:
    if strategy != "自定义":
        return None
    defaults = STRATEGY_PRESETS["稳健优先"]
    st.sidebar.caption("自定义权重会自动归一化。经营准入不在这里，它是机会分之后的门槛。")
    weights = {
        factor: st.sidebar.slider(
            label,
            0,
            50,
            int(defaults.get(factor, 0) * 100),
            1,
            key=f"w_{factor}",
        )
        / 100
        for factor, label in FACTOR_LABELS.items()
    }
    if sum(weights.values()) <= 0:
        st.sidebar.warning("权重不能全部为0，已使用稳健优先。")
        return dict(defaults)
    return weights


def capability_controls(profile: str) -> dict[str, bool]:
    defaults = PROFILE_CAPABILITY_DEFAULTS[profile]
    values: dict[str, bool] = {}
    with st.sidebar.expander("已有能力与资质", expanded=False):
        st.caption("勾选只代表你声明具备该能力；高监管类目最多降低一个准入等级，仍需人工和专业机构复核。")
        for key, label in CAPABILITY_LABELS.items():
            values[key] = st.checkbox(
                label,
                value=bool(defaults.get(key, False)),
                key=f"cap_{profile}_{key}",
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
        )
        usd = st.number_input(
            "1 USD = CNY",
            min_value=0.01,
            value=float(reference.cny_per_currency["USD"]),
            step=0.01,
            format="%.4f",
        )
        eur = st.number_input(
            "1 EUR = CNY",
            min_value=0.01,
            value=float(reference.cny_per_currency["EUR"]),
            step=0.01,
            format="%.4f",
        )
        gbp = st.number_input(
            "1 GBP = CNY",
            min_value=0.01,
            value=float(reference.cny_per_currency["GBP"]),
            step=0.01,
            format="%.4f",
        )
        st.caption("趋势分析仍使用本位币，避免汇率变化制造假增长。")
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
    st.caption(f"{APP_VERSION} · 经营准入 + 人民币比较")
    market_code = st.selectbox(
        "主分析站点",
        list(MARKETS),
        format_func=lambda code: f"{MARKETS[code].flag} {MARKETS[code].name}",
    )
    strategy = st.selectbox("市场机会策略", list(STRATEGY_PRESETS) + ["自定义"])
    weights = custom_weights(strategy)
    engine_strategy = strategy if strategy != "自定义" else "稳健优先"
    root_blend = st.slider(
        "同大类内部比较权重",
        0,
        60,
        25,
        5,
        help="提高后，更容易发现大类目内部的小众机会，而不是只看到巨型类目。",
    ) / 100
    st.divider()
    profile = st.selectbox(
        "经营者画像",
        list(PROFILE_DEFAULTS),
        index=list(PROFILE_DEFAULTS).index("当前公司画像"),
        format_func=lambda key: str(PROFILE_DEFAULTS[key]["label"]),
    )

capabilities = capability_controls(profile)
fx_rates, fx_reference_date, fx_source = fx_controls()

with st.sidebar:
    st.divider()
    query = st.text_input("搜索类目 / 关键词", placeholder="例如 fan、收纳、rasierer")
    raw_market = all_data.loc[all_data["MarketCode"].eq(market_code)]
    roots = sorted(raw_market["RootStandard"].dropna().astype(str).unique())
    selected_roots = st.multiselect("标准大类目", roots, default=roots)
    selected_entry_classes = st.multiselect(
        "主榜经营准入等级",
        ["A", "B", "C", "D"],
        default=["A", "B"],
        help="C/D 默认只在“准入研究”页查看；主动勾选后也可进入主榜筛选。",
    )
    only_physical = st.toggle("排除数字商品高风险节点", True)
    min_confidence = st.slider("最低数据置信度", 0, 100, 50, 5)
    min_priority = st.slider("最低最终优先级", 0, 100, 0, 1)
    positive_asin = raw_market.loc[raw_market["ASINCount"].gt(0), "ASINCount"]
    max_asin = max(1, int(positive_asin.max())) if not positive_asin.empty else 1
    asin_cap = st.number_input("最多ASIN数量", 1, max_asin, max_asin, max(1, max_asin // 100))
    positive_asp = raw_market.loc[raw_market["ASP"].gt(0), "ASP"]
    max_asp = max(1, int(positive_asp.max())) if not positive_asp.empty else 1
    min_asp = st.number_input(
        f"最低平均价格（{MARKETS[market_code].currency_symbol}）",
        0,
        max_asp,
        0,
        max(1, max_asp // 100),
    )
    st.divider()
    if st.button("↻ 强制刷新四站数据", use_container_width=True):
        cached_load_all.clear()
        st.rerun()

market_scored = apply_strategy_score(
    all_data,
    engine_strategy,
    root_blend=root_blend,
    custom_weights=weights,
)
scored = apply_business_model(
    market_scored,
    profile=profile,
    capability_overrides=capabilities,
    fx_rates=fx_rates,
    fx_reference_date=fx_reference_date,
    fx_source=fx_source,
)
market_df = scored.loc[scored["MarketCode"].eq(market_code)].copy()
mask = market_df["EligibleCore"].fillna(False).astype(bool)
mask &= market_df["RootStandard"].isin(selected_roots) if selected_roots else False
mask &= market_df["EntryClass"].isin(selected_entry_classes) if selected_entry_classes else False
if only_physical:
    mask &= market_df["DigitalRisk"].ne("高")
mask &= market_df["DataQualityScore"].ge(min_confidence)
mask &= market_df["FinalPriorityScore"].ge(min_priority)
mask &= market_df["ASINCount"].le(float(asin_cap))
mask &= market_df["ASP"].ge(float(min_asp))
mask &= text_match_mask(market_df, query)
filtered = market_df.loc[mask.fillna(False)].copy()
config = MARKETS[market_code]

st.markdown(
    f"""
    <section class="hero">
      <div class="hero-kicker">Amazon Multi-Market Category Intelligence</div>
      <h1>全球类目机会与经营准入系统</h1>
      <p>先判断市场是否有吸引力，再判断普通跨境卖家能不能做、我们适不适合做。保留本位币理解当地市场，并用人民币建立跨站统一比较层。</p>
      <div class="meta-row">
        <span class="pill">{config.flag} 主站点：{config.name}</span>
        <span class="pill">🧭 市场策略：{strategy}</span>
        <span class="pill">🏢 画像：{PROFILE_DEFAULTS[profile]['label']}</span>
        <span class="pill">🚪 主榜准入：{' / '.join(selected_entry_classes) or '无'}</span>
        <span class="pill">📦 当前候选：{len(filtered):,}</span>
        <span class="pill">💱 汇率基准：{fx_reference_date}</span>
        <span class="pill">🧪 {APP_VERSION}</span>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)
if load_errors:
    st.warning("部分站点读取失败：" + "、".join(MARKETS[c].name for c in load_errors))
if filtered.empty:
    st.warning("当前筛选没有候选，请降低门槛、扩大大类目范围或在主榜准入等级中加入C/D。")

search_mask = text_match_mask(market_df, query)
diagnosis_pool = market_df.loc[market_df["EligibleCore"].fillna(False) & search_mask].copy()

tabs = st.tabs(
    [
        "🌐 全球总览",
        "🏆 可经营机会",
        "🧭 多维矩阵",
        "🔀 跨站点比较",
        "🔬 单类目诊断",
        "🚧 准入研究",
        "📈 趋势中心",
        "🧪 数据质量",
    ]
)
with tabs[0]:
    render_overview(scored)
with tabs[1]:
    render_opportunities(filtered, market_code, strategy)
with tabs[2]:
    render_matrix(filtered)
with tabs[3]:
    render_cross_market(scored, query)
with tabs[4]:
    render_diagnosis(diagnosis_pool if not diagnosis_pool.empty else market_df, market_code)
with tabs[5]:
    render_entry_research(scored, market_code)
with tabs[6]:
    render_trends(scored)
with tabs[7]:
    render_quality(
        scored,
        diagnostics,
        load_errors,
        market_code,
        weights or STRATEGY_PRESETS[engine_strategy],
    )
