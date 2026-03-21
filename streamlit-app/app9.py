"""
大学生财务管理系统 - Campus Finance Tracker v5.0
运行：streamlit run finance_app.py
依赖：pip install streamlit plotly pandas openpyxl
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json, os, io
from datetime import datetime, timedelta, date
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 常量
# ============================================================
DATA_FILE     = "finance_data.json"
SETTINGS_FILE = "finance_settings.json"
WALLETS_FILE  = "finance_wallets.json"

INCOME_CATEGORIES = ["生活费/家庭", "兼职收入", "奖学金", "转账收入", "其他收入"]
EXPENSE_CATEGORIES = [
    "餐饮伙食", "生活用品", "学习费用", "通讯网络",
    "基础交通", "社交聚餐", "娱乐消费", "服饰鞋包",
    "美妆护理", "医疗应急", "人情往来", "机动备用金", "其他支出"
]
ALL_CATEGORIES = INCOME_CATEGORIES + EXPENSE_CATEGORIES

WALLET_NAMES    = ["微信零钱", "支付宝余额", "银行卡", "现金"]
WALLET_ICONS    = {"微信零钱": "💚", "支付宝余额": "💙", "银行卡": "💳", "现金": "💵"}
PAYMENT_METHODS = WALLET_NAMES

# 支出类别建议占比 (min%, max%) 及必要性等级
CATEGORY_INFO = {
    "餐饮伙食":   {"range": (55, 65), "necessity": "极高", "desc": "生存必需，涵盖三餐、水果、饮用水及日常零食"},
    "生活用品":   {"range": (5,  8),  "necessity": "高",   "desc": "洗漱、洗护、纸巾、洗衣液及基础护肤等"},
    "学习费用":   {"range": (4,  7),  "necessity": "高",   "desc": "教材、打印、文具、网课会员与考证资料等"},
    "通讯网络":   {"range": (2,  3),  "necessity": "高",   "desc": "手机话费、流量及校园网费用"},
    "基础交通":   {"range": (2,  4),  "necessity": "中高", "desc": "公交、地铁及校内通勤，不含频繁打车"},
    "社交聚餐":   {"range": (8, 15),  "necessity": "中",   "desc": "室友聚餐、同学生日、社团聚会及奶茶咖啡等"},
    "娱乐消费":   {"range": (4,  8),  "necessity": "中低", "desc": "电影、游戏充值、视频音乐会员及兴趣支出"},
    "服饰鞋包":   {"range": (3,  8),  "necessity": "中低", "desc": "换季衣物、鞋子购置，不追求品牌消费"},
    "美妆护理":   {"range": (2,  6),  "necessity": "中低", "desc": "彩妆、面膜、护发等用品（以女生为主）"},
    "医疗应急":   {"range": (2,  3),  "necessity": "高",   "desc": "小病买药及应急医疗支出"},
    "人情往来":   {"range": (2,  4),  "necessity": "中低", "desc": "生日红包、节日小礼物等花费"},
    "机动备用金": {"range": (1,  3),  "necessity": "高",   "desc": "应对突发支出，避免整体预算超支"},
    "其他支出":   {"range": (0,  5),  "necessity": "低",   "desc": "其他未分类支出"},
}

NECESSITY_COLOR = {"极高": "#10B981", "高": "#3B82F6", "中高": "#8B5CF6", "中": "#F59E0B", "中低": "#F97316", "低": "#EF4444"}

SPENDING_STYLES = {
    "节俭自律型": {"必需支出": 85, "社交娱乐": 10, "服饰形象": 3, "备用金": 2},
    "正常平衡型": {"必需支出": 75, "社交娱乐": 15, "服饰形象": 6, "备用金": 4},
    "宽松舒适型": {"必需支出": 68, "社交娱乐": 20, "服饰形象": 9, "备用金": 3},
}

THEMES = {
    "极光紫": {"primary":"#7C3AED","secondary":"#A78BFA","accent":"#F59E0B","bg":"#0F0A1E","card":"#1E1535","text":"#F3F0FF","income":"#10B981","expense":"#EF4444","mode":"dark"},
    "珊瑚橙": {"primary":"#EA580C","secondary":"#FB923C","accent":"#0EA5E9","bg":"#1C0F0A","card":"#2D1A10","text":"#FFF7F0","income":"#22C55E","expense":"#F43F5E","mode":"dark"},
    "海洋蓝": {"primary":"#0369A1","secondary":"#38BDF8","accent":"#F97316","bg":"#F0F9FF","card":"#FFFFFF","text":"#0C4A6E","income":"#059669","expense":"#DC2626","mode":"light"},
    "抹茶绿": {"primary":"#15803D","secondary":"#4ADE80","accent":"#A21CAF","bg":"#F0FDF4","card":"#FFFFFF","text":"#14532D","income":"#16A34A","expense":"#B91C1C","mode":"light"},
    "樱花粉": {"primary":"#BE185D","secondary":"#F472B6","accent":"#7C3AED","bg":"#FDF2F8","card":"#FFFFFF","text":"#831843","income":"#0D9488","expense":"#E11D48","mode":"light"},
    "深夜黑": {"primary":"#E2E8F0","secondary":"#94A3B8","accent":"#F59E0B","bg":"#0D1117","card":"#161B22","text":"#E6EDF3","income":"#3FB950","expense":"#F85149","mode":"dark"},
}

# ============================================================
# 持久化
# ============================================================
def load_wallets():
    if os.path.exists(WALLETS_FILE):
        try:
            with open(WALLETS_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: pass
    return {w:0.0 for w in WALLET_NAMES}

def save_wallets(w):
    with open(WALLETS_FILE,"w",encoding="utf-8") as f: json.dump(w,f,ensure_ascii=False,indent=2)

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE,"r",encoding="utf-8") as f: records=json.load(f)
            df=pd.DataFrame(records)
            if not df.empty: df["date"]=pd.to_datetime(df["date"])
            return df
        except Exception as e: st.error(f"数据加载失败:{e}")
    return pd.DataFrame(columns=["id","type","category","amount","date","note","payment_method"])

def save_data(df):
    r=df.copy()
    if not r.empty: r["date"]=r["date"].dt.strftime("%Y-%m-%d")
    with open(DATA_FILE,"w",encoding="utf-8") as f: json.dump(r.to_dict("records"),f,ensure_ascii=False,indent=2)

def load_settings():
    d={"theme":"极光紫","layout":"宽松","default_period":"本月","sort_order":"日期降序",
       "monthly_budget":2000.0,"show_modules":{"summary":True,"wallets":True,"charts":True,"advice":True,"records":True},
       "wallets_initialized":False}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE,"r",encoding="utf-8") as f: saved=json.load(f)
            d.update(saved)
        except: pass
    return d

def save_settings(s):
    with open(SETTINGS_FILE,"w",encoding="utf-8") as f: json.dump(s,f,ensure_ascii=False,indent=2)

# ============================================================
# 辅助
# ============================================================
def get_period_df(df, period, cs=None, ce=None):
    if df.empty: return df
    now=datetime.now()
    if period=="今日": s=now.replace(hour=0,minute=0,second=0); e=now
    elif period=="本周": s=(now-timedelta(days=now.weekday())).replace(hour=0,minute=0,second=0); e=now
    elif period=="本月": s=now.replace(day=1,hour=0,minute=0,second=0); e=now
    elif period=="本学期": s=now-timedelta(days=150); e=now
    elif period=="全部": return df
    elif period=="自定义" and cs and ce: s=pd.Timestamp(cs); e=pd.Timestamp(ce)+timedelta(days=1)
    else: s=now.replace(day=1,hour=0,minute=0,second=0); e=now
    return df[(df["date"]>=pd.Timestamp(s))&(df["date"]<=pd.Timestamp(e))]

def fmt(v): return f"¥{v:,.2f}"
def tc(n): return THEMES.get(n, THEMES["极光紫"])

# ============================================================
# 单条记录的智能建议
# ============================================================
def get_record_advice(row, all_expense_df):
    """针对单条记录生成建议文字"""
    cat = row["category"]
    amount = row["amount"]
    tx_type = row["type"]

    if tx_type == "收入":
        if row["category"] == "兼职收入":
            return f"💪 兼职收入 {fmt(amount)}，建议将 20% 存入备用金账户，剩余合理分配日常支出。"
        elif row["category"] == "奖学金":
            return f"🏆 奖学金 {fmt(amount)}，恭喜！建议优先补充学习费用投入，剩余存入备用金。"
        else:
            return f"✅ 已到账 {fmt(amount)}，请合理规划本期支出，优先保障基础生活需要。"

    info = CATEGORY_INFO.get(cat, {})
    lo, hi = info.get("range", (0, 100))
    necessity = info.get("necessity", "中")
    desc = info.get("desc", "")

    # 计算该类别在总支出中的实际占比
    total_exp = all_expense_df["amount"].sum() if not all_expense_df.empty else 0
    cat_total = all_expense_df[all_expense_df["category"]==cat]["amount"].sum() if not all_expense_df.empty else 0
    ratio = (cat_total / total_exp * 100) if total_exp > 0 else 0

    advice = ""
    if cat == "餐饮伙食":
        if amount > 80: advice = f"⚠️ 本次餐饮消费 {fmt(amount)} 偏高，建议多选食堂，每餐控制在 20 元左右可有效节省。"
        elif amount <= 25: advice = f"👍 本次餐饮 {fmt(amount)}，非常节省！保持这种习惯，食堂是最省钱的选择。"
        else: advice = f"✅ 餐饮消费 {fmt(amount)}，在正常范围内。当前类别占总支出 {ratio:.1f}%（建议 {lo}%～{hi}%）。"
    elif cat == "社交聚餐":
        if amount > 150: advice = f"💡 社交聚餐 {fmt(amount)} 较高，当前占总支出 {ratio:.1f}%。建议控制频率，或选择性价比更高的聚餐方式。"
        else: advice = f"😊 社交聚餐 {fmt(amount)}，维持社交关系是必要的，注意控制频率，建议月度不超过总支出 15%。"
    elif cat == "娱乐消费":
        if ratio > 8: advice = f"🎮 娱乐消费占比已达 {ratio:.1f}%，超出建议上限 8%。可利用图书馆、校园免费活动替代部分付费娱乐。"
        else: advice = f"🎯 娱乐支出 {fmt(amount)}，适度放松有益身心。目前占比 {ratio:.1f}%，在建议范围内。"
    elif cat == "服饰鞋包":
        if amount > 300: advice = f"👗 服饰支出 {fmt(amount)} 较大，建议换季统一购买而非频繁小额消费，注意理性消费。"
        else: advice = f"👕 服饰支出 {fmt(amount)}，在合理范围。注意避免冲动购物，优先选择耐用实用的款式。"
    elif cat == "学习费用":
        advice = f"📚 学习投入 {fmt(amount)}，非常值得！教育是最好的投资，当前学习支出占比 {ratio:.1f}%（建议维持 {lo}%～{hi}%）。"
    elif cat == "医疗应急":
        advice = f"🏥 医疗支出 {fmt(amount)}，身体健康最重要！建议平时注意作息，保持锻炼以减少医疗支出。"
    elif cat == "机动备用金":
        advice = f"💰 备用金 {fmt(amount)}，良好的应急意识！建议始终保持一定备用金余额，应对突发情况。"
    elif cat == "通讯网络":
        advice = f"📱 通讯网络 {fmt(amount)}，属于必要支出。可对比各运营商套餐，选择性价比最高的方案节省费用。"
    elif cat == "基础交通":
        if amount > 100: advice = f"🚌 交通支出 {fmt(amount)} 偏高，建议减少打车次数，优先选择公交地铁出行。"
        else: advice = f"🚇 交通支出 {fmt(amount)}，在合理范围内。坚持公共交通出行是节省的好习惯。"
    elif cat == "美妆护理":
        if ratio > 6: advice = f"💄 美妆护理占比 {ratio:.1f}%，已超出建议上限 6%。建议选择平价替代产品，避免盲目跟风消费。"
        else: advice = f"✨ 美妆护理 {fmt(amount)}，适度即可。优先选择学生党友好的平价产品。"
    elif cat == "人情往来":
        advice = f"🎁 人情往来 {fmt(amount)}，维系感情是必要的。建议控制礼物金额，重在心意而非价格。"
    elif cat == "生活用品":
        advice = f"🛒 生活用品 {fmt(amount)}，属于必要支出。可批量采购节省开支，注意避免过度囤货。"
    else:
        if ratio > 5: advice = f"📋 其他支出占比 {ratio:.1f}%，请关注是否有更合理的分类方式，避免支出模糊化。"
        else: advice = f"📝 支出 {fmt(amount)}，已记录。建议尽量将支出归入具体分类，便于后续分析。"

    return advice

# ============================================================
# CSS 注入
# ============================================================
def inject_css(theme_name, settings):
    t = tc(theme_name)
    pad = "1rem" if settings["layout"] == "紧凑" else "2rem"
    st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&family=Syne:wght@400;600;700;800&display=swap');
.stApp{{background:{t['bg']};color:{t['text']};font-family:'Noto Sans SC',sans-serif;}}
.main .block-container{{padding:{pad};max-width:1400px;}}
h1,h2,h3{{color:{t['text']} !important;font-family:'Syne','Noto Sans SC',sans-serif !important;}}
.metric-card{{background:linear-gradient(135deg,{t['card']},{t['primary']}18);border:1px solid {t['primary']}44;border-radius:20px;padding:1.6rem 1.4rem;text-align:center;}}
.metric-value{{font-size:2rem;font-weight:700;line-height:1.2;font-family:'Syne',monospace;}}
.metric-label{{font-size:0.82rem;opacity:0.65;margin-top:0.3rem;}}
.metric-icon{{font-size:1.8rem;margin-bottom:0.4rem;}}
.wallet-card{{background:{t['card']};border:1px solid {t['primary']}33;border-radius:16px;padding:1.2rem 1.4rem;margin-bottom:0.8rem;display:flex;align-items:center;justify-content:space-between;}}
.wallet-icon{{font-size:1.8rem;margin-right:0.8rem;}}
.wallet-name{{font-size:0.85rem;opacity:0.65;}}
.wallet-amount{{font-size:1.4rem;font-weight:700;color:{t['primary']};font-family:'Syne',monospace;}}
.wallet-total{{background:linear-gradient(135deg,{t['primary']},{t['secondary']});border-radius:16px;padding:1.2rem 1.8rem;color:white;display:flex;align-items:center;justify-content:space-between;margin-bottom:1.2rem;}}
.finance-card{{background:{t['card']};border:1px solid {t['primary']}22;border-radius:16px;padding:1.4rem;margin-bottom:0.9rem;}}
.budget-bar-wrap{{background:{t['primary']}22;border-radius:8px;height:10px;margin:.4rem 0;overflow:hidden;}}
.budget-bar{{height:100%;border-radius:8px;transition:width .6s;}}
.advice-card{{background:{t['card']};border-left:4px solid {t['accent']};border-radius:0 12px 12px 0;padding:.8rem 1rem;margin:.4rem 0;font-size:.88rem;}}
.warning-card{{border-left-color:{t['expense']};}}
.good-card{{border-left-color:{t['income']};}}
.urgent-card{{border-left-color:#FF0000;background:rgba(255,0,0,0.08);}}
.record-row{{background:{t['card']};border:1px solid {t['primary']}22;border-radius:14px;padding:1rem 1.2rem;margin-bottom:.7rem;}}
.record-row-income{{border-left:4px solid {t['income']};}}
.record-row-expense{{border-left:4px solid {t['expense']};}}
.record-advice{{background:{t['primary']}10;border-radius:8px;padding:.6rem .9rem;margin-top:.5rem;font-size:.83rem;color:{t['text']};opacity:.9;}}
.welcome-banner{{background:linear-gradient(135deg,{t['primary']},{t['secondary']},{t['accent']});border-radius:20px;padding:1.8rem 2.4rem;margin-bottom:1.8rem;color:white;position:relative;overflow:hidden;}}
.welcome-banner::after{{content:'💰';position:absolute;right:2rem;top:50%;transform:translateY(-50%);font-size:5rem;opacity:.15;}}
.section-header{{display:flex;align-items:center;gap:.6rem;padding:.8rem 0;border-bottom:2px solid {t['primary']}33;margin-bottom:1.2rem;}}
.section-title{{font-size:1.1rem;font-weight:700;color:{t['text']};}}
.guide-tip{{background:linear-gradient(135deg,{t['primary']}15,{t['accent']}15);border:1px dashed {t['primary']}55;border-radius:14px;padding:1.1rem;margin:.7rem 0;font-size:.88rem;}}
.empty-state{{text-align:center;padding:3rem 1rem;opacity:.55;}}
.empty-icon{{font-size:3rem;margin-bottom:1rem;}}
.cat-tag{{display:inline-block;padding:.2rem .6rem;border-radius:6px;font-size:.78rem;font-weight:600;margin-right:.4rem;}}
.stSelectbox>div>div,.stTextInput>div>div>input,.stNumberInput>div>div>input,.stDateInput>div>div>input,.stTextArea>div>div>textarea{{background:{t['card']} !important;color:{t['text']} !important;border:1px solid {t['primary']}44 !important;border-radius:10px !important;}}
.stButton>button{{background:linear-gradient(135deg,{t['primary']},{t['secondary']}) !important;color:white !important;border:none !important;border-radius:10px !important;font-weight:600 !important;}}
.stSidebar{{background:{t['card']} !important;}}
.stTabs [data-baseweb="tab-list"]{{gap:8px;background:{t['card']};padding:8px;border-radius:14px;}}
.stTabs [data-baseweb="tab"]{{background:transparent;color:{t['text']}99;border-radius:10px;padding:.45rem 1rem;font-weight:500;}}
.stTabs [aria-selected="true"]{{background:{t['primary']} !important;color:white !important;}}
::-webkit-scrollbar{{width:6px;}}::-webkit-scrollbar-track{{background:{t['bg']};}}::-webkit-scrollbar-thumb{{background:{t['primary']}66;border-radius:3px;}}
</style>""", unsafe_allow_html=True)

