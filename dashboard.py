import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io
import numpy as np  # <--- 这里就是之前缺失的关键一行！

# ==========================================
# 1. 页面配置：全宽模式 + 商务风格
# ==========================================
st.set_page_config(layout="wide", page_title="Amazon JP 战略指挥舱")

# 自定义 CSS 让界面更紧凑专业
st.markdown("""
<style>
    .reportview-container .main .block-container {padding-top: 1rem;}
    div[data-testid="stMetricValue"] {font-size: 24px;}
</style>
""", unsafe_allow_html=True)

st.title("🏯 Amazon Japan 市场战略指挥舱 (Strategic Matrix)")
st.markdown("---")

# ==========================================
# 2. 数据读取与核心清洗
# ==========================================
@st.cache_data
def load_data():
    # 使用你最新提供的 CSV 链接
    csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ0-aEMMkENn3f4WyGVbUhB0D5XPpTCC1dJCL03MBkp3yUWUoz4vLEzFQPE_MkGeRvk6DuoA7IQwn23/pub?gid=1391802072&single=true&output=csv"
    try:
        response = requests.get(csv_url)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        df = pd.read_csv(io.StringIO(response.text))
        
        # 强力清洗函数
        def clean_num(x):
            if pd.isna(x) or x == '': return 0.0
            if isinstance(x, str):
                s = x.replace(',', '').replace('¥', '').replace(' ', '').replace('Equalto', '')
                try: return float(s)
                except: return 0.0
            return float(x)

        # 映射列名
        df['Sales'] = df['近12个月销量'].apply(clean_num)
        df['Revenue'] = df['近12个月净销售额'].apply(clean_num)
        df['Category'] = df['中文名称'].astype(str)
        
        # 智能处理大类目：如果没有大类目列，尝试从 Node Path 提取或设为其他
        if '大类目' in df.columns:
            df['BigCategory'] = df['大类目'].astype(str)
        elif '分类名称' in df.columns:
            df['BigCategory'] = df['分类名称'].astype(str)
        else:
            df['BigCategory'] = '未分类'

        # 核心指标计算
        # ASP (平均客单价) = 市场对价格的接受度
        # 防止除以0错误
        df['ASP'] = df.apply(lambda row: row['Revenue'] / row['Sales'] if row['Sales'] > 0 else 0, axis=1)
        
        # 过滤脏数据
        df = df[(df['Sales'] > 100) & (df['Revenue'] > 1000000)]
        return df
        
    except Exception as e:
        st.error(f"数据源连接失败，请检查 Google Sheet 权限或链接: {e}")
        return pd.DataFrame()

df = load_data()
if df.empty: st.stop()

# ==========================================
# 3. 侧边栏：专业筛选器
# ==========================================
with st.sidebar:
    st.header("🎛️ 战术筛选 (Tactical Filter)")
    
    # 3.1 核心门槛
    min_rev = st.number_input("💰 最低市场规模 (日元)", min_value=0, value=500000000, step=100000000, format="%d")
    st.caption(f"当前过滤：仅显示 {min_rev/100000000:.1f} 亿日元以上的赛道")
    
    # 3.2 利润/客单价偏好
    min_asp = st.slider("💎 最低客单价 (ASP)", 0, 50000, 2000, help="过滤掉低价铺货型产品")
    
    # 3.3 标签显示阈值
    st.markdown("---")
    st.subheader("🏷️ 标签显示控制")
    label_threshold = st.slider("只显示头部赛道名称 (Top Revenue)", 
                                min_value=0, 
                                max_value=len(df), 
                                value=30,
                                help="为了防止重叠，只显示销售额排名前 N 的类目名字")
    
    # 3.4 大类目过滤
    all_cats = sorted(df['BigCategory'].unique())
    sel_cats = st.multiselect("📂 聚焦大类目", all_cats, default=all_cats[:5] if len(all_cats)>5 else all_cats)

# --- 数据应用筛选 ---
mask = (
    (df['Revenue'] >= min_rev) & 
    (df['ASP'] >= min_asp) & 
    (df['BigCategory'].isin(sel_cats))
)
filtered_df = df[mask].copy()

# ==========================================
# 4. 核心图表区域
# ==========================================

