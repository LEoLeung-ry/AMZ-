import io

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# ==========================================
# 1. 页面配置：全宽模式 + 商务风格
# ==========================================
st.set_page_config(
    layout="wide",
    page_title="Amazon JP 战略指挥舱",
    page_icon="🏯",
)

st.markdown(
    """
    <style>
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
        }
        div[data-testid="stMetricValue"] {
            font-size: 24px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏯 Amazon Japan 市场战略指挥舱 (Strategic Matrix)")
st.markdown("---")


# ==========================================
# 2. 数据读取与核心清洗
# ==========================================
@st.cache_data(ttl=1800, show_spinner="正在读取市场数据……")
def load_data() -> pd.DataFrame:
    csv_url = (
        "https://docs.google.com/spreadsheets/d/e/"
        "2PACX-1vQ0-aEMMkENn3f4WyGVbUhB0D5XPpTCC1dJCL03MBkp3yUWUoz4vLEzFQPE_"
        "MkGeRvk6DuoA7IQwn23/pub?gid=1391802072&single=true&output=csv"
    )

    response = requests.get(csv_url, timeout=(10, 30))
    response.raise_for_status()
    response.encoding = "utf-8"

    df = pd.read_csv(io.StringIO(response.text))

    required_columns = {"近12个月销量", "近12个月净销售额", "中文名称"}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        raise ValueError(
            "数据源缺少必要字段：" + "、".join(sorted(missing_columns))
        )

    def clean_num(value) -> float:
        if pd.isna(value) or value == "":
            return 0.0
        if isinstance(value, str):
            normalized = (
                value.replace(",", "")
                .replace("¥", "")
                .replace(" ", "")
                .replace("Equalto", "")
            )
            try:
                return float(normalized)
            except ValueError:
                return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    df["Sales"] = df["近12个月销量"].map(clean_num)
    df["Revenue"] = df["近12个月净销售额"].map(clean_num)
    df["Category"] = df["中文名称"].fillna("未命名类目").astype(str)

    if "大类目" in df.columns:
        df["BigCategory"] = df["大类目"].fillna("未分类").astype(str)
    elif "分类名称" in df.columns:
        df["BigCategory"] = df["分类名称"].fillna("未分类").astype(str)
    else:
        df["BigCategory"] = "未分类"

    # ASP（平均售价）= 近 12 个月销售额 / 近 12 个月销量
    # 使用 divide + where，避免空值或除零导致运行错误。
    df["ASP"] = df["Revenue"].div(df["Sales"].where(df["Sales"] > 0))
    df["ASP"] = (
        pd.to_numeric(df["ASP"], errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
    )

    df = df[(df["Sales"] > 100) & (df["Revenue"] > 1_000_000)].copy()
    return df


try:
    df = load_data()
except Exception as exc:
    st.error("数据没有成功载入。请确认 Google Sheet 已发布到网页，并允许公开读取。")
    with st.expander("技术详情"):
        st.exception(exc)
    st.stop()

if df.empty:
    st.warning("数据源已连接，但清洗后没有可展示的数据。")
    st.stop()


# ==========================================
# 3. 侧边栏：筛选器
# ==========================================
with st.sidebar:
    st.header("🎛️ 战术筛选 (Tactical Filter)")

    min_rev = st.number_input(
        "💰 最低市场规模（日元）",
        min_value=0,
        value=500_000_000,
        step=100_000_000,
        format="%d",
    )
    st.caption(f"当前过滤：仅显示 {min_rev / 100_000_000:.1f} 亿日元以上的赛道")

    min_asp = st.slider(
        "💎 最低平均售价（ASP）",
        min_value=0,
        max_value=50_000,
        value=2_000,
        help="过滤平均售价较低的类目。",
    )

    st.markdown("---")
    st.subheader("🏷️ 标签显示控制")

    max_labels = len(df)
    default_labels = min(30, max_labels)
    label_threshold = st.slider(
        "显示销售额前 N 名类目名称",
        min_value=0,
        max_value=max_labels,
        value=default_labels,
        help="减少气泡标签重叠。",
    )

    all_cats = sorted(df["BigCategory"].dropna().unique().tolist())
    default_cats = all_cats[:5] if len(all_cats) > 5 else all_cats
    sel_cats = st.multiselect(
        "📂 聚焦大类目",
        options=all_cats,
        default=default_cats,
    )


mask = (
    (df["Revenue"] >= min_rev)
    & (df["ASP"] >= min_asp)
    & (df["BigCategory"].isin(sel_cats))
)
filtered_df = df.loc[mask].copy()


# ==========================================
# 4. 核心指标和图表
# ==========================================
avg_asp = filtered_df["ASP"].mean() if not filtered_df.empty else 0
total_revenue = filtered_df["Revenue"].sum() if not filtered_df.empty else 0
max_revenue = filtered_df["Revenue"].max() if not filtered_df.empty else 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("筛选后赛道数", f"{len(filtered_df):,}")
kpi2.metric("平均售价（ASP）", f"¥{avg_asp:,.0f}")
kpi3.metric("市场总盘子", f"¥{total_revenue / 100_000_000:.1f} 亿")
kpi4.metric("最高单类目产出", f"¥{max_revenue / 100_000_000:.1f} 亿")

if not filtered_df.empty:
    top_n_indices = filtered_df.nlargest(label_threshold, "Revenue").index
    filtered_df["Label"] = np.where(
        filtered_df.index.isin(top_n_indices),
        filtered_df["Category"],
        "",
    )

    fig = px.scatter(
        filtered_df,
        x="Sales",
        y="Revenue",
        size="ASP",
        color="BigCategory",
        text="Label",
        hover_name="Category",
        hover_data={
            "Sales": ":,.0f",
            "Revenue": ":,.0f",
            "ASP": ":,.0f",
            "Label": False,
        },
        log_x=True,
        log_y=True,
        size_max=80,
        template="plotly_white",
        title=(
            "<b>市场机会矩阵 (Market Opportunity Matrix)</b>"
            "<br><sup>气泡大小代表平均售价；纵轴代表市场规模；横轴代表年销量</sup>"
        ),
    )

    fig.update_traces(textposition="top center", textfont_size=11)

    median_sales = filtered_df["Sales"].median()
    median_revenue = filtered_df["Revenue"].median()
    fig.add_hline(
        y=median_revenue,
        line_dash="dot",
        line_color="grey",
        annotation_text="营收中位线",
    )
    fig.add_vline(
        x=median_sales,
        line_dash="dot",
        line_color="grey",
        annotation_text="销量中位线",
    )

    fig.update_layout(
        height=800,
        xaxis_title="近 12 个月销量",
        yaxis_title="近 12 个月净销售额（日元）",
        legend_title_text="大类目",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("当前筛选条件下无数据，请降低筛选门槛或增加大类目。")


# ==========================================
# 5. 操盘手决策辅助表
# ==========================================
st.markdown("### 📋 核心赛道战力排行榜")
st.caption("按近 12 个月净销售额从高到低排列。")

display_cols = ["Category", "BigCategory", "Revenue", "Sales", "ASP"]
ranking_df = (
    filtered_df.sort_values("Revenue", ascending=False)[display_cols]
    .reset_index(drop=True)
    .copy()
)

# 不使用 Pandas Styler.background_gradient，避免服务器缺少 matplotlib 时崩溃。
ranking_df["Revenue"] = ranking_df["Revenue"].map(lambda value: f"¥{value:,.0f}")
ranking_df["Sales"] = ranking_df["Sales"].map(lambda value: f"{value:,.0f}")
ranking_df["ASP"] = ranking_df["ASP"].map(lambda value: f"¥{value:,.0f}")
ranking_df.rename(
    columns={
        "Category": "类目",
        "BigCategory": "大类目",
        "Revenue": "近12个月净销售额",
        "Sales": "近12个月销量",
        "ASP": "平均售价（ASP）",
    },
    inplace=True,
)

st.dataframe(ranking_df, use_container_width=True)