# ============================================================
# Plotly 布局 — 使用 **kwargs 展开，完全兼容新版
# ============================================================
def apply_layout(fig, t, title_text="", extra=None):
    """通过 **kwargs 方式传递布局，彻底解决嵌套对象兼容问题"""
    kwargs = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=16, r=16, t=48 if title_text else 24, b=16),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    )
    if title_text:
        kwargs["title"] = dict(text=title_text, font=dict(color=t["text"], size=16), x=0.02, xanchor="left")
    if extra:
        kwargs.update(extra)
    # 始终用 **kwargs 展开调用，避免 dict 传参的版本差异
    fig.update_layout(**kwargs)
    # 单独设置 font，避免与其他参数冲突
    fig.update_layout(font=dict(color=t["text"], family="Noto Sans SC, sans-serif", size=13))
    return fig

# ============================================================
# 钱包面板
# ============================================================
def render_wallet_panel(theme_name):
    t = tc(theme_name)
    wallets = st.session_state.wallets
    total = sum(wallets.values())
    st.markdown(f"""<div class="wallet-total">
      <div><div style="font-size:.82rem;opacity:.85">💰 当前总资产</div>
      <div style="font-size:2rem;font-weight:900;font-family:'Syne',monospace">{fmt(total)}</div></div>
      <div style="font-size:2.5rem;opacity:.4">🏦</div></div>""", unsafe_allow_html=True)

    cols = st.columns(2)
    for i, (name, amount) in enumerate(wallets.items()):
        icon = WALLET_ICONS.get(name, "💰")
        with cols[i%2]:
            st.markdown(f"""<div class="wallet-card">
              <div style="display:flex;align-items:center"><span class="wallet-icon">{icon}</span><span class="wallet-name">{name}</span></div>
              <span class="wallet-amount">{fmt(amount)}</span></div>""", unsafe_allow_html=True)

    with st.expander("✏️ 修改账户余额", expanded=False):
        st.markdown('<div class="guide-tip">💡 充值/提现/转账等账外变动时，直接更新余额。系统自动记录差额。</div>', unsafe_allow_html=True)
        edit_cols = st.columns(2)
        new_vals = {}
        for i, name in enumerate(WALLET_NAMES):
            with edit_cols[i%2]:
                new_vals[name] = st.number_input(f"{WALLET_ICONS.get(name,'')} {name}（元）",
                    min_value=0.0, value=float(wallets.get(name,0.0)), step=1.0, key=f"wallet_edit_{name}")
        if st.button("💾 保存余额", use_container_width=True, key="save_wallets"):
            diff = sum(new_vals.values()) - sum(st.session_state.wallets.values())
            st.session_state.wallets = new_vals
            save_wallets(new_vals)
            if abs(diff) > 0.01:
                adj_row = pd.DataFrame([{"id":f"adj_{int(datetime.now().timestamp()*1000)}",
                    "type":"收入" if diff>0 else "支出",
                    "category":"其他收入" if diff>0 else "其他支出",
                    "amount":round(abs(diff),2),"date":pd.Timestamp(date.today()),
                    "note":"余额手动调整","payment_method":"银行卡"}])
                st.session_state.df = pd.concat([st.session_state.df, adj_row], ignore_index=True)
                save_data(st.session_state.df)
            st.success(f"✅ 余额已更新！总资产：{fmt(sum(new_vals.values()))}")
            st.rerun()

