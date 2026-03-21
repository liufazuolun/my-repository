import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime, timedelta, date
import random
import io
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 常量定义
# ============================================================
DATA_FILE = "finance_data.json"
SETTINGS_FILE = "finance_settings.json"

INCOME_CATEGORIES = ["生活费/家庭", "兼职收入", "奖学金", "其他收入"]
EXPENSE_CATEGORIES = ["餐饮", "学习/书籍", "娱乐", "交通", "购物/服装", "医疗", "日用品", "社交", "其他支出"]
ALL_CATEGORIES = INCOME_CATEGORIES + EXPENSE_CATEGORIES

PAYMENT_METHODS = ["微信支付", "支付宝", "现金", "银行卡", "学生卡"]

# 推荐各类别支出占比（基于大学生消费研究）
RECOMMENDED_RATIOS = {
    "餐饮": (35, 45),
    "学习/书籍": (10, 20),
    "娱乐": (5, 15),
    "交通": (5, 10),
    "购物/服装": (5, 15),
    "医疗": (2, 8),
    "日用品": (5, 10),
    "社交": (5, 10),
    "其他支出": (0, 10),
}

THEMES = {
    "极光紫": {
        "primary": "#7C3AED",
        "secondary": "#A78BFA",
        "accent": "#F59E0B",
        "bg": "#0F0A1E",
        "card": "#1E1535",
        "text": "#F3F0FF",
        "income": "#10B981",
        "expense": "#EF4444",
        "mode": "dark"
    },
    "珊瑚橙": {
        "primary": "#EA580C",
        "secondary": "#FB923C",
        "accent": "#0EA5E9",
        "bg": "#1C0F0A",
        "card": "#2D1A10",
        "text": "#FFF7F0",
        "income": "#22C55E",
        "expense": "#F43F5E",
        "mode": "dark"
    },
    "海洋蓝": {
        "primary": "#0369A1",
        "secondary": "#38BDF8",
        "accent": "#F97316",
        "bg": "#F0F9FF",
        "card": "#FFFFFF",
        "text": "#0C4A6E",
        "income": "#059669",
        "expense": "#DC2626",
        "mode": "light"
    },
    "抹茶绿": {
        "primary": "#15803D",
        "secondary": "#4ADE80",
        "accent": "#A21CAF",
        "bg": "#F0FDF4",
        "card": "#FFFFFF",
        "text": "#14532D",
        "income": "#16A34A",
        "expense": "#B91C1C",
        "mode": "light"
    },
    "樱花粉": {
        "primary": "#BE185D",
        "secondary": "#F472B6",
        "accent": "#7C3AED",
        "bg": "#FDF2F8",
        "card": "#FFFFFF",
        "text": "#831843",
        "income": "#0D9488",
        "expense": "#E11D48",
        "mode": "light"
    },
    "深夜黑": {
        "primary": "#E2E8F0",
        "secondary": "#94A3B8",
        "accent": "#F59E0B",
        "bg": "#0D1117",
        "card": "#161B22",
        "text": "#E6EDF3",
        "income": "#3FB950",
        "expense": "#F85149",
        "mode": "dark"
    },
}

# ============================================================
# 数据持久化
# ============================================================
def load_data():
    """从JSON文件加载财务数据"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)
            df = pd.DataFrame(records)
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"])
            return df
        except Exception as e:
            st.error(f"数据加载失败: {e}")
    return pd.DataFrame(columns=["id", "type", "category", "amount", "date", "note", "payment_method"])


def save_data(df):
    """将财务数据保存到JSON文件"""
    try:
        records = df.copy()
        if not records.empty:
            records["date"] = records["date"].dt.strftime("%Y-%m-%d")
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(records.to_dict("records"), f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"数据保存失败: {e}")
        return False


def load_settings():
    """加载个性化设置"""
    default = {
        "theme": "极光紫",
        "layout": "宽松",
        "default_period": "月",
        "sort_order": "日期降序",
        "monthly_budget": 2000.0,
        "show_modules": {
            "summary": True,
            "charts": True,
            "advice": True,
            "records": True
        },
        "chart_style": "圆角",
        "budgets": {c: 0.0 for c in EXPENSE_CATEGORIES}
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            default.update(saved)
        except:
            pass
    return default


def save_settings(settings):
    """保存个性化设置"""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"设置保存失败: {e}")


# ============================================================
# 示例数据生成
# ============================================================
def generate_sample_data():
    """生成3个月的示例财务数据"""
    random.seed(42)
    records = []
    today = datetime.now()

    for i in range(90):
        day = today - timedelta(days=i)

        # 每月固定生活费
        if day.day == 1:
            records.append({
                "id": f"s{i}_1",
                "type": "收入",
                "category": "生活费/家庭",
                "amount": round(random.uniform(1500, 2000), 2),
                "date": day.strftime("%Y-%m-%d"),
                "note": "月度生活费",
                "payment_method": "银行卡"
            })

        # 随机支出（每天0-3笔）
        num_expenses = random.randint(0, 3)
        for j in range(num_expenses):
            cat = random.choice(EXPENSE_CATEGORIES)
            amount_range = {
                "餐饮": (8, 60),
                "学习/书籍": (20, 200),
                "娱乐": (10, 150),
                "交通": (2, 50),
                "购物/服装": (30, 300),
                "医疗": (10, 100),
                "日用品": (5, 80),
                "社交": (20, 200),
                "其他支出": (5, 100)
            }
            lo, hi = amount_range.get(cat, (10, 100))
            records.append({
                "id": f"s{i}_{j}",
                "type": "支出",
                "category": cat,
                "amount": round(random.uniform(lo, hi), 2),
                "date": day.strftime("%Y-%m-%d"),
                "note": "",
                "payment_method": random.choice(PAYMENT_METHODS)
            })

        # 偶尔有兼职收入
        if random.random() < 0.05:
            records.append({
                "id": f"s{i}_pt",
                "type": "收入",
                "category": "兼职收入",
                "amount": round(random.uniform(50, 500), 2),
                "date": day.strftime("%Y-%m-%d"),
                "note": "兼职收入",
                "payment_method": "微信支付"
            })

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    return df


# ============================================================
# CSS 主题注入
# ============================================================
def inject_css(theme_name, settings):
    t = THEMES.get(theme_name, THEMES["极光紫"])
    layout_padding = "1rem" if settings["layout"] == "紧凑" else "2rem"

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&family=Space+Grotesk:wght@400;600;700&display=swap');

    /* ===== 全局重置 ===== */
    .stApp {{
        background: {t['bg']};
        color: {t['text']};
        font-family: 'Noto Sans SC', sans-serif;
    }}

    /* ===== 主内容区 ===== */
    .main .block-container {{
        padding: {layout_padding};
        max-width: 1400px;
    }}

    /* ===== 标题样式 ===== */
    h1, h2, h3 {{
        font-family: 'Space Grotesk', 'Noto Sans SC', sans-serif !important;
        color: {t['text']} !important;
    }}

    /* ===== 卡片组件 ===== */
    .finance-card {{
        background: {t['card']};
        border: 1px solid {t['primary']}33;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 24px {t['primary']}22;
        transition: all 0.3s ease;
    }}
    .finance-card:hover {{
        border-color: {t['primary']}88;
        transform: translateY(-2px);
        box-shadow: 0 8px 32px {t['primary']}33;
    }}

    /* ===== 指标卡片 ===== */
    .metric-card {{
        background: linear-gradient(135deg, {t['card']}, {t['primary']}22);
        border: 1px solid {t['primary']}44;
        border-radius: 20px;
        padding: 1.8rem 1.5rem;
        text-align: center;
        position: relative;
        overflow: hidden;
    }}
    .metric-card::before {{
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 120px;
        height: 120px;
        background: {t['primary']}22;
        border-radius: 50%;
    }}
    .metric-value {{
        font-size: 2.2rem;
        font-weight: 900;
        font-family: 'Space Grotesk', monospace;
        line-height: 1.2;
    }}
    .metric-label {{
        font-size: 0.85rem;
        opacity: 0.7;
        margin-top: 0.3rem;
        letter-spacing: 0.05em;
    }}
    .metric-icon {{
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }}

    /* ===== 收入/支出颜色 ===== */
    .income-color {{ color: {t['income']}; }}
    .expense-color {{ color: {t['expense']}; }}
    .primary-color {{ color: {t['primary']}; }}
    .accent-color {{ color: {t['accent']}; }}

    /* ===== 预算进度条 ===== */
    .budget-bar-wrap {{
        background: {t['primary']}22;
        border-radius: 8px;
        height: 10px;
        margin: 0.4rem 0;
        overflow: hidden;
    }}
    .budget-bar {{
        height: 100%;
        border-radius: 8px;
        transition: width 0.6s ease;
    }}

    /* ===== 建议卡片 ===== */
    .advice-card {{
        background: {t['card']};
        border-left: 4px solid {t['accent']};
        border-radius: 0 12px 12px 0;
        padding: 1rem 1.2rem;
        margin: 0.6rem 0;
    }}
    .warning-card {{
        border-left-color: {t['expense']};
    }}
    .good-card {{
        border-left-color: {t['income']};
    }}

    /* ===== 模块标题 ===== */
    .section-header {{
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.8rem 0;
        border-bottom: 2px solid {t['primary']}44;
        margin-bottom: 1.2rem;
    }}
    .section-title {{
        font-size: 1.2rem;
        font-weight: 700;
        color: {t['text']};
    }}
    .section-badge {{
        background: {t['primary']};
        color: white;
        padding: 0.15rem 0.6rem;
        border-radius: 20px;
        font-size: 0.75rem;
    }}

    /* ===== 欢迎横幅 ===== */
    .welcome-banner {{
        background: linear-gradient(135deg, {t['primary']}, {t['secondary']}, {t['accent']});
        background-size: 200% 200%;
        animation: gradientShift 6s ease infinite;
        border-radius: 20px;
        padding: 2rem 2.5rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
        color: white;
    }}
    .welcome-banner::after {{
        content: '💰';
        position: absolute;
        right: 2rem;
        top: 50%;
        transform: translateY(-50%);
        font-size: 5rem;
        opacity: 0.2;
    }}
    @keyframes gradientShift {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}

    /* ===== Streamlit 组件覆盖 ===== */
    .stSelectbox > div > div,
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input,
    .stTextArea > div > div > textarea {{
        background: {t['card']} !important;
        color: {t['text']} !important;
        border: 1px solid {t['primary']}44 !important;
        border-radius: 10px !important;
    }}
    .stButton > button {{
        background: linear-gradient(135deg, {t['primary']}, {t['secondary']}) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px {t['primary']}66 !important;
    }}
    .stDataFrame {{
        border-radius: 12px !important;
        overflow: hidden !important;
    }}
    .stSidebar {{
        background: {t['card']} !important;
    }}
    .stSidebar .stMarkdown {{
        color: {t['text']} !important;
    }}

    /* ===== 标签页 ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background: {t['card']};
        padding: 8px;
        border-radius: 14px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent;
        color: {t['text']}aa;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }}
    .stTabs [aria-selected="true"] {{
        background: {t['primary']} !important;
        color: white !important;
    }}

    /* ===== 首次引导提示 ===== */
    .guide-tip {{
        background: linear-gradient(135deg, {t['primary']}22, {t['accent']}22);
        border: 1px dashed {t['primary']}66;
        border-radius: 14px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        font-size: 0.9rem;
    }}

    /* ===== 滚动条 ===== */
    ::-webkit-scrollbar {{ width: 6px; }}
    ::-webkit-scrollbar-track {{ background: {t['bg']}; }}
    ::-webkit-scrollbar-thumb {{
        background: {t['primary']}66;
        border-radius: 3px;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ============================================================
# 辅助函数
# ============================================================
def get_period_df(df, period, custom_start=None, custom_end=None):
    """按时间周期筛选数据"""
    if df.empty:
        return df
    now = datetime.now()
    if period == "今日":
        start = now.replace(hour=0, minute=0, second=0)
        end = now
    elif period == "本周":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0)
        end = now
    elif period == "本月":
        start = now.replace(day=1, hour=0, minute=0, second=0)
        end = now
    elif period == "本学期":
        # 假设学期为近5个月
        start = now - timedelta(days=150)
        end = now
    elif period == "全部":
        return df
    elif period == "自定义" and custom_start and custom_end:
        start = pd.Timestamp(custom_start)
        end = pd.Timestamp(custom_end) + timedelta(days=1)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0)
        end = now

    return df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))]


def format_amount(amount, prefix="¥"):
    """格式化金额显示"""
    return f"{prefix}{amount:,.2f}"


def get_theme_colors(theme_name):
    return THEMES.get(theme_name, THEMES["极光紫"])


# ============================================================
# UI 组件：顶部统计卡片
# ============================================================
def render_summary_cards(df, theme_name):
    t = get_theme_colors(theme_name)

    total_income = df[df["type"] == "收入"]["amount"].sum()
    total_expense = df[df["type"] == "支出"]["amount"].sum()
    balance = total_income - total_expense

    balance_color = t["income"] if balance >= 0 else t["expense"]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">📥</div>
            <div class="metric-value income-color">{format_amount(total_income)}</div>
            <div class="metric-label">总收入</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">📤</div>
            <div class="metric-value expense-color">{format_amount(total_expense)}</div>
            <div class="metric-label">总支出</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        sign = "+" if balance >= 0 else ""
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">{'💚' if balance >= 0 else '❤️'}</div>
            <div class="metric-value" style="color:{balance_color}">{sign}{format_amount(balance)}</div>
            <div class="metric-label">当期结余</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        tx_count = len(df)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">📋</div>
            <div class="metric-value primary-color">{tx_count}</div>
            <div class="metric-label">交易笔数</div>
        </div>""", unsafe_allow_html=True)


# ============================================================
# UI 组件：可视化图表
# ============================================================
def render_charts(df, theme_name, settings):
    t = get_theme_colors(theme_name)
    is_dark = t["mode"] == "dark"
    template = "plotly_dark" if is_dark else "plotly_white"
    colors = px.colors.qualitative.Pastel if not is_dark else px.colors.qualitative.Dark24

    expense_df = df[df["type"] == "支出"]
    income_df = df[df["type"] == "收入"]

    tab1, tab2, tab3, tab4 = st.tabs(["🥧 支出分布", "📊 月度对比", "📈 趋势变化", "🌡️ 消费热力图"])

    with tab1:
        if expense_df.empty:
            st.info("暂无支出数据")
        else:
            cat_sum = expense_df.groupby("category")["amount"].sum().reset_index()
            fig = px.pie(
                cat_sum, values="amount", names="category",
                title="支出类别占比",
                color_discrete_sequence=px.colors.qualitative.Set3,
                hole=0.45,
                template=template
            )
            fig.update_traces(
                textposition="outside",
                textinfo="percent+label",
                hovertemplate="<b>%{label}</b><br>金额: ¥%{value:.2f}<br>占比: %{percent}<extra></extra>"
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=t["text"], family="Noto Sans SC"),
                legend=dict(
                    bgcolor="rgba(0,0,0,0)",
                    font=dict(color=t["text"])
                ),
                title=dict(font=dict(size=16, color=t["text"]))
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if df.empty:
            st.info("暂无数据")
        else:
            df_copy = df.copy()
            df_copy["month"] = df_copy["date"].dt.to_period("M").astype(str)
            monthly = df_copy.groupby(["month", "type"])["amount"].sum().reset_index()

            fig = px.bar(
                monthly, x="month", y="amount", color="type",
                title="月度收支对比",
                barmode="group",
                color_discrete_map={"收入": t["income"], "支出": t["expense"]},
                template=template,
                text_auto=".0f"
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=t["text"], family="Noto Sans SC"),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=t["text"])),
                xaxis=dict(gridcolor=t["primary"] + "33"),
                yaxis=dict(gridcolor=t["primary"] + "33"),
                title=dict(font=dict(size=16, color=t["text"]))
            )
            fig.update_traces(
                hovertemplate="<b>%{x}</b><br>金额: ¥%{y:.2f}<extra></extra>",
                marker_line_width=0
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        if df.empty:
            st.info("暂无数据")
        else:
            df_copy = df.copy()
            df_copy["week"] = df_copy["date"].dt.to_period("W").apply(lambda r: r.start_time)
            weekly = df_copy.groupby(["week", "type"])["amount"].sum().reset_index()

            fig = go.Figure()
            for tx_type, color in [("收入", t["income"]), ("支出", t["expense"])]:
                sub = weekly[weekly["type"] == tx_type]
                if not sub.empty:
                    fig.add_trace(go.Scatter(
                        x=sub["week"], y=sub["amount"],
                        mode="lines+markers",
                        name=tx_type,
                        line=dict(color=color, width=2.5, shape="spline"),
                        marker=dict(size=7, color=color),
                        fill="tozeroy",
                        fillcolor=color + "22",
                        hovertemplate="<b>%{x|%Y-%m-%d}</b><br>¥%{y:.2f}<extra></extra>"
                    ))

            fig.update_layout(
                title="周度收支趋势",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=t["text"], family="Noto Sans SC"),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=t["text"])),
                xaxis=dict(gridcolor=t["primary"] + "22"),
                yaxis=dict(gridcolor=t["primary"] + "22"),
                title_font=dict(size=16, color=t["text"])
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab4:
        if expense_df.empty:
            st.info("暂无支出数据")
        else:
            df_copy = expense_df.copy()
            df_copy["weekday"] = df_copy["date"].dt.day_name()
            df_copy["hour_group"] = pd.cut(
                df_copy["date"].dt.hour,
                bins=[0, 8, 12, 14, 18, 22, 24],
                labels=["凌晨", "上午", "中午", "下午", "晚上", "深夜"],
                right=False
            )
            weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            weekday_cn = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
                          "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"}
            df_copy["weekday_cn"] = df_copy["weekday"].map(weekday_cn)

            # 按日期分组计算每日支出次数
            df_copy["day_of_week"] = df_copy["date"].dt.dayofweek
            df_copy["week_num"] = df_copy["date"].dt.isocalendar().week
            heatmap_data = df_copy.groupby(["day_of_week", "week_num"]).size().reset_index(name="count")

            pivot = df_copy.groupby("day_of_week")["amount"].sum()
            pivot_count = df_copy.groupby("day_of_week").size()
            days_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

            fig = go.Figure(data=go.Bar(
                x=days_cn,
                y=[pivot_count.get(i, 0) for i in range(7)],
                marker_color=[t["primary"], t["primary"], t["primary"],
                              t["primary"], t["primary"], t["accent"], t["accent"]],
                text=[pivot_count.get(i, 0) for i in range(7)],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>消费次数: %{y}次<extra></extra>"
            ))
            fig.update_layout(
                title="各星期消费频次分布",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=t["text"], family="Noto Sans SC"),
                xaxis=dict(gridcolor="rgba(0,0,0,0)"),
                yaxis=dict(gridcolor=t["primary"] + "22"),
                title_font=dict(size=16, color=t["text"])
            )
            st.plotly_chart(fig, use_container_width=True)


# ============================================================
# UI 组件：智能建议
# ============================================================
def render_advice(df, settings, theme_name):
    t = get_theme_colors(theme_name)
    expense_df = df[df["type"] == "支出"]

    if expense_df.empty:
        st.info("录入更多支出数据后，系统将为您生成个性化消费建议 🎯")
        return

    total_expense = expense_df["amount"].sum()
    cat_expense = expense_df.groupby("category")["amount"].sum()
    monthly_budget = settings.get("monthly_budget", 2000.0)

    # 预算执行情况
    st.markdown('<div class="section-header"><span>💡</span><span class="section-title">预算监控</span></div>', unsafe_allow_html=True)

    budget_ratio = (total_expense / monthly_budget * 100) if monthly_budget > 0 else 0
    bar_color = t["income"] if budget_ratio < 80 else (t["accent"] if budget_ratio < 100 else t["expense"])

    st.markdown(f"""
    <div class="finance-card">
        <div style="display:flex;justify-content:space-between;margin-bottom:0.5rem">
            <span>月度预算执行情况</span>
            <span style="color:{bar_color};font-weight:700">{budget_ratio:.1f}%</span>
        </div>
        <div class="budget-bar-wrap">
            <div class="budget-bar" style="width:{min(budget_ratio,100)}%;background:{bar_color}"></div>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:0.82rem;opacity:0.7;margin-top:0.4rem">
            <span>已支出 {format_amount(total_expense)}</span>
            <span>预算 {format_amount(monthly_budget)}</span>
        </div>
    </div>""", unsafe_allow_html=True)

    if budget_ratio >= 100:
        st.error(f"⚠️ 本期支出已超预算 {format_amount(total_expense - monthly_budget)}！建议立即控制消费。")
    elif budget_ratio >= 80:
        st.warning(f"⚡ 预算已使用 {budget_ratio:.1f}%，剩余 {format_amount(monthly_budget - total_expense)}，注意节省。")
    else:
        st.success(f"✅ 预算执行良好！剩余 {format_amount(monthly_budget - total_expense)}")

    # 各类别分析
    st.markdown('<div class="section-header" style="margin-top:1.5rem"><span>📊</span><span class="section-title">消费结构分析</span></div>', unsafe_allow_html=True)

    advice_list = []
    for cat, (lo, hi) in RECOMMENDED_RATIOS.items():
        actual = cat_expense.get(cat, 0)
        actual_ratio = (actual / total_expense * 100) if total_expense > 0 else 0

        status = "good" if lo <= actual_ratio <= hi else ("warning" if actual_ratio > hi else "info")
        if actual_ratio > hi:
            diff = actual_ratio - hi
            advice_list.append({
                "status": "warning",
                "cat": cat,
                "msg": f"**{cat}** 支出占比 {actual_ratio:.1f}%，超出建议上限 {hi}% 约 {diff:.1f}%。建议适当减少。",
                "amount": actual
            })
        elif actual_ratio < lo and actual > 0:
            advice_list.append({
                "status": "good",
                "cat": cat,
                "msg": f"**{cat}** 支出控制良好（{actual_ratio:.1f}%），在建议范围 {lo}%-{hi}% 内。",
                "amount": actual
            })

    if not advice_list:
        st.markdown("""<div class="advice-card good-card">
        🎉 您的消费结构非常健康！各类支出都在合理范围内。继续保持！</div>""", unsafe_allow_html=True)
    else:
        for a in advice_list:
            card_class = "warning-card" if a["status"] == "warning" else "good-card"
            icon = "⚠️" if a["status"] == "warning" else "✅"
            st.markdown(f'<div class="advice-card {card_class}">{icon} {a["msg"]}</div>',
                        unsafe_allow_html=True)

    # 个性化建议
    st.markdown('<div class="section-header" style="margin-top:1.5rem"><span>🎯</span><span class="section-title">个性化建议</span></div>', unsafe_allow_html=True)

    tips = []
    food = cat_expense.get("餐饮", 0)
    entertainment = cat_expense.get("娱乐", 0)
    study = cat_expense.get("学习/书籍", 0)

    if food > 0:
        avg_daily = food / max(df["date"].nunique(), 1)
        if avg_daily > 80:
            tips.append("🍜 日均餐饮支出较高，可考虑减少外卖频率、多在食堂就餐，预计每月可节省100-300元。")
        else:
            tips.append("🥗 餐饮支出合理，继续保持健康饮食习惯！")

    if entertainment > food * 0.3:
        tips.append("🎮 娱乐支出占餐饮的30%以上，建议寻找免费娱乐资源（图书馆、校园活动等）。")

    if study < total_expense * 0.05:
        tips.append("📚 学习投入比例偏低，适当增加书籍/课程投资有助于提升竞争力，这是最值得的消费！")

    income_df = df[df["type"] == "收入"]
    if not income_df.empty:
        part_time = income_df[income_df["category"] == "兼职收入"]["amount"].sum()
        if part_time > 0:
            tips.append(f"💪 本期兼职收入 {format_amount(part_time)}，独立创收意识很棒！建议将至少20%存入应急基金。")

    if not tips:
        tips.append("💡 数据积累中，记录更多消费后将获得更精准的个性化建议。")

    for tip in tips:
        st.markdown(f'<div class="advice-card">{tip}</div>', unsafe_allow_html=True)


# ============================================================
# UI 组件：记录管理
# ============================================================
def render_records_management(df, settings, theme_name):
    t = get_theme_colors(theme_name)

    tab1, tab2, tab3 = st.tabs(["➕ 新增记录", "📝 查看/编辑记录", "📤 导入/导出"])

    with tab1:
        st.markdown('<div class="guide-tip">💡 <b>快速录入</b>：选择收支类型、填写金额和类别，点击保存即可。支持多种支付方式记录。</div>',
                    unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            tx_type = st.selectbox("类型 *", ["支出", "收入"], key="add_type")
            categories = EXPENSE_CATEGORIES if tx_type == "支出" else INCOME_CATEGORIES
            category = st.selectbox("类别 *", categories, key="add_cat")
            amount = st.number_input("金额（元）*", min_value=0.01, value=50.0, step=0.01, key="add_amount")

        with col2:
            tx_date = st.date_input("日期 *", value=date.today(), key="add_date")
            payment = st.selectbox("支付方式", PAYMENT_METHODS, key="add_payment")
            note = st.text_input("备注（可选）", placeholder="如：和朋友聚餐、购买教材...", key="add_note")

        if st.button("💾 保存记录", key="btn_save", use_container_width=True):
            if amount <= 0:
                st.error("金额必须大于0！")
            else:
                new_id = f"{int(datetime.now().timestamp())}"
                new_row = pd.DataFrame([{
                    "id": new_id,
                    "type": tx_type,
                    "category": category,
                    "amount": round(amount, 2),
                    "date": pd.Timestamp(tx_date),
                    "note": note,
                    "payment_method": payment
                }])
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                save_data(st.session_state.df)
                st.success(f"✅ 已保存：{tx_type} - {category} - {format_amount(amount)}")
                st.rerun()

    with tab2:
        if df.empty:
            st.info("暂无记录，请先添加收支数据。")
        else:
            # 筛选控件
            with st.expander("🔍 筛选条件", expanded=False):
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    filter_type = st.multiselect("类型", ["收入", "支出"], default=["收入", "支出"])
                with fc2:
                    filter_cat = st.multiselect("类别", ALL_CATEGORIES, default=[])
                with fc3:
                    amt_min = st.number_input("最低金额", value=0.0, step=1.0)
                    amt_max = st.number_input("最高金额", value=10000.0, step=1.0)

                date_range = st.date_input("日期范围", value=(df["date"].min().date(), df["date"].max().date()))

            # 应用筛选
            filtered = df[df["type"].isin(filter_type if filter_type else ["收入", "支出"])]
            if filter_cat:
                filtered = filtered[filtered["category"].isin(filter_cat)]
            filtered = filtered[(filtered["amount"] >= amt_min) & (filtered["amount"] <= amt_max)]
            if len(date_range) == 2:
                filtered = filtered[
                    (filtered["date"] >= pd.Timestamp(date_range[0])) &
                    (filtered["date"] <= pd.Timestamp(date_range[1]) + timedelta(days=1))
                ]

            # 排序
            sort_map = {
                "日期降序": ("date", False),
                "日期升序": ("date", True),
                "金额降序": ("amount", False),
                "金额升序": ("amount", True)
            }
            sort_col, asc = sort_map.get(settings["sort_order"], ("date", False))
            filtered = filtered.sort_values(sort_col, ascending=asc)

            st.caption(f"共 {len(filtered)} 条记录")

            # 显示表格
            display_df = filtered[["date", "type", "category", "amount", "payment_method", "note"]].copy()
            display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
            display_df.columns = ["日期", "类型", "类别", "金额(元)", "支付方式", "备注"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # 删除功能
            st.markdown("---")
            del_id = st.text_input("输入要删除记录的序号（列表中的行号，从0开始）", placeholder="输入数字，如 0、1、2...")
            if st.button("🗑️ 删除该记录", type="secondary"):
                try:
                    idx = int(del_id)
                    if 0 <= idx < len(filtered):
                        record_id = filtered.iloc[idx]["id"]
                        st.session_state.df = st.session_state.df[st.session_state.df["id"] != record_id]
                        save_data(st.session_state.df)
                        st.success("记录已删除")
                        st.rerun()
                    else:
                        st.error("序号超出范围")
                except ValueError:
                    st.error("请输入有效的数字序号")

    with tab3:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**📥 导入数据**")
            uploaded = st.file_uploader("上传 CSV 文件", type=["csv"])
            if uploaded:
                try:
                    import_df = pd.read_csv(uploaded)
                    # 尝试映射列名
                    col_map = {
                        "类型": "type", "类别": "category", "金额(元)": "amount",
                        "日期": "date", "备注": "note", "支付方式": "payment_method"
                    }
                    import_df = import_df.rename(columns=col_map)
                    import_df["date"] = pd.to_datetime(import_df["date"])
                    import_df["id"] = [f"imp_{i}" for i in range(len(import_df))]
                    if "amount" not in import_df.columns:
                        st.error("CSV 必须包含金额列")
                    else:
                        st.dataframe(import_df.head(5))
                        if st.button("确认导入"):
                            st.session_state.df = pd.concat([st.session_state.df, import_df], ignore_index=True)
                            save_data(st.session_state.df)
                            st.success(f"✅ 成功导入 {len(import_df)} 条记录！")
                            st.rerun()
                except Exception as e:
                    st.error(f"导入失败：{e}")

        with col2:
            st.markdown("**📤 导出数据**")
            if not df.empty:
                export_df = df.copy()
                export_df["date"] = export_df["date"].dt.strftime("%Y-%m-%d")
                export_df = export_df.rename(columns={
                    "type": "类型", "category": "类别", "amount": "金额(元)",
                    "date": "日期", "note": "备注", "payment_method": "支付方式"
                })
                export_df = export_df[["日期", "类型", "类别", "金额(元)", "支付方式", "备注"]]

                # CSV 导出
                csv_buf = io.StringIO()
                export_df.to_csv(csv_buf, index=False, encoding="utf-8-sig")
                st.download_button(
                    "⬇️ 下载 CSV",
                    data=csv_buf.getvalue().encode("utf-8-sig"),
                    file_name=f"finance_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

                # Excel 导出
                try:
                    excel_buf = io.BytesIO()
                    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                        export_df.to_excel(writer, index=False, sheet_name="财务记录")
                    st.download_button(
                        "⬇️ 下载 Excel",
                        data=excel_buf.getvalue(),
                        file_name=f"finance_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                except ImportError:
                    st.caption("安装 openpyxl 以支持 Excel 导出：`pip install openpyxl`")
            else:
                st.info("暂无数据可导出")


# ============================================================
# 侧边栏
# ============================================================
def render_sidebar(settings):
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:1rem 0">
            <div style="font-size:2.5rem">🎓</div>
            <div style="font-size:1.1rem;font-weight:700;margin-top:0.3rem">Campus Finance</div>
            <div style="font-size:0.75rem;opacity:0.6">大学生财务管理系统</div>
        </div>""", unsafe_allow_html=True)

        st.divider()

        # 时间周期选择
        st.markdown("**📅 数据周期**")
        period = st.selectbox(
            "查看时段",
            ["本月", "本周", "今日", "本学期", "全部", "自定义"],
            index=["本月", "本周", "今日", "本学期", "全部", "自定义"].index(
                settings.get("default_period", "本月")
            ),
            label_visibility="collapsed"
        )

        custom_start, custom_end = None, None
        if period == "自定义":
            custom_start = st.date_input("开始日期", value=date.today() - timedelta(days=30))
            custom_end = st.date_input("结束日期", value=date.today())

        st.divider()

        # 主题设置
        st.markdown("**🎨 主题定制**")
        theme = st.selectbox("主题颜色", list(THEMES.keys()),
                             index=list(THEMES.keys()).index(settings.get("theme", "极光紫")))

        layout = st.radio("布局密度", ["宽松", "紧凑"],
                          index=["宽松", "紧凑"].index(settings.get("layout", "宽松")),
                          horizontal=True)

        sort_order = st.selectbox("排序方式", ["日期降序", "日期升序", "金额降序", "金额升序"],
                                  index=["日期降序", "日期升序", "金额降序", "金额升序"].index(
                                      settings.get("sort_order", "日期降序")
                                  ))

        st.divider()

        # 预算设置
        st.markdown("**💰 预算设置**")
        monthly_budget = st.number_input(
            "月度总预算（元）",
            min_value=0.0, value=float(settings.get("monthly_budget", 2000.0)), step=100.0
        )

        st.divider()

        # 显示模块控制
        st.markdown("**📦 显示模块**")
        show_summary = st.checkbox("统计总览", value=settings["show_modules"].get("summary", True))
        show_charts = st.checkbox("可视化图表", value=settings["show_modules"].get("charts", True))
        show_advice = st.checkbox("智能建议", value=settings["show_modules"].get("advice", True))
        show_records = st.checkbox("记录管理", value=settings["show_modules"].get("records", True))

        st.divider()

        # 数据管理
        st.markdown("**🗄️ 数据管理**")
        if st.button("🔄 加载示例数据", use_container_width=True):
            st.session_state.df = generate_sample_data()
            save_data(st.session_state.df)
            st.success("示例数据已加载！")
            st.rerun()

        if st.button("🗑️ 清空所有数据", use_container_width=True, type="secondary"):
            if st.session_state.get("confirm_clear"):
                st.session_state.df = pd.DataFrame(
                    columns=["id", "type", "category", "amount", "date", "note", "payment_method"])
                save_data(st.session_state.df)
                st.session_state.confirm_clear = False
                st.rerun()
            else:
                st.session_state.confirm_clear = True
                st.warning("再次点击确认清空所有数据！")

        # 保存设置
        new_settings = {
            "theme": theme,
            "layout": layout,
            "default_period": period,
            "sort_order": sort_order,
            "monthly_budget": monthly_budget,
            "show_modules": {
                "summary": show_summary,
                "charts": show_charts,
                "advice": show_advice,
                "records": show_records
            },
            "chart_style": settings.get("chart_style", "圆角"),
            "budgets": settings.get("budgets", {})
        }

        if new_settings != settings:
            save_settings(new_settings)

        st.markdown(f"""
        <div style="text-align:center;font-size:0.72rem;opacity:0.45;padding:1rem 0">
            v2.0 · 数据本地存储<br>Made with ❤️ for Students
        </div>""", unsafe_allow_html=True)

    return new_settings, period, custom_start, custom_end


# ============================================================
# 主程序
# ============================================================
def main():
    st.set_page_config(
        page_title="Campus Finance · 大学生财务管理",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 加载设置
    settings = load_settings()

    # 加载数据
    if "df" not in st.session_state:
        df = load_data()
        if df.empty:
            # 首次启动，加载示例数据
            df = generate_sample_data()
            save_data(df)
            st.session_state.first_run = True
        st.session_state.df = df
    else:
        df = st.session_state.df

    # 注入CSS主题
    inject_css(settings["theme"], settings)

    # 渲染侧边栏并获取最新设置
    settings, period, custom_start, custom_end = render_sidebar(settings)

    # 过滤当前时段数据
    filtered_df = get_period_df(df, period, custom_start, custom_end)

    # ===== 主内容区 =====

    # 欢迎横幅
    period_label = period if period != "自定义" else f"{custom_start} ~ {custom_end}"
    st.markdown(f"""
    <div class="welcome-banner">
        <div style="font-size:0.85rem;opacity:0.8;margin-bottom:0.3rem">欢迎回来 👋</div>
        <div style="font-size:1.8rem;font-weight:900;letter-spacing:-0.02em">
            Campus Finance
        </div>
        <div style="font-size:0.9rem;opacity:0.8;margin-top:0.4rem">
            当前查看：{period_label} · 共 {len(filtered_df)} 条记录
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 首次使用引导
    if st.session_state.get("first_run"):
        st.markdown("""
        <div class="guide-tip">
        🎉 <b>欢迎使用 Campus Finance！</b><br>
        系统已为您自动加载示例数据以展示功能。您可以：
        ① 在<b>左侧边栏</b>切换主题、设置预算、选择时间范围
        ② 在<b>记录管理</b>标签页手动添加您的真实收支记录
        ③ 点击<b>加载示例数据</b>可随时重置演示数据
        ④ 所有数据自动保存到本地，无需担心丢失
        </div>
        """, unsafe_allow_html=True)
        st.session_state.first_run = False

    # 模块1：统计总览
    if settings["show_modules"].get("summary", True):
        with st.expander("📊 统计总览", expanded=True):
            render_summary_cards(filtered_df, settings["theme"])

    # 模块2：可视化图表
    if settings["show_modules"].get("charts", True):
        with st.expander("📈 可视化图表", expanded=True):
            render_charts(filtered_df, settings["theme"], settings)

    # 模块3：智能建议
    if settings["show_modules"].get("advice", True):
        with st.expander("💡 智能消费建议", expanded=True):
            render_advice(filtered_df, settings, settings["theme"])

    # 模块4：记录管理
    if settings["show_modules"].get("records", True):
        with st.expander("📂 收支记录管理", expanded=True):
            render_records_management(df, settings, settings["theme"])


if __name__ == "__main__":
    main()