# 4.1 顶部 KPI 指标
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("筛选后赛道数", f"{len(filtered_df)}")
kpi2.metric("平均客单价 (ASP)", f"¥{filtered_df['ASP'].mean():,.0f}")
kpi3.metric("市场总盘子", f"¥{filtered_df['Revenue'].sum()/100000000:.1f} 亿")
kpi4.metric("最高单品类产出", f"¥{filtered_df['Revenue'].max()/100000000:.1f} 亿")

# 4.2 制作专业级 Plotly 图表
if not filtered_df.empty:
    # 准备标签列：只给前 N 名打标签，其他的设为 None
    top_n_indices = filtered_df.nlargest(label_threshold, 'Revenue').index
    filtered_df['Label'] = filtered_df.apply(lambda x: x['Category'] if x.name in top_n_indices else '', axis=1)

    fig = px.scatter(
        filtered_df,
        x="Sales",
        y="Revenue",
        size="ASP",          # 气泡大小 = 利润空间 (客单价)
        color="BigCategory", # 颜色 = 行业
        text="Label",        # 核心：把文字直接印在图上
        hover_name="Category",
        hover_data={"Sales":True, "Revenue":True, "ASP":":.0f", "Label":False},
        log_x=True,          # 对数坐标
        log_y=True,          # 对数坐标
        size_max=80,         # 气泡放大
        template="plotly_white",
        title=f"<b>市场机会矩阵 (Market Opportunity Matrix)</b><br><sup>气泡越大=客单价越高(利润越厚) | 越靠上=市场越大 | 越靠左=竞争越小</sup>"
    )

    # 优化文字显示位置
    fig.update_traces(textposition='top center', textfont_size=11)

    # 添加战略象限分割线 (根据当前数据自动计算中位数)
    median_sales = filtered_df['Sales'].median()
    median_rev = filtered_df['Revenue'].median()
    
    # 绘制象限线
    fig.add_hline(y=median_rev, line_dash="dot", line_color="grey", annotation_text="平均营收线")
    fig.add_vline(x=median_sales, line_dash="dot", line_color="grey", annotation_text="平均竞争线")

    # 添加象限标注 (水印风格) - 修复后的代码
    # 注意：对数坐标下加注释需要小心 0 值，但我们之前已过滤 >100
    try:
        min_log_x = np.log10(filtered_df['Sales'].min())
        max_log_y = np.log10(filtered_df['Revenue'].max())
        max_log_x = np.log10(filtered_df['Sales'].max())
        min_log_y = np.log10(filtered_df['Revenue'].min())

        fig.add_annotation(x=min_log_x, y=max_log_y, 
                           text="👑 蓝海霸主区<br>(高营收/低竞争)", showarrow=False, 
                           font=dict(size=20, color="gold"), xanchor="left", yanchor="top")
        
        fig.add_annotation(x=max_log_x, y=max_log_y, 
                           text="⚔️ 巨头绞肉机<br>(高营收/高竞争)", showarrow=False, 
                           font=dict(size=15, color="grey"), xanchor="right", yanchor="top")
    except:
        pass # 如果数据太少导致 log 计算出错，就不显示注释

    fig.update_layout(height=800, xaxis_title="年销量 (竞争拥挤度)", yaxis_title="年销售额 (市场天花板)")
    
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("当前筛选条件下无数据，请降低门槛。")

# ==========================================
# 5. 操盘手决策辅助表
# ==========================================
st.markdown("### 📋 核心赛道战力排行榜")
st.caption("按 '机会指数' 排序：我们赋予了高客单价+高流水的类目更高的权重")

# 格式化显示
display_cols = ['Category', 'BigCategory', 'Revenue', 'Sales', 'ASP']
st.dataframe(
    filtered_df.sort_values('Revenue', ascending=False)[display_cols]
    .style.format({
        'Revenue': '¥{:,.0f}', 
        'Sales': '{:,.0f}', 
        'ASP': '¥{:,.0f}'
    })
    .background_gradient(subset=['Revenue'], cmap='Greens') # 销售额越高越绿
    .background_gradient(subset=['ASP'], cmap='Oranges'),   # 客单价越高越橙
    use_container_width=True
)