# ============================================================
# 统计总览
# ============================================================
def render_summary_cards(df, theme_name):
    t = tc(theme_name)
    income  = df[df["type"]=="收入"]["amount"].sum()
    expense = df[df["type"]=="支出"]["amount"].sum()
    balance = income - expense
    bcol = t["income"] if balance>=0 else t["expense"]
    total_assets = sum(st.session_state.wallets.values())
    c1,c2,c3,c4 = st.columns(4)
    for col,icon,val,color,label in [
        (c1,"📥",fmt(income),t["income"],"期间收入"),
        (c2,"📤",fmt(expense),t["expense"],"期间支出"),
        (c3,"💰",(("+" if balance>=0 else "")+fmt(balance)),bcol,"期间结余"),
        (c4,"🏦",fmt(total_assets),t["primary"],"当前总资产"),
    ]:
        col.markdown(f"""<div class="metric-card">
          <div class="metric-icon">{icon}</div>
          <div class="metric-value" style="color:{color}">{val}</div>
          <div class="metric-label">{label}</div></div>""", unsafe_allow_html=True)

# ============================================================
# 图表 — 用 apply_layout() 彻底修复 Plotly 兼容性
# ============================================================
def render_charts(df, theme_name):
    t = tc(theme_name)
    template = "plotly_dark" if t["mode"]=="dark" else "plotly_white"
    exp_df = df[df["type"]=="支出"]
    grid = t["primary"]+"22"

    tab1,tab2,tab3,tab4,tab5 = st.tabs(["🥧 支出分布","📊 月度对比","📈 趋势变化","🗓️ 消费频次","🎯 消费结构"])

    with tab1:
        if exp_df.empty:
            st.markdown('<div class="empty-state"><div class="empty-icon">📊</div><p>暂无支出数据</p></div>', unsafe_allow_html=True)
        else:
            cat_sum = exp_df.groupby("category")["amount"].sum().reset_index()
            fig = px.pie(cat_sum, values="amount", names="category", hole=.42,
                         color_discrete_sequence=px.colors.qualitative.Set3, template=template)
            fig.update_traces(textposition="outside", textinfo="percent+label",
                              hovertemplate="<b>%{label}</b><br>¥%{value:.2f} · %{percent}<extra></extra>")
            apply_layout(fig, t, "支出类别占比")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if df.empty:
            st.markdown('<div class="empty-state"><div class="empty-icon">📊</div><p>暂无数据</p></div>', unsafe_allow_html=True)
        else:
            dc = df.copy()
            dc["month"] = dc["date"].dt.to_period("M").astype(str)
            monthly = dc.groupby(["month","type"])["amount"].sum().reset_index()
            fig = px.bar(monthly, x="month", y="amount", color="type", barmode="group",
                         color_discrete_map={"收入":t["income"],"支出":t["expense"]},
                         template=template, text_auto=".0f")
            fig.update_traces(hovertemplate="<b>%{x}</b><br>¥%{y:.2f}<extra></extra>", marker_line_width=0)
            apply_layout(fig, t, "月度收支对比",
                         extra=dict(xaxis=dict(gridcolor=grid), yaxis=dict(gridcolor=grid)))
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        if df.empty:
            st.markdown('<div class="empty-state"><div class="empty-icon">📈</div><p>暂无数据</p></div>', unsafe_allow_html=True)
        else:
            dc = df.copy()
            dc["week"] = dc["date"].dt.to_period("W").apply(lambda r: r.start_time)
            weekly = dc.groupby(["week","type"])["amount"].sum().reset_index()
            fig = go.Figure()
            for tp, color in [("收入",t["income"]),("支出",t["expense"])]:
                sub = weekly[weekly["type"]==tp]
                if sub.empty: continue
                fig.add_trace(go.Scatter(x=sub["week"], y=sub["amount"], name=tp,
                    mode="lines+markers", line=dict(color=color, width=2.5, shape="spline"),
                    marker=dict(size=7, color=color), fill="tozeroy", fillcolor=color+"22",
                    hovertemplate="<b>%{x|%Y-%m-%d}</b><br>¥%{y:.2f}<extra></extra>"))
            apply_layout(fig, t, "周度收支趋势",
                         extra=dict(xaxis=dict(gridcolor=grid), yaxis=dict(gridcolor=grid)))
            st.plotly_chart(fig, use_container_width=True)

    with tab4:
        if exp_df.empty:
            st.markdown('<div class="empty-state"><div class="empty-icon">🗓️</div><p>暂无支出数据</p></div>', unsafe_allow_html=True)
        else:
            dc = exp_df.copy()
            dc["dow"] = dc["date"].dt.dayofweek
            counts = dc.groupby("dow").size().reindex(range(7), fill_value=0)
            days_cn = ["周一","周二","周三","周四","周五","周六","周日"]
            fig = go.Figure(go.Bar(x=days_cn, y=counts.values,
                marker_color=[t["primary"]]*5+[t["accent"]]*2,
                text=counts.values, textposition="outside",
                hovertemplate="<b>%{x}</b><br>消费%{y}次<extra></extra>"))
            apply_layout(fig, t, "各星期消费频次",
                         extra=dict(xaxis=dict(gridcolor="rgba(0,0,0,0)"), yaxis=dict(gridcolor=grid)))
            st.plotly_chart(fig, use_container_width=True)

    with tab5:
        if exp_df.empty:
            st.markdown('<div class="empty-state"><div class="empty-icon">🎯</div><p>暂无支出数据</p></div>', unsafe_allow_html=True)
        else:
            total_exp = exp_df["amount"].sum()
            cat_sum = exp_df.groupby("category")["amount"].sum()
            rows = []
            for cat, info in CATEGORY_INFO.items():
                actual = cat_sum.get(cat, 0)
                ar = (actual/total_exp*100) if total_exp>0 else 0
                lo, hi = info["range"]
                status = "✅ 合理" if lo<=ar<=hi else ("⚠️ 偏高" if ar>hi else ("📉 偏低" if ar>0 else "—"))
                rows.append({"类别":cat, "实际占比":f"{ar:.1f}%", "建议区间":f"{lo}%～{hi}%",
                             "必要性":info["necessity"], "状态":status, "金额":fmt(actual)})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("**三种消费风格参考**")
            style_cols = st.columns(3)
            for i, (style, ratios) in enumerate(SPENDING_STYLES.items()):
                with style_cols[i]:
                    st.markdown(f"**{style}**")
                    for k, v in ratios.items():
                        st.markdown(f"- {k}：{v}%")

# ============================================================
# 资金建议（总体）
# ============================================================
def render_advice(df, settings, theme_name):
    t = tc(theme_name)
    wallets = st.session_state.wallets
    total_assets = sum(wallets.values())
    exp_df = df[df["type"]=="支出"]
    budget = settings.get("monthly_budget", 2000.0)

    st.markdown('<div class="section-header"><span>🏦</span><span class="section-title">资产健康状态</span></div>', unsafe_allow_html=True)
    if total_assets < 200:
        st.markdown(f'<div class="advice-card urgent-card">🚨 <b>紧急预警</b>：当前总资产仅 {fmt(total_assets)}！建议立即联系家人补充生活费，减少一切非必要支出。</div>', unsafe_allow_html=True)
    elif total_assets < 500:
        st.markdown(f'<div class="advice-card warning-card">⚠️ <b>余额偏低</b>：当前总资产 {fmt(total_assets)}，建议控制消费，优先保障餐饮和交通。</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="advice-card good-card">✅ <b>资产良好</b>：当前总资产 {fmt(total_assets)}，继续保持理性消费。</div>', unsafe_allow_html=True)

    for name, amount in wallets.items():
        if 0 < amount < 50:
            st.markdown(f'<div class="advice-card warning-card">💡 <b>{name}</b> 余额仅 {fmt(amount)}，建议及时充值。</div>', unsafe_allow_html=True)

    if not exp_df.empty:
        st.markdown('<div class="section-header" style="margin-top:1.5rem"><span>💡</span><span class="section-title">本月预算监控</span></div>', unsafe_allow_html=True)
        total_exp = exp_df["amount"].sum()
        ratio = (total_exp / budget * 100) if budget > 0 else 0
        bar_c = t["income"] if ratio<80 else (t["accent"] if ratio<100 else t["expense"])
        st.markdown(f"""<div class="finance-card">
          <div style="display:flex;justify-content:space-between;margin-bottom:.5rem">
            <span>月度预算执行</span><span style="color:{bar_c};font-weight:700">{ratio:.1f}%</span></div>
          <div class="budget-bar-wrap"><div class="budget-bar" style="width:{min(ratio,100):.1f}%;background:{bar_c}"></div></div>
          <div style="display:flex;justify-content:space-between;font-size:.8rem;opacity:.65;margin-top:.4rem">
            <span>已支出 {fmt(total_exp)}</span><span>预算 {fmt(budget)}</span></div></div>""", unsafe_allow_html=True)
        if ratio>=100: st.error(f"⚠️ 已超预算 {fmt(total_exp-budget)}！请立即控制消费。")
        elif ratio>=80: st.warning(f"⚡ 预算已用 {ratio:.1f}%，剩余 {fmt(budget-total_exp)}，注意节省。")
        else: st.success(f"✅ 预算执行良好！剩余 {fmt(budget-total_exp)}")

        st.markdown('<div class="section-header" style="margin-top:1.5rem"><span>📊</span><span class="section-title">消费结构分析</span></div>', unsafe_allow_html=True)
        cat_expense = exp_df.groupby("category")["amount"].sum()
        for cat, info in CATEGORY_INFO.items():
            lo, hi = info["range"]
            actual = cat_expense.get(cat, 0)
            ar = (actual/total_exp*100) if total_exp>0 else 0
            if ar > hi:
                st.markdown(f'<div class="advice-card warning-card">⚠️ <b>{cat}</b> 占比 {ar:.1f}%，超出建议上限 {hi}%，建议适当减少。</div>', unsafe_allow_html=True)
            elif lo<=ar<=hi and actual>0:
                st.markdown(f'<div class="advice-card good-card">✅ <b>{cat}</b> 支出占比 {ar:.1f}%，处于合理区间 {lo}%～{hi}%。</div>', unsafe_allow_html=True)

    # 日均建议
    st.markdown('<div class="section-header" style="margin-top:1.5rem"><span>🎯</span><span class="section-title">实时消费建议</span></div>', unsafe_allow_html=True)
    tips = []
    if total_assets > 0:
        days_left = max(1, 30 - datetime.now().day + 1)
        daily = total_assets / days_left
        tips.append(f"📅 当前总资产 {fmt(total_assets)}，月底还有 {days_left} 天，日均可用 {fmt(daily)}。")
        if daily < 30: tips.append("🍱 日均预算偏低，建议以食堂为主，暂停娱乐和购物消费。")
        elif daily < 60: tips.append("🎯 预算适中，建议餐饮控制在 40 元/天以内，减少冲动消费。")
        else: tips.append("💪 日均预算充足，建议保留 20% 作为应急储备。")

    if not tips:
        tips.append("💡 记录更多收支数据后，系统将生成更精准的个性化建议。")
    for tip in tips:
        st.markdown(f'<div class="advice-card">{tip}</div>', unsafe_allow_html=True)

# ============================================================
# 记录管理 — 带逐条建议
# ============================================================
def render_records_management(df, settings, theme_name):
    t = tc(theme_name)
    tab1, tab2, tab3 = st.tabs(["➕ 新增记录", "📝 查看记录（含建议）", "📤 导入/导出"])

    with tab1:
        st.markdown('<div class="guide-tip">💡 每笔收支都会自动更新对应账户余额，并即时生成消费建议。</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            tx_type = st.selectbox("类型 *", ["支出","收入"], key="a_type")
            cats = EXPENSE_CATEGORIES if tx_type=="支出" else INCOME_CATEGORIES
            cat = st.selectbox("类别 *", cats, key="a_cat")
            amount = st.number_input("金额（元）*", min_value=0.01, value=10.0, step=0.01, key="a_amt")
        with c2:
            tx_date = st.date_input("日期 *", value=date.today(), key="a_date")
            payment = st.selectbox("支付账户 *", PAYMENT_METHODS, key="a_pay")
            note = st.text_input("备注（可选）", placeholder="如：食堂午饭、购买教材...", key="a_note")

        # 预览建议
        if tx_type == "支出" and cat in CATEGORY_INFO:
            info = CATEGORY_INFO[cat]
            nc = NECESSITY_COLOR.get(info["necessity"], "#888")
            st.markdown(f"""<div class="guide-tip">
              <b>{cat}</b> — 必要性：<span style="color:{nc};font-weight:700">{info['necessity']}</span><br>
              {info['desc']}<br>建议占月支出 <b>{info['range'][0]}%～{info['range'][1]}%</b>
            </div>""", unsafe_allow_html=True)

        if st.button("💾 保存记录", use_container_width=True):
            wallets = st.session_state.wallets.copy()
            if tx_type=="支出":
                if wallets.get(payment,0) < amount:
                    st.warning(f"⚠️ {payment} 余额不足（当前 {fmt(wallets.get(payment,0))}），记录已保存，请注意补充。")
                wallets[payment] = max(0.0, wallets.get(payment,0) - amount)
            else:
                wallets[payment] = wallets.get(payment,0) + amount
            st.session_state.wallets = wallets
            save_wallets(wallets)

            new_row = pd.DataFrame([{"id":str(int(datetime.now().timestamp()*1000)),
                "type":tx_type,"category":cat,"amount":round(amount,2),
                "date":pd.Timestamp(tx_date),"note":note,"payment_method":payment}])
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            save_data(st.session_state.df)

            # 生成即时建议
            exp_all = st.session_state.df[st.session_state.df["type"]=="支出"]
            advice_text = get_record_advice(new_row.iloc[0], exp_all)
            st.success(f"✅ 已保存：{tx_type} · {cat} · {fmt(amount)}  →  {payment} 余额：{fmt(wallets[payment])}")
            st.info(f"💡 **消费建议：** {advice_text}")
            st.rerun()

    with tab2:
        if df.empty:
            st.markdown('<div class="empty-state"><div class="empty-icon">📝</div><p>还没有任何记录，前往「新增记录」添加第一笔数据</p></div>', unsafe_allow_html=True)
            return

        with st.expander("🔍 筛选条件", expanded=False):
            fa, fb, fc = st.columns(3)
            with fa: f_type = st.multiselect("类型", ["收入","支出"], default=["收入","支出"])
            with fb: f_cat  = st.multiselect("类别", ALL_CATEGORIES, default=[])
            with fc:
                amt_min = st.number_input("最低金额", value=0.0, step=1.0)
                amt_max = st.number_input("最高金额", value=99999.0, step=1.0)
            dr = st.date_input("日期范围", value=(df["date"].min().date(), df["date"].max().date()))

        filt = df[df["type"].isin(f_type or ["收入","支出"])]
        if f_cat: filt = filt[filt["category"].isin(f_cat)]
        filt = filt[(filt["amount"]>=amt_min)&(filt["amount"]<=amt_max)]
        if len(dr)==2:
            filt = filt[(filt["date"]>=pd.Timestamp(dr[0]))&(filt["date"]<=pd.Timestamp(dr[1])+timedelta(days=1))]

        sort_map={"日期降序":("date",False),"日期升序":("date",True),"金额降序":("amount",False),"金额升序":("amount",True)}
        sc, asc = sort_map.get(settings["sort_order"],("date",False))
        filt = filt.sort_values(sc, ascending=asc)

        exp_all = df[df["type"]=="支出"]
        st.caption(f"共 {len(filt)} 条记录")

        # 逐条渲染（含建议）
        for _, row in filt.iterrows():
            is_income = row["type"]=="收入"
            row_class = "record-row-income" if is_income else "record-row-expense"
            color = t["income"] if is_income else t["expense"]
            sign = "+" if is_income else "-"
            advice_text = get_record_advice(row, exp_all)
            date_str = row["date"].strftime("%Y-%m-%d") if hasattr(row["date"],"strftime") else str(row["date"])
            note_html = f'<span style="opacity:.55;font-size:.8rem"> · {row["note"]}</span>' if row["note"] else ""

            st.markdown(f"""<div class="record-row {row_class}">
              <div style="display:flex;justify-content:space-between;align-items:flex-start">
                <div>
                  <span class="cat-tag" style="background:{color}22;color:{color}">{row['category']}</span>
                  <span style="font-size:.82rem;opacity:.6">{date_str}</span>
                  {note_html}
                  <span style="font-size:.8rem;opacity:.5;margin-left:.4rem">via {row['payment_method']}</span>
                </div>
                <div style="font-size:1.2rem;font-weight:700;color:{color};font-family:'Syne',monospace">
                  {sign}{fmt(row['amount'])}
                </div>
              </div>
              <div class="record-advice">💡 {advice_text}</div>
            </div>""", unsafe_allow_html=True)

        # 删除记录
        st.markdown("---")
        del_id = st.text_input("输入要删除的行号（从 0 开始，按上方显示顺序）", placeholder="如: 0", key="del_idx")
        if st.button("🗑️ 删除该记录", type="secondary"):
            try:
                idx = int(del_id)
                filt_list = filt.reset_index(drop=True)
                if 0 <= idx < len(filt_list):
                    row = filt_list.iloc[idx]
                    wallets = st.session_state.wallets.copy()
                    pm = row["payment_method"]
                    if pm in wallets:
                        wallets[pm] = (wallets[pm]+row["amount"]) if row["type"]=="支出" else max(0.0, wallets[pm]-row["amount"])
                        st.session_state.wallets = wallets
                        save_wallets(wallets)
                    st.session_state.df = st.session_state.df[st.session_state.df["id"]!=row["id"]]
                    save_data(st.session_state.df)
                    st.success("记录已删除，账户余额已同步更新")
                    st.rerun()
                else:
                    st.error("序号超出范围")
            except ValueError:
                st.error("请输入有效数字")

    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📥 导入 CSV**")
            up = st.file_uploader("上传 CSV", type=["csv"])
            if up:
                try:
                    imp = pd.read_csv(up).rename(columns={"类型":"type","类别":"category","金额(元)":"amount","日期":"date","备注":"note","支付账户":"payment_method"})
                    imp["date"] = pd.to_datetime(imp["date"])
                    imp["id"] = [f"imp_{i}" for i in range(len(imp))]
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
                exp = exp.rename(columns={"type":"类型","category":"类别","amount":"金额(元)","date":"日期","note":"备注","payment_method":"支付账户"})
                exp = exp[["日期","类型","类别","金额(元)","支付账户","备注"]]
                buf = io.StringIO(); exp.to_csv(buf, index=False, encoding="utf-8-sig")
                st.download_button("⬇️ 下载 CSV", data=buf.getvalue().encode("utf-8-sig"),
                    file_name=f"finance_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
                try:
                    xbuf = io.BytesIO()
                    with pd.ExcelWriter(xbuf, engine="openpyxl") as writer:
                        exp.to_excel(writer, index=False, sheet_name="财务记录")
                    st.download_button("⬇️ 下载 Excel", data=xbuf.getvalue(),
                        file_name=f"finance_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                except ImportError:
                    st.caption("安装 openpyxl 以支持 Excel 导出")
            else:
                st.info("暂无数据可导出")

# ============================================================
# 初始化向导
# ============================================================
def render_init_wizard():
    t = tc("极光紫")
    st.markdown(f"""<div style="max-width:600px;margin:3rem auto;text-align:center">
      <div style="font-size:3rem;margin-bottom:1rem">👋</div>
      <h2 style="color:{t['text']}">欢迎使用 Campus Finance！</h2>
      <p style="opacity:.7">首先，请输入您当前各账户的实际余额。<br>这是系统的起点，后续所有收支通过手动录入追踪，每条记录都会生成个性化建议。</p>
    </div>""", unsafe_allow_html=True)

    _, mid, _ = st.columns([1,2,1])
    with mid:
        st.markdown('<div class="guide-tip">💡 如实填写当前各账户余额，填 0 表示该账户暂无余额或不使用。</div>', unsafe_allow_html=True)
        init_vals = {}
        for name in WALLET_NAMES:
            icon = WALLET_ICONS.get(name, "💰")
            init_vals[name] = st.number_input(f"{icon} {name} 当前余额（元）",
                min_value=0.0, value=0.0, step=10.0, key=f"init_{name}")
        total_init = sum(init_vals.values())
        st.markdown(f"""<div style="text-align:center;padding:1rem;background:rgba(124,58,237,0.15);border-radius:12px;margin:1rem 0">
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
            st.session_state.df = pd.DataFrame(columns=["id","type","category","amount","date","note","payment_method"])
            save_data(st.session_state.df)
            st.success("初始化完成！正在进入系统...")
            st.rerun()

# ============================================================
# 侧边栏
# ============================================================
def render_sidebar(settings):
    with st.sidebar:
        st.markdown("""<div style="text-align:center;padding:1.2rem 0 .8rem">
          <div style="font-size:2.5rem">🎓</div>
          <div style="font-size:1.1rem;font-weight:700;margin:.3rem 0">Campus Finance</div>
          <div style="font-size:.78rem;opacity:.55">大学生财务管理系统</div>
        </div>""", unsafe_allow_html=True)
        st.divider()

        st.markdown("**📅 数据周期**")
        period_opts = ["本月","本周","今日","本学期","全部","自定义"]
        dp = settings.get("default_period","本月")
        if dp not in period_opts: dp = "本月"
        period = st.selectbox("查看时段", period_opts, index=period_opts.index(dp), label_visibility="collapsed")
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
        layout = st.radio("布局", ["宽松","紧凑"], index=["宽松","紧凑"].index(settings.get("layout","宽松")), horizontal=True)
        sort_opts = ["日期降序","日期升序","金额降序","金额升序"]
        cur_sort = settings.get("sort_order","日期降序")
        if cur_sort not in sort_opts: cur_sort = "日期降序"
        sort_order = st.selectbox("记录排序", sort_opts, index=sort_opts.index(cur_sort))
        st.divider()

        st.markdown("**💰 月度预算（元）**")
        budget = st.number_input("", min_value=0.0, value=float(settings.get("monthly_budget",2000.0)), step=100.0, label_visibility="collapsed")
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
        if st.button("🏁 重置账户初始化", use_container_width=True, type="secondary"):
            st.session_state.wallets_initialized = False
            s2=load_settings(); s2["wallets_initialized"]=False; save_settings(s2); st.rerun()
        if st.button("🗑️ 清空所有记录", use_container_width=True, type="secondary"):
            if st.session_state.get("confirm_clear"):
                st.session_state.df = pd.DataFrame(columns=["id","type","category","amount","date","note","payment_method"])
                save_data(st.session_state.df)
                st.session_state.confirm_clear = False; st.rerun()
            else:
                st.session_state.confirm_clear = True
                st.warning("再次点击确认清空！")

        st.markdown('<div style="text-align:center;font-size:.7rem;opacity:.35;padding:.8rem 0">v5.0 · 本地数据存储<br>Made with ❤️ for Students</div>', unsafe_allow_html=True)

    new_settings = {
        "theme":theme,"layout":layout,"default_period":period,"sort_order":sort_order,"monthly_budget":budget,
        "show_modules":{"wallets":show_wallets,"summary":show_summary,"charts":show_charts,"advice":show_advice,"records":show_records},
        "wallets_initialized":settings.get("wallets_initialized",False),
    }
    if new_settings != settings: save_settings(new_settings)
    return new_settings, period, custom_start, custom_end

# ============================================================
# 主程序
# ============================================================
def main():
    st.set_page_config(page_title="Campus Finance · 大学生财务管理",
                       page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

    settings = load_settings()

    if "wallets" not in st.session_state:
        st.session_state.wallets = load_wallets()
    if "wallets_initialized" not in st.session_state:
        st.session_state.wallets_initialized = settings.get("wallets_initialized", False)

    if not st.session_state.wallets_initialized:
        inject_css(settings.get("theme","极光紫"), settings)
        render_init_wizard()
        return

    if "df" not in st.session_state:
        st.session_state.df = load_data()
    df = st.session_state.df

    inject_css(settings["theme"], settings)
    settings, period, custom_start, custom_end = render_sidebar(settings)
    filtered = get_period_df(df, period, custom_start, custom_end)

    period_label = period if period!="自定义" else f"{custom_start} ~ {custom_end}"
    total_assets = sum(st.session_state.wallets.values())
    st.markdown(f"""<div class="welcome-banner">
      <div style="font-size:.82rem;opacity:.8;margin-bottom:.3rem">欢迎回来 👋</div>
      <div style="font-size:1.8rem;font-weight:900;letter-spacing:-.02em">Campus Finance</div>
      <div style="font-size:.88rem;opacity:.8;margin-top:.4rem">
        {period_label} · {len(filtered)} 条记录 · 总资产 {fmt(total_assets)}
      </div></div>""", unsafe_allow_html=True)

    if df.empty:
        st.markdown("""<div class="guide-tip">🎉 <b>系统已就绪！</b><br>
        ① 在下方「收支记录管理」→「新增记录」开始记录每笔收支<br>
        ② 每笔记录会自动更新账户余额并生成个性化消费建议<br>
        ③ 积累数据后，图表和统计模块将自动显示分析结果</div>""", unsafe_allow_html=True)

    sm = settings["show_modules"]

    if sm.get("wallets",True):
        with st.expander("🏦 账户余额", expanded=True):
            render_wallet_panel(settings["theme"])

    if sm.get("summary",True):
        with st.expander("📊 统计总览", expanded=True):
            render_summary_cards(filtered, settings["theme"])

    if sm.get("charts",True):
        with st.expander("📈 可视化图表", expanded=not df.empty):
            if df.empty:
                st.markdown('<div class="empty-state"><div class="empty-icon">📈</div><p>添加收支记录后，图表将在此处显示</p></div>', unsafe_allow_html=True)
            else:
                render_charts(filtered, settings["theme"])

    if sm.get("advice",True):
        with st.expander("💡 整体资金建议", expanded=True):
            render_advice(filtered, settings, settings["theme"])

    if sm.get("records",True):
        with st.expander("📂 收支记录管理", expanded=True):
            render_records_management(df, settings, settings["theme"])


if __name__ == "__main__":
    main()