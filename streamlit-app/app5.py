"""
大学生财务管理系统 - Campus Finance Tracker v3.0
===========================================
功能模块：
1. 钱包/账户初始化（微信/支付宝/银行卡/现金）
2. 收支记录管理（增删改查）
3. 多维度可视化图表（已修复 Plotly 兼容性问题）
4. 实时资金建议
5. 个性化主题定制
6. 预算监控与超支提醒
7. 数据导出（CSV/Excel）

运行方式：streamlit run finance_app.py
依赖安装：pip install streamlit plotly pandas openpyxl
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime, timedelta, date
import random
import io
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 路径 & 常量
# ============================================================
DATA_FILE     = "finance_data.json"
SETTINGS_FILE = "finance_settings.json"
WALLETS_FILE  = "finance_wallets.json"

INCOME_CATEGORIES  = ["生活费/家庭", "兼职收入", "奖学金", "转账收入", "其他收入"]
EXPENSE_CATEGORIES = ["餐饮", "学习/书籍", "娱乐", "交通", "购物/服装",
                       "医疗", "日用品", "社交", "转账支出", "其他支出"]
ALL_CATEGORIES = INCOME_CATEGORIES + EXPENSE_CATEGORIES

WALLET_NAMES   = ["微信零钱", "支付宝余额", "银行卡", "现金"]
WALLET_ICONS   = {"微信零钱": "💚", "支付宝余额": "💙", "银行卡": "💳", "现金": "💵"}
PAYMENT_METHODS = WALLET_NAMES  # 支付方式与钱包对齐

RECOMMENDED_RATIOS = {
    "餐饮":     (35, 45), "学习/书籍": (10, 20), "娱乐":    (5, 15),
    "交通":     (5, 10),  "购物/服装": (5, 15),  "医疗":    (2, 8),
    "日用品":   (5, 10),  "社交":      (5, 10),  "其他支出": (0, 10),
}

THEMES = {
    "极光紫": {
        "primary": "#7C3AED", "secondary": "#A78BFA", "accent": "#F59E0B",
        "bg": "#0F0A1E", "card": "#1E1535", "text": "#F3F0FF",
        "income": "#10B981", "expense": "#EF4444", "mode": "dark",
    },
    "珊瑚橙": {
        "primary": "#EA580C", "secondary": "#FB923C", "accent": "#0EA5E9",
        "bg": "#1C0F0A", "card": "#2D1A10", "text": "#FFF7F0",
        "income": "#22C55E", "expense": "#F43F5E", "mode": "dark",
    },
    "海洋蓝": {
        "primary": "#0369A1", "secondary": "#38BDF8", "accent": "#F97316",
        "bg": "#F0F9FF", "card": "#FFFFFF", "text": "#0C4A6E",
        "income": "#059669", "expense": "#DC2626", "mode": "light",
    },
    "抹茶绿": {
        "primary": "#15803D", "secondary": "#4ADE80", "accent": "#A21CAF",
        "bg": "#F0FDF4", "card": "#FFFFFF", "text": "#14532D",
        "income": "#16A34A", "expense": "#B91C1C", "mode": "light",
    },
    "樱花粉": {
        "primary": "#BE185D", "secondary": "#F472B6", "accent": "#7C3AED",
        "bg": "#FDF2F8", "card": "#FFFFFF", "text": "#831843",
        "income": "#0D9488", "expense": "#E11D48", "mode": "light",
    },
    "深夜黑": {
        "primary": "#E2E8F0", "secondary": "#94A3B8", "accent": "#F59E0B",
        "bg": "#0D1117", "card": "#161B22", "text": "#E6EDF3",
        "income": "#3FB950", "expense": "#F85149", "mode": "dark",
    },
}

# ============================================================
# 钱包数据持久化
# ============================================================
def load_wallets() -> dict:
    if os.path.exists(WALLETS_FILE):
        try:
            with open(WALLETS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {w: 0.0 for w in WALLET_NAMES}

def save_wallets(wallets: dict):
    with open(WALLETS_FILE, "w", encoding="utf-8") as f:
        json.dump(wallets, f, ensure_ascii=False, indent=2)

# ============================================================
# 收支数据持久化
# ============================================================
def load_data() -> pd.DataFrame:
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

def save_data(df: pd.DataFrame):
    records = df.copy()
    if not records.empty:
        records["date"] = records["date"].dt.strftime("%Y-%m-%d")
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records.to_dict("records"), f, ensure_ascii=False, indent=2)

# ============================================================
# 设置持久化
# ============================================================
def load_settings() -> dict:
    default = {
        "theme": "极光紫", "layout": "宽松", "default_period": "本月",
        "sort_order": "日期降序", "monthly_budget": 2000.0,
        "show_modules": {"summary": True, "wallets": True, "charts": True,
                         "advice": True, "records": True},
        "wallets_initialized": False,
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            default.update(saved)
        except Exception:
            pass
    return default

def save_settings(settings: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

# ============================================================
# 示例数据生成
# ============================================================
def generate_sample_data() -> pd.DataFrame:
    random.seed(42)
    records, today = [], datetime.now()
    for i in range(90):
        day = today - timedelta(days=i)
        if day.day == 1:
            records.append({"id": f"s{i}_1", "type": "收入", "category": "生活费/家庭",
                             "amount": round(random.uniform(1500, 2000), 2),
                             "date": day.strftime("%Y-%m-%d"), "note": "月度生活费",
                             "payment_method": "银行卡"})
        for j in range(random.randint(0, 3)):
            cat = random.choice(EXPENSE_CATEGORIES)
            lo, hi = {"餐饮":(8,60),"学习/书籍":(20,200),"娱乐":(10,150),"交通":(2,50),
                       "购物/服装":(30,300),"医疗":(10,100),"日用品":(5,80),"社交":(20,200)}.get(cat,(5,100))
            records.append({"id": f"s{i}_{j}", "type": "支出", "category": cat,
                             "amount": round(random.uniform(lo, hi), 2),
                             "date": day.strftime("%Y-%m-%d"), "note": "",
                             "payment_method": random.choice(PAYMENT_METHODS)})
        if random.random() < 0.05:
            records.append({"id": f"s{i}_pt", "type": "收入", "category": "兼职收入",
                             "amount": round(random.uniform(50, 500), 2),
                             "date": day.strftime("%Y-%m-%d"), "note": "兼职收入",
                             "payment_method": "微信零钱"})
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    return df

# ============================================================
# 辅助函数
# ============================================================
def get_period_df(df, period, custom_start=None, custom_end=None):
    if df.empty:
        return df
    now = datetime.now()
    if period == "今日":
        s = now.replace(hour=0, minute=0, second=0); e = now
    elif period == "本周":
        s = (now - timedelta(days=now.weekday())).replace(hour=0,minute=0,second=0); e = now
    elif period == "本月":
        s = now.replace(day=1,hour=0,minute=0,second=0); e = now
    elif period == "本学期":
        s = now - timedelta(days=150); e = now
    elif period == "全部":
        return df
    elif period == "自定义" and custom_start and custom_end:
        s = pd.Timestamp(custom_start); e = pd.Timestamp(custom_end) + timedelta(days=1)
    else:
        s = now.replace(day=1,hour=0,minute=0,second=0); e = now
    return df[(df["date"] >= pd.Timestamp(s)) & (df["date"] <= pd.Timestamp(e))]

def fmt(amount): return f"¥{amount:,.2f}"
def tc(theme_name): return THEMES.get(theme_name, THEMES["极光紫"])

# ============================================================
# 安全的 Plotly 布局 helper（修复兼容性问题）
# ============================================================
def safe_layout(t: dict, title_text: str = "") -> dict:
    """返回兼容所有 Plotly 版本的 layout 字典"""
    layout = {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor":  "rgba(0,0,0,0)",
        "font_color":    t["text"],
        "font_family":   "Noto Sans SC",
    }
    if title_text:
        layout["title_text"] = title_text
        layout["title_font_size"] = 16
        layout["title_font_color"] = t["text"]
    return layout

# ============================================================
# CSS 主题注入
# ============================================================
def inject_css(theme_name, settings):
    t = tc(theme_name)
    pad = "1rem" if settings["layout"] == "紧凑" else "2rem"
    st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&family=Space+Grotesk:wght@400;600;700&display=swap');

.stApp {{ background:{t['bg']}; color:{t['text']}; font-family:'Noto Sans SC',sans-serif; }}
.main .block-container {{ padding:{pad}; max-width:1400px; }}
h1,h2,h3 {{ color:{t['text']} !important; font-family:'Space Grotesk','Noto Sans SC',sans-serif !important; }}

.metric-card {{
  background:linear-gradient(135deg,{t['card']},{t['primary']}18);
  border:1px solid {t['primary']}44; border-radius:20px;
  padding:1.6rem 1.4rem; text-align:center; position:relative; overflow:hidden;
}}
.metric-value {{ font-family:'Space Grotesk',monospace; font-size:2rem; font-weight:700; line-height:1.2; }}
.metric-label {{ font-size:0.82rem; opacity:0.65; margin-top:0.3rem; }}
.metric-icon  {{ font-size:1.8rem; margin-bottom:0.4rem; }}

.wallet-card {{
  background:{t['card']}; border:1px solid {t['primary']}33;
  border-radius:16px; padding:1.2rem 1.4rem; margin-bottom:0.8rem;
  display:flex; align-items:center; justify-content:space-between;
  transition:all .3s;
}}
.wallet-card:hover {{ border-color:{t['primary']}88; transform:translateY(-2px); box-shadow:0 6px 24px {t['primary']}22; }}
.wallet-icon {{ font-size:1.8rem; margin-right:0.8rem; }}
.wallet-name {{ font-size:0.85rem; opacity:0.65; }}
.wallet-amount {{ font-family:'Space Grotesk',monospace; font-size:1.4rem; font-weight:700; color:{t['primary']}; }}
.wallet-total {{
  background:linear-gradient(135deg,{t['primary']},{t['secondary']});
  border-radius:16px; padding:1.2rem 1.8rem; color:white;
  display:flex; align-items:center; justify-content:space-between; margin-bottom:1.2rem;
}}

.finance-card {{
  background:{t['card']}; border:1px solid {t['primary']}22;
  border-radius:16px; padding:1.4rem; margin-bottom:0.9rem;
  box-shadow:0 4px 20px {t['primary']}12; transition:all .3s;
}}
.budget-bar-wrap {{ background:{t['primary']}22; border-radius:8px; height:10px; margin:.4rem 0; overflow:hidden; }}
.budget-bar {{ height:100%; border-radius:8px; transition:width .6s; }}

.advice-card {{ background:{t['card']}; border-left:4px solid {t['accent']}; border-radius:0 12px 12px 0; padding:1rem 1.2rem; margin:.5rem 0; }}
.warning-card {{ border-left-color:{t['expense']}; }}
.good-card    {{ border-left-color:{t['income']}; }}
.urgent-card  {{ border-left-color:#FF0000; background:rgba(255,0,0,0.08); }}

.welcome-banner {{
  background:linear-gradient(135deg,{t['primary']},{t['secondary']},{t['accent']});
  border-radius:20px; padding:1.8rem 2.4rem; margin-bottom:1.8rem;
  color:white; position:relative; overflow:hidden;
}}
.welcome-banner::after {{ content:'💰'; position:absolute; right:2rem; top:50%;
  transform:translateY(-50%); font-size:5rem; opacity:.15; }}

.section-header {{
  display:flex; align-items:center; gap:.6rem;
  padding:.8rem 0; border-bottom:2px solid {t['primary']}33; margin-bottom:1.2rem;
}}
.section-title {{ font-size:1.1rem; font-weight:700; color:{t['text']}; }}

.guide-tip {{
  background:linear-gradient(135deg,{t['primary']}15,{t['accent']}15);
  border:1px dashed {t['primary']}55; border-radius:14px; padding:1.1rem; margin:.7rem 0; font-size:.88rem;
}}

.stSelectbox>div>div, .stTextInput>div>div>input,
.stNumberInput>div>div>input, .stDateInput>div>div>input,
.stTextArea>div>div>textarea {{
  background:{t['card']} !important; color:{t['text']} !important;
  border:1px solid {t['primary']}44 !important; border-radius:10px !important;
}}
.stButton>button {{
  background:linear-gradient(135deg,{t['primary']},{t['secondary']}) !important;
  color:white !important; border:none !important; border-radius:10px !important;
  font-weight:600 !important; transition:all .25s !important;
}}
.stButton>button:hover {{ transform:translateY(-2px) !important; box-shadow:0 6px 18px {t['primary']}55 !important; }}
.stSidebar {{ background:{t['card']} !important; }}
.stTabs [data-baseweb="tab-list"] {{ gap:8px; background:{t['card']}; padding:8px; border-radius:14px; }}
.stTabs [data-baseweb="tab"] {{ background:transparent; color:{t['text']}99; border-radius:10px; padding:.45rem 1rem; font-weight:500; }}
.stTabs [aria-selected="true"] {{ background:{t['primary']} !important; color:white !important; }}
::-webkit-scrollbar {{ width:6px; }}
::-webkit-scrollbar-track {{ background:{t['bg']}; }}
::-webkit-scrollbar-thumb {{ background:{t['primary']}66; border-radius:3px; }}
.income-color  {{ color:{t['income']}; }}
.expense-color {{ color:{t['expense']}; }}
.primary-color {{ color:{t['primary']}; }}
</style>""", unsafe_allow_html=True)

# ============================================================
# 钱包面板
# ============================================================
def render_wallet_panel(theme_name):
    t = tc(theme_name)
    wallets = st.session_state.wallets
    total = sum(wallets.values())

    # 总资产横幅
    st.markdown(f"""
    <div class="wallet-total">
      <div>
        <div style="font-size:.82rem;opacity:.85">💰 当前总资产</div>
        <div style="font-size:2rem;font-weight:900;font-family:'Space Grotesk',monospace">{fmt(total)}</div>
      </div>
      <div style="font-size:2.5rem;opacity:.4">🏦</div>
    </div>""", unsafe_allow_html=True)

    cols = st.columns(2)
    wallet_list = list(wallets.items())
    for i, (name, amount) in enumerate(wallet_list):
        icon = WALLET_ICONS.get(name, "💰")
        with cols[i % 2]:
            st.markdown(f"""
            <div class="wallet-card">
              <div style="display:flex;align-items:center">
                <span class="wallet-icon">{icon}</span>
                <span class="wallet-name">{name}</span>
              </div>
              <span class="wallet-amount">{fmt(amount)}</span>
            </div>""", unsafe_allow_html=True)

    # 修改余额
    with st.expander("✏️ 修改账户余额", expanded=False):
        st.markdown('<div class="guide-tip">💡 当余额发生变化时（充值/提现/转账等），在此直接更新各账户的最新余额。</div>', unsafe_allow_html=True)
        edit_cols = st.columns(2)
        new_vals = {}
        for i, name in enumerate(WALLET_NAMES):
            with edit_cols[i % 2]:
                new_vals[name] = st.number_input(
                    f"{WALLET_ICONS.get(name,'')} {name}（元）",
                    min_value=0.0,
                    value=float(wallets.get(name, 0.0)),
                    step=1.0,
                    key=f"wallet_edit_{name}"
                )
        if st.button("💾 保存余额", use_container_width=True, key="save_wallets"):
            old_total = sum(st.session_state.wallets.values())
            new_total = sum(new_vals.values())
            diff = new_total - old_total
            st.session_state.wallets = new_vals
            save_wallets(new_vals)
            if abs(diff) > 0.01:
                # 自动记录余额调整
                adj_type = "收入" if diff > 0 else "支出"
                adj_cat  = "其他收入" if diff > 0 else "其他支出"
                adj_row  = pd.DataFrame([{
                    "id": f"adj_{int(datetime.now().timestamp()*1000)}",
                    "type": adj_type, "category": adj_cat,
                    "amount": round(abs(diff), 2),
                    "date": pd.Timestamp(date.today()),
                    "note": "余额手动调整",
                    "payment_method": "银行卡"
                }])
                st.session_state.df = pd.concat([st.session_state.df, adj_row], ignore_index=True)
                save_data(st.session_state.df)
            st.success(f"✅ 余额已更新！总资产：{fmt(sum(new_vals.values()))}")
            st.rerun()

# ============================================================
# 统计总览卡片
# ============================================================
def render_summary_cards(df, theme_name):
    t = tc(theme_name)
    income  = df[df["type"]=="收入"]["amount"].sum()
    expense = df[df["type"]=="支出"]["amount"].sum()
    balance = income - expense
    bcol = t["income"] if balance >= 0 else t["expense"]
    total_assets = sum(st.session_state.wallets.values())

    c1,c2,c3,c4 = st.columns(4)
    for col, icon, val, color, label in [
        (c1,"📥",fmt(income),   t["income"],  "期间收入"),
        (c2,"📤",fmt(expense),  t["expense"], "期间支出"),
        (c3,"💰",(("+" if balance>=0 else "")+fmt(balance)), bcol, "期间结余"),
        (c4,"🏦",fmt(total_assets), t["primary"], "当前总资产"),
    ]:
        col.markdown(f"""<div class="metric-card">
          <div class="metric-icon">{icon}</div>
          <div class="metric-value" style="color:{color}">{val}</div>
          <div class="metric-label">{label}</div>
        </div>""", unsafe_allow_html=True)

# ============================================================
# 可视化图表（修复所有 Plotly 兼容性问题）
# ============================================================
def render_charts(df, theme_name):
    t = tc(theme_name)
    is_dark = t["mode"] == "dark"
    template = "plotly_dark" if is_dark else "plotly_white"

    exp_df = df[df["type"]=="支出"]
    tab1,tab2,tab3,tab4 = st.tabs(["🥧 支出分布","📊 月度对比","📈 趋势变化","🗓️ 消费频次"])

    # ── Tab1: 支出饼图 ──
    with tab1:
        if exp_df.empty:
            st.info("暂无支出数据"); return
        cat_sum = exp_df.groupby("category")["amount"].sum().reset_index()
        fig = px.pie(cat_sum, values="amount", names="category", hole=.42,
                     color_discrete_sequence=px.colors.qualitative.Set3,
                     template=template)
        fig.update_traces(
            textposition="outside", textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>¥%{value:.2f} · %{percent}<extra></extra>"
        )
        fig.update_layout(**safe_layout(t, "支出类别占比"))
        st.plotly_chart(fig, use_container_width=True)

    # ── Tab2: 月度柱状图 ──
    with tab2:
        if df.empty:
            st.info("暂无数据"); return
        dc = df.copy()
        dc["month"] = dc["date"].dt.to_period("M").astype(str)
        monthly = dc.groupby(["month","type"])["amount"].sum().reset_index()
        fig = px.bar(monthly, x="month", y="amount", color="type", barmode="group",
                     color_discrete_map={"收入":t["income"],"支出":t["expense"]},
                     template=template, text_auto=".0f")
        layout = safe_layout(t, "月度收支对比")
        layout["xaxis_gridcolor"] = t["primary"] + "22"
        layout["yaxis_gridcolor"] = t["primary"] + "22"
        layout["legend_title_text"] = ""
        fig.update_layout(**layout)
        fig.update_traces(hovertemplate="<b>%{x}</b><br>¥%{y:.2f}<extra></extra>",
                          marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True)

    # ── Tab3: 周度趋势折线 ──
    with tab3:
        if df.empty:
            st.info("暂无数据"); return
        dc = df.copy()
        dc["week"] = dc["date"].dt.to_period("W").apply(lambda r: r.start_time)
        weekly = dc.groupby(["week","type"])["amount"].sum().reset_index()
        fig = go.Figure()
        for tp, color in [("收入",t["income"]),("支出",t["expense"])]:
            sub = weekly[weekly["type"]==tp]
            if sub.empty: continue
            fig.add_trace(go.Scatter(
                x=sub["week"], y=sub["amount"], name=tp,
                mode="lines+markers",
                line=dict(color=color, width=2.5, shape="spline"),
                marker=dict(size=7, color=color),
                fill="tozeroy", fillcolor=color+"22",
                hovertemplate="<b>%{x|%Y-%m-%d}</b><br>¥%{y:.2f}<extra></extra>"
            ))
        layout = safe_layout(t, "周度收支趋势")
        layout["xaxis_gridcolor"] = t["primary"] + "22"
        layout["yaxis_gridcolor"] = t["primary"] + "22"
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True)

    # ── Tab4: 星期消费频次 ──
    with tab4:
        if exp_df.empty:
            st.info("暂无支出数据"); return
        dc = exp_df.copy()
        dc["dow"] = dc["date"].dt.dayofweek
        counts = dc.groupby("dow").size().reindex(range(7), fill_value=0)
        days_cn = ["周一","周二","周三","周四","周五","周六","周日"]
        bar_colors = [t["primary"]]*5 + [t["accent"]]*2
        fig = go.Figure(go.Bar(
            x=days_cn, y=counts.values, marker_color=bar_colors,
            text=counts.values, textposition="outside",
            hovertemplate="<b>%{x}</b><br>消费%{y}次<extra></extra>"
        ))
        layout = safe_layout(t, "各星期消费频次")
        layout["xaxis_gridcolor"] = "rgba(0,0,0,0)"
        layout["yaxis_gridcolor"] = t["primary"] + "22"
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
# 实时资金建议
# ============================================================
def render_advice(df, settings, theme_name):
    t = tc(theme_name)
    wallets = st.session_state.wallets
    total_assets = sum(wallets.values())
    exp_df = df[df["type"]=="支出"]
    budget = settings.get("monthly_budget", 2000.0)

    # ── 资产健康预警 ──
    st.markdown('<div class="section-header"><span>🏦</span><span class="section-title">资产健康状态</span></div>', unsafe_allow_html=True)

    if total_assets < 200:
        st.markdown(f'<div class="advice-card urgent-card">🚨 <b>紧急预警</b>：当前总资产仅 {fmt(total_assets)}，已进入危险区间！建议立即联系家人补充生活费，减少一切非必要支出。</div>', unsafe_allow_html=True)
    elif total_assets < 500:
        st.markdown(f'<div class="advice-card warning-card">⚠️ <b>余额偏低</b>：当前总资产 {fmt(total_assets)}，建议控制消费，优先保障餐饮和交通支出。</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="advice-card good-card">✅ <b>资产状况良好</b>：当前总资产 {fmt(total_assets)}，继续保持理性消费。</div>', unsafe_allow_html=True)

    # 各账户低余额提示
    for name, amount in wallets.items():
        if amount < 50 and amount > 0:
            st.markdown(f'<div class="advice-card warning-card">💡 <b>{name}</b> 余额仅 {fmt(amount)}，建议及时充值。</div>', unsafe_allow_html=True)

    # ── 预算监控 ──
    if not exp_df.empty:
        st.markdown('<div class="section-header" style="margin-top:1.5rem"><span>💡</span><span class="section-title">本月预算监控</span></div>', unsafe_allow_html=True)
        total_exp = exp_df["amount"].sum()
        ratio = (total_exp / budget * 100) if budget > 0 else 0
        bar_c = t["income"] if ratio < 80 else (t["accent"] if ratio < 100 else t["expense"])

        st.markdown(f"""<div class="finance-card">
          <div style="display:flex;justify-content:space-between;margin-bottom:.5rem">
            <span>月度预算执行</span>
            <span style="color:{bar_c};font-weight:700">{ratio:.1f}%</span>
          </div>
          <div class="budget-bar-wrap"><div class="budget-bar" style="width:{min(ratio,100):.1f}%;background:{bar_c}"></div></div>
          <div style="display:flex;justify-content:space-between;font-size:.8rem;opacity:.65;margin-top:.4rem">
            <span>已支出 {fmt(total_exp)}</span><span>预算 {fmt(budget)}</span>
          </div>
        </div>""", unsafe_allow_html=True)

        if ratio >= 100:   st.error(f"⚠️ 已超预算 {fmt(total_exp - budget)}！请立即控制消费。")
        elif ratio >= 80:  st.warning(f"⚡ 预算已用 {ratio:.1f}%，剩余 {fmt(budget - total_exp)}，注意节省。")
        else:              st.success(f"✅ 预算执行良好！剩余 {fmt(budget - total_exp)}")

        # ── 消费结构分析 ──
        st.markdown('<div class="section-header" style="margin-top:1.5rem"><span>📊</span><span class="section-title">消费结构分析</span></div>', unsafe_allow_html=True)
        cat_expense = exp_df.groupby("category")["amount"].sum()
        for cat,(lo,hi) in RECOMMENDED_RATIOS.items():
            actual = cat_expense.get(cat, 0)
            ar = (actual / total_exp * 100) if total_exp > 0 else 0
            if ar > hi:
                st.markdown(f'<div class="advice-card warning-card">⚠️ <b>{cat}</b> 占比 {ar:.1f}%，高于建议上限 {hi}%，建议适当减少。</div>', unsafe_allow_html=True)
            elif lo <= ar <= hi and actual > 0:
                st.markdown(f'<div class="advice-card good-card">✅ <b>{cat}</b> 支出占比 {ar:.1f}%，处于合理区间。</div>', unsafe_allow_html=True)

    # ── 实时消费建议 ──
    st.markdown('<div class="section-header" style="margin-top:1.5rem"><span>🎯</span><span class="section-title">实时消费建议</span></div>', unsafe_allow_html=True)
    tips = []

    # 基于总资产的建议
    if total_assets > 0 and budget > 0:
        days_in_month = 30
        today_day = datetime.now().day
        days_left = days_in_month - today_day + 1
        daily_budget = (total_assets / days_left) if days_left > 0 else 0
        tips.append(f"📅 当前总资产 {fmt(total_assets)}，月底还有 {days_left} 天，日均可用 {fmt(daily_budget)}。")
        if daily_budget < 30:
            tips.append("🍱 日均预算偏低，建议以食堂用餐为主，暂停娱乐和购物消费。")
        elif daily_budget < 60:
            tips.append("🎯 预算适中，建议餐饮控制在 40 元/天以内，减少冲动消费。")
        else:
            tips.append("💪 日均预算充足，但仍建议保留 20% 作为应急储备。")

    if not exp_df.empty:
        cat_expense = exp_df.groupby("category")["amount"].sum()
        food = cat_expense.get("餐饮", 0)
        entertainment = cat_expense.get("娱乐", 0)
        study = cat_expense.get("学习/书籍", 0)
        total_exp = exp_df["amount"].sum()

        if food > 0:
            avg = food / max(len(df["date"].dt.date.unique()), 1)
            if avg > 80:
                tips.append(f"🍜 日均餐饮 {fmt(avg)} 偏高，多在食堂用餐可节省 100-300 元/月。")

        if entertainment > 0 and food > 0 and entertainment > food * 0.3:
            tips.append("🎮 娱乐支出占餐饮 30% 以上，建议利用图书馆、校园免费资源替代付费娱乐。")

        if study < total_exp * 0.05 and total_exp > 0:
            tips.append("📚 学习投入偏低，适当增加书籍/课程消费是性价比最高的投资！")

        inc_df = df[df["type"]=="收入"]
        if not inc_df.empty:
            pt = inc_df[inc_df["category"]=="兼职收入"]["amount"].sum()
            if pt > 0:
                tips.append(f"💪 本期兼职收入 {fmt(pt)}，建议将至少 20% 转入储蓄账户作为应急基金。")

    if not tips:
        tips.append("💡 记录更多收支数据后，系统将为您生成更精准的个性化建议。")

    for tip in tips:
        st.markdown(f'<div class="advice-card">{tip}</div>', unsafe_allow_html=True)

# ============================================================
# 记录管理
# ============================================================
def render_records_management(df, settings):
    tab1,tab2,tab3 = st.tabs(["➕ 新增记录","📝 查看/编辑","📤 导入/导出"])

    with tab1:
        st.markdown('<div class="guide-tip">💡 每笔收支都会自动更新对应账户余额。选择正确的支付方式确保账户数据准确。</div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            tx_type = st.selectbox("类型 *", ["支出","收入"], key="a_type")
            cats    = EXPENSE_CATEGORIES if tx_type=="支出" else INCOME_CATEGORIES
            cat     = st.selectbox("类别 *", cats, key="a_cat")
            amount  = st.number_input("金额（元）*", min_value=0.01, value=50.0, step=0.01, key="a_amt")
        with c2:
            tx_date = st.date_input("日期 *", value=date.today(), key="a_date")
            payment = st.selectbox("支付账户", PAYMENT_METHODS, key="a_pay")
            note    = st.text_input("备注（可选）", placeholder="如：食堂午饭、购买教材...", key="a_note")

        if st.button("💾 保存记录", use_container_width=True):
            if amount <= 0:
                st.error("金额须大于 0")
            else:
                # 更新钱包余额
                wallets = st.session_state.wallets.copy()
                if tx_type == "支出":
                    if wallets.get(payment, 0) < amount:
                        st.warning(f"⚠️ {payment} 余额不足（当前 {fmt(wallets.get(payment,0))}），记录已保存但请注意补充余额。")
                    wallets[payment] = max(0.0, wallets.get(payment, 0) - amount)
                else:
                    wallets[payment] = wallets.get(payment, 0) + amount

                st.session_state.wallets = wallets
                save_wallets(wallets)

                new_row = pd.DataFrame([{
                    "id": str(int(datetime.now().timestamp()*1000)),
                    "type": tx_type, "category": cat, "amount": round(amount,2),
                    "date": pd.Timestamp(tx_date), "note": note, "payment_method": payment
                }])
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                save_data(st.session_state.df)
                st.success(f"✅ 已保存：{tx_type} · {cat} · {fmt(amount)}  →  {payment} 余额：{fmt(wallets[payment])}")
                st.rerun()

    with tab2:
        if df.empty:
            st.info("暂无记录，先在「新增记录」添加数据吧。"); return

        with st.expander("🔍 筛选条件", expanded=False):
            fa,fb,fc = st.columns(3)
            with fa: f_type = st.multiselect("类型", ["收入","支出"], default=["收入","支出"])
            with fb: f_cat  = st.multiselect("类别", ALL_CATEGORIES, default=[])
            with fc:
                amt_min = st.number_input("最低金额", value=0.0, step=1.0)
                amt_max = st.number_input("最高金额", value=10000.0, step=1.0)
            dr = st.date_input("日期范围", value=(df["date"].min().date(), df["date"].max().date()))

        filt = df[df["type"].isin(f_type or ["收入","支出"])]
        if f_cat: filt = filt[filt["category"].isin(f_cat)]
        filt = filt[(filt["amount"]>=amt_min)&(filt["amount"]<=amt_max)]
        if len(dr)==2:
            filt = filt[(filt["date"]>=pd.Timestamp(dr[0]))&(filt["date"]<=pd.Timestamp(dr[1])+timedelta(days=1))]

        sort_map={"日期降序":("date",False),"日期升序":("date",True),"金额降序":("amount",False),"金额升序":("amount",True)}
        sc,asc = sort_map.get(settings["sort_order"],("date",False))
        filt = filt.sort_values(sc, ascending=asc)

        st.caption(f"共 {len(filt)} 条记录")
        disp = filt[["date","type","category","amount","payment_method","note"]].copy()
        disp["date"] = disp["date"].dt.strftime("%Y-%m-%d")
        disp.columns = ["日期","类型","类别","金额(元)","支付账户","备注"]
        st.dataframe(disp, use_container_width=True, hide_index=True)

        st.markdown("---")
        del_idx = st.text_input("输入要删除的行号（从 0 开始）", placeholder="如: 0", key="del_idx")
        if st.button("🗑️ 删除该记录", type="secondary"):
            try:
                idx = int(del_idx)
                if 0 <= idx < len(filt):
                    row = filt.iloc[idx]
                    # 反向更新钱包
                    wallets = st.session_state.wallets.copy()
                    pm = row["payment_method"]
                    if pm in wallets:
                        if row["type"] == "支出":
                            wallets[pm] = wallets[pm] + row["amount"]
                        else:
                            wallets[pm] = max(0.0, wallets[pm] - row["amount"])
                        st.session_state.wallets = wallets
                        save_wallets(wallets)
                    st.session_state.df = st.session_state.df[st.session_state.df["id"]!=row["id"]]
                    save_data(st.session_state.df)
                    st.success("记录已删除，账户余额已同步更新"); st.rerun()
                else:
                    st.error("序号超出范围")
            except ValueError:
                st.error("请输入有效数字")

    with tab3:
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**📥 导入 CSV**")
            up = st.file_uploader("上传 CSV", type=["csv"])
            if up:
                try:
                    imp = pd.read_csv(up).rename(columns={
                        "类型":"type","类别":"category","金额(元)":"amount",
                        "日期":"date","备注":"note","支付账户":"payment_method"})
                    imp["date"] = pd.to_datetime(imp["date"])
                    imp["id"]   = [f"imp_{i}" for i in range(len(imp))]
                    st.dataframe(imp.head())
                    if st.button("确认导入"):
                        st.session_state.df = pd.concat([st.session_state.df, imp], ignore_index=True)
                        save_data(st.session_state.df)
                        st.success(f"成功导入 {len(imp)} 条"); st.rerun()
                except Exception as e:
                    st.error(f"导入失败：{e}")
        with c2:
            st.markdown("**📤 导出数据**")
            if not df.empty:
                exp = df.copy(); exp["date"] = exp["date"].dt.strftime("%Y-%m-%d")
                exp = exp.rename(columns={"type":"类型","category":"类别","amount":"金额(元)",
                                           "date":"日期","note":"备注","payment_method":"支付账户"})
                exp = exp[["日期","类型","类别","金额(元)","支付账户","备注"]]
                buf = io.StringIO(); exp.to_csv(buf, index=False, encoding="utf-8-sig")
                st.download_button("⬇️ 下载 CSV", data=buf.getvalue().encode("utf-8-sig"),
                                   file_name=f"finance_{datetime.now().strftime('%Y%m%d')}.csv",
                                   mime="text/csv", use_container_width=True)
                try:
                    xbuf = io.BytesIO()
                    with pd.ExcelWriter(xbuf, engine="openpyxl") as writer:
                        exp.to_excel(writer, index=False, sheet_name="财务记录")
                    st.download_button("⬇️ 下载 Excel", data=xbuf.getvalue(),
                                       file_name=f"finance_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                       use_container_width=True)
                except ImportError:
                    st.caption("安装 openpyxl 以支持 Excel 导出")
            else:
                st.info("暂无数据可导出")

# ============================================================
# 钱包初始化向导
# ============================================================
def render_init_wizard():
    t = tc("极光紫")
    st.markdown(f"""
    <div style="max-width:600px;margin:3rem auto;text-align:center">
      <div style="font-size:3rem;margin-bottom:1rem">👋</div>
      <h2 style="color:{t['text']}">欢迎使用 Campus Finance！</h2>
      <p style="opacity:.7">首先，请输入您当前各账户的实际余额。<br>这将帮助系统准确追踪您的资金状况。</p>
    </div>""", unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown('<div class="guide-tip">💡 请如实填写当前各账户余额，填 0 表示该账户暂无余额或不使用。后续随时可在「账户余额」模块修改。</div>', unsafe_allow_html=True)

        init_vals = {}
        for name in WALLET_NAMES:
            icon = WALLET_ICONS.get(name, "💰")
            init_vals[name] = st.number_input(
                f"{icon} {name} 当前余额（元）",
                min_value=0.0, value=0.0, step=10.0,
                key=f"init_{name}"
            )

        total_init = sum(init_vals.values())
        st.markdown(f"""
        <div style="text-align:center;padding:1rem;background:rgba(124,58,237,0.15);
             border-radius:12px;margin:1rem 0">
          <div style="font-size:.82rem;opacity:.7">初始总资产</div>
          <div style="font-size:2rem;font-weight:700;color:#7C3AED">{fmt(total_init)}</div>
        </div>""", unsafe_allow_html=True)

        if st.button("✅ 确认并开始使用", use_container_width=True):
            st.session_state.wallets = init_vals
            save_wallets(init_vals)
            settings = load_settings()
            settings["wallets_initialized"] = True
            save_settings(settings)
            st.session_state.wallets_initialized = True
            st.success("初始化完成！正在进入系统...")
            st.rerun()

# ============================================================
# 侧边栏
# ============================================================
def render_sidebar(settings):
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:1.2rem 0 .8rem">
          <div style="font-size:2.5rem">🎓</div>
          <div style="font-size:1.1rem;font-weight:700;margin:.3rem 0">Campus Finance</div>
          <div style="font-size:.78rem;opacity:.55">大学生财务管理系统</div>
        </div>""", unsafe_allow_html=True)
        st.divider()

        st.markdown("**📅 数据周期**")
        period_opts = ["本月","本周","今日","本学期","全部","自定义"]
        dp = settings.get("default_period","本月")
        if dp not in period_opts: dp = "本月"
        period = st.selectbox("查看时段", period_opts, index=period_opts.index(dp),
                              label_visibility="collapsed")
        custom_start = custom_end = None
        if period == "自定义":
            custom_start = st.date_input("开始", value=date.today()-timedelta(days=30))
            custom_end   = st.date_input("结束", value=date.today())
        st.divider()

        st.markdown("**🎨 主题**")
        theme_keys = list(THEMES.keys())
        cur_theme = settings.get("theme","极光紫")
        if cur_theme not in theme_keys: cur_theme = "极光紫"
        theme = st.selectbox("主题", theme_keys, index=theme_keys.index(cur_theme))
        layout = st.radio("布局", ["宽松","紧凑"],
                          index=["宽松","紧凑"].index(settings.get("layout","宽松")), horizontal=True)
        sort_opts = ["日期降序","日期升序","金额降序","金额升序"]
        cur_sort = settings.get("sort_order","日期降序")
        if cur_sort not in sort_opts: cur_sort = "日期降序"
        sort_order = st.selectbox("排序", sort_opts, index=sort_opts.index(cur_sort))
        st.divider()

        st.markdown("**💰 月度预算（元）**")
        budget = st.number_input("", min_value=0.0,
                                 value=float(settings.get("monthly_budget",2000.0)),
                                 step=100.0, label_visibility="collapsed")
        st.divider()

        st.markdown("**📦 显示模块**")
        sm = settings.get("show_modules",{})
        show_wallets = st.checkbox("账户余额",  value=sm.get("wallets",True))
        show_summary = st.checkbox("统计总览",  value=sm.get("summary",True))
        show_charts  = st.checkbox("可视化图表", value=sm.get("charts",True))
        show_advice  = st.checkbox("资金建议",  value=sm.get("advice",True))
        show_records = st.checkbox("记录管理",  value=sm.get("records",True))
        st.divider()

        st.markdown("**🗄️ 数据操作**")
        if st.button("🔄 加载示例数据", use_container_width=True):
            st.session_state.df = generate_sample_data()
            save_data(st.session_state.df)
            st.success("示例数据已加载！"); st.rerun()
        if st.button("🏁 重置账户初始化", use_container_width=True, type="secondary"):
            st.session_state.wallets_initialized = False
            settings2 = load_settings()
            settings2["wallets_initialized"] = False
            save_settings(settings2)
            st.rerun()
        if st.button("🗑️ 清空所有数据", use_container_width=True, type="secondary"):
            if st.session_state.get("confirm_clear"):
                st.session_state.df = pd.DataFrame(
                    columns=["id","type","category","amount","date","note","payment_method"])
                save_data(st.session_state.df)
                st.session_state.confirm_clear = False; st.rerun()
            else:
                st.session_state.confirm_clear = True
                st.warning("再次点击确认清空！")

        st.markdown('<div style="text-align:center;font-size:.7rem;opacity:.35;padding:.8rem 0">v3.0 · 本地数据存储<br>Made with ❤️ for Students</div>', unsafe_allow_html=True)

    new_settings = {
        "theme": theme, "layout": layout, "default_period": period,
        "sort_order": sort_order, "monthly_budget": budget,
        "show_modules": {"wallets":show_wallets,"summary":show_summary,
                         "charts":show_charts,"advice":show_advice,"records":show_records},
        "wallets_initialized": settings.get("wallets_initialized", False),
    }
    if new_settings != settings:
        save_settings(new_settings)
    return new_settings, period, custom_start, custom_end

# ============================================================
# 主程序
# ============================================================
def main():
    st.set_page_config(
        page_title="Campus Finance · 大学生财务管理",
        page_icon="🎓", layout="wide",
        initial_sidebar_state="expanded"
    )

    settings = load_settings()

    # 加载钱包
    if "wallets" not in st.session_state:
        st.session_state.wallets = load_wallets()
    if "wallets_initialized" not in st.session_state:
        st.session_state.wallets_initialized = settings.get("wallets_initialized", False)

    # 首次使用 → 显示初始化向导
    if not st.session_state.wallets_initialized:
        inject_css(settings.get("theme","极光紫"), settings)
        render_init_wizard()
        return

    # 加载收支数据
    if "df" not in st.session_state:
        df = load_data()
        if df.empty:
            df = generate_sample_data()
            save_data(df)
            st.session_state.first_run = True
        st.session_state.df = df
    df = st.session_state.df

    inject_css(settings["theme"], settings)
    settings, period, custom_start, custom_end = render_sidebar(settings)
    filtered = get_period_df(df, period, custom_start, custom_end)

    # 欢迎横幅
    period_label = period if period != "自定义" else f"{custom_start} ~ {custom_end}"
    total_assets = sum(st.session_state.wallets.values())
    st.markdown(f"""
    <div class="welcome-banner">
      <div style="font-size:.82rem;opacity:.8;margin-bottom:.3rem">欢迎回来 👋</div>
      <div style="font-size:1.8rem;font-weight:900;letter-spacing:-.02em">Campus Finance</div>
      <div style="font-size:.88rem;opacity:.8;margin-top:.4rem">
        {period_label} · {len(filtered)} 条记录 · 总资产 {fmt(total_assets)}
      </div>
    </div>""", unsafe_allow_html=True)

    if st.session_state.pop("first_run", False):
        st.markdown("""<div class="guide-tip">
        🎉 <b>初始化完成！</b>已为您加载示例数据以展示功能。<br>
        ① 在「账户余额」模块查看并随时修改各账户余额<br>
        ② 每次收支都会自动更新对应账户余额<br>
        ③ 侧边栏可切换主题、时段和预算设置
        </div>""", unsafe_allow_html=True)

    sm = settings["show_modules"]

    if sm.get("wallets", True):
        with st.expander("🏦 账户余额", expanded=True):
            render_wallet_panel(settings["theme"])

    if sm.get("summary", True):
        with st.expander("📊 统计总览", expanded=True):
            render_summary_cards(filtered, settings["theme"])

    if sm.get("charts", True):
        with st.expander("📈 可视化图表", expanded=True):
            render_charts(filtered, settings["theme"])

    if sm.get("advice", True):
        with st.expander("💡 实时资金建议", expanded=True):
            render_advice(filtered, settings, settings["theme"])

    if sm.get("records", True):
        with st.expander("📂 收支记录管理", expanded=True):
            render_records_management(df, settings)


if __name__ == "__main__":
    main()