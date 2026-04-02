"""
大学生财务管理系统 - Campus Finance Tracker v9.2
修复：登录/注册 if submitted 移入 with st.form 块内，解决已注册账号无法登录的问题
运行：streamlit run finance_app.py
依赖：pip install streamlit plotly pandas openpyxl
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json, os, io, hashlib
from datetime import datetime, timedelta, date
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 常量 & 文件路径
# ============================================================
DATA_FILE      = "finance_data.json"
SETTINGS_FILE  = "finance_settings.json"
WALLETS_FILE   = "finance_wallets.json"
AUTH_FILE      = "finance_auth.json"

# ============================================================
# 颜色工具：将 #RRGGBB + 0-1 透明度 转为 rgba()
# ============================================================
def hex_alpha(hex6: str, alpha: float) -> str:
    h = hex6.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"

# ============================================================
# 认证系统
# ============================================================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def load_auth() -> dict:
    if os.path.exists(AUTH_FILE):
        try:
            with open(AUTH_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, PermissionError, UnicodeDecodeError):
            pass
    return {}

def save_auth(auth: dict):
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(auth, f, ensure_ascii=False, indent=2)

def verify_password(username: str, password: str) -> bool:
    auth = load_auth()
    if username not in auth:
        return False
    return auth[username]["password_hash"] == hash_password(password)

def register_user(username: str, password: str, display_name: str = "") -> bool:
    auth = load_auth()
    if username in auth:
        return False
    auth[username] = {
        "password_hash": hash_password(password),
        "display_name": display_name or username,
        "created_at": datetime.now().isoformat(),
    }
    save_auth(auth)
    return True

def get_display_name(username: str) -> str:
    auth = load_auth()
    return auth.get(username, {}).get("display_name", username)

def change_password(username: str, old_pw: str, new_pw: str) -> bool:
    if not verify_password(username, old_pw):
        return False
    auth = load_auth()
    auth[username]["password_hash"] = hash_password(new_pw)
    save_auth(auth)
    return True

# ============================================================
# 分类体系
# ============================================================
INCOME_CATEGORIES = ["生活费/家庭", "兼职收入", "奖学金", "转账收入", "其他收入"]

EXPENSE_STRUCTURE = {
    "餐饮消费": {
        "食堂正餐":     {"priority": 1, "desc": "早餐、午餐、晚餐、面食、小碗菜、套餐"},
        "校内简餐":     {"priority": 2, "desc": "手抓饼、烤肠、饭团、煎饼、卤味、小吃窗口"},
        "校内水饮":     {"priority": 1, "desc": "瓶装水、豆浆、酸梅汤、绿豆汤、平价饮料"},
        "平价快餐":     {"priority": 2, "desc": "黄焖鸡、烤肉饭、沙县小吃、兰州拉面、煲仔饭"},
        "街头小吃":     {"priority": 3, "desc": "炸串、烤冷面、烤串、炸鸡、汉堡、卤味"},
        "奶茶咖啡":     {"priority": 3, "desc": "奶茶、果茶、咖啡、各类茶饮、酸奶饮品"},
        "正餐外卖":     {"priority": 2, "desc": "米饭套餐、盖饭、炒菜、轻食沙拉、粥粉面"},
        "夜宵外卖":     {"priority": 4, "desc": "烧烤、炸鸡、麻辣烫、卤味、甜品、速食"},
        "饮品外卖":     {"priority": 3, "desc": "奶茶、果茶、水果切、酸奶捞、各类外卖饮品"},
        "朋友小聚":     {"priority": 3, "desc": "火锅、烤肉、串串、鸡公煲、烤鱼"},
        "生日节日聚餐": {"priority": 4, "desc": "生日蛋糕、中档餐厅、包厢消费"},
        "班级社团团建": {"priority": 4, "desc": "自助餐、集体点餐、轰趴、户外烧烤"},
        "水果":         {"priority": 2, "desc": "新鲜水果、水果切盒、水果捞"},
        "零食囤货":     {"priority": 3, "desc": "薯片、辣条、饼干、巧克力、肉干、坚果"},
        "宿舍自炊":     {"priority": 4, "desc": "泡面、自热火锅、挂面、鸡蛋、蔬菜"},
    },
    "生活日用": {
        "洗漱用品":     {"priority": 1, "desc": "洗发水、沐浴露、牙膏、牙刷、洗面奶"},
        "清洁用品":     {"priority": 1, "desc": "洗衣液、纸巾、湿巾、垃圾袋、洗洁精"},
        "护肤美妆":     {"priority": 2, "desc": "基础护肤品、面膜、彩妆、卸妆产品"},
        "宿舍生活用品": {"priority": 1, "desc": "水杯、毛巾、衣架、收纳盒、雨伞、拖鞋"},
        "电子耗材":     {"priority": 1, "desc": "插排、台灯、充电宝、电池、数据线"},
        "季节用品":     {"priority": 2, "desc": "风扇、暖手宝、防晒、棉被、凉席、口罩"},
        "日常衣物":     {"priority": 2, "desc": "T恤、裤子、外套、内衣、袜子"},
        "鞋类":         {"priority": 2, "desc": "运动鞋、帆布鞋、拖鞋、皮鞋"},
        "箱包":         {"priority": 3, "desc": "背包、行李箱、手提包、收纳包"},
        "话费流量":     {"priority": 1, "desc": "手机话费、流量套餐费用"},
        "宿舍缴费":     {"priority": 1, "desc": "水费、电费、网费、空调费"},
        "饮水费用":     {"priority": 1, "desc": "桶装水、直饮水费用"},
    },
    "娱乐休闲": {
        "视频会员":   {"priority": 3, "desc": "腾讯视频、爱奇艺、优酷、芒果TV、B站大会员"},
        "音乐会员":   {"priority": 3, "desc": "网易云音乐、QQ音乐、酷狗音乐"},
        "游戏相关":   {"priority": 4, "desc": "手游充值、皮肤、点券、端游点卡、游戏道具"},
        "网文漫画":   {"priority": 4, "desc": "小说会员、漫画付费、电子书购买"},
        "直播打赏":   {"priority": 5, "desc": "打赏、礼物、付费直播间"},
        "观影K歌":    {"priority": 4, "desc": "电影院、KTV、私人影院"},
        "休闲体验":   {"priority": 4, "desc": "剧本杀、密室逃脱、台球、桌游、抓娃娃"},
        "户外游玩":   {"priority": 4, "desc": "逛街、公园游览、短途出游、景点门票"},
        "追星周边":   {"priority": 5, "desc": "专辑、海报、应援物、演唱会门票"},
        "兴趣器材":   {"priority": 4, "desc": "绘画工具、摄影器材、乐器、手办、模型"},
        "健身运动":   {"priority": 3, "desc": "健身房卡、瑜伽垫、护具、运动装备"},
    },
    "学习教育": {
        "文具耗材":   {"priority": 2, "desc": "笔、笔记本、文件夹、便利贴、尺子"},
        "打印复印":   {"priority": 2, "desc": "资料打印、论文打印、复印、装订"},
        "教材书籍":   {"priority": 2, "desc": "教材、参考书、题库、课外书籍"},
        "考试报名":   {"priority": 3, "desc": "四六级、计算机、教资、考研、驾照报名费"},
        "网课培训":   {"priority": 3, "desc": "考研课程、技能课程、语言课程、编程课程"},
        "竞赛费用":   {"priority": 4, "desc": "竞赛报名费、材料费、培训费"},
        "学习设备":   {"priority": 2, "desc": "电脑、平板、U盘、硬盘、打印机"},
        "设备配件":   {"priority": 2, "desc": "鼠标、键盘、耳机、充电器、保护膜"},
        "软件会员":   {"priority": 3, "desc": "Office、Adobe、知网、编程软件会员"},
    },
    "交通出行": {
        "校内代步": {"priority": 2, "desc": "共享单车、校园巴士、电动车"},
        "市内交通": {"priority": 2, "desc": "公交、地铁、网约车、出租车、顺风车"},
        "往返家乡": {"priority": 2, "desc": "火车、高铁、汽车、飞机票（寒暑假刚需）"},
        "旅游出行": {"priority": 4, "desc": "长途车票、租车费用、景区交通"},
    },
    "社交人情": {
        "生日礼品": {"priority": 3, "desc": "生日礼物、蛋糕、鲜花"},
        "节日礼品": {"priority": 4, "desc": "情人节、圣诞节、新年礼品"},
        "人情红包": {"priority": 4, "desc": "喜事红包、份子钱"},
        "约会消费": {"priority": 3, "desc": "餐饮、电影、逛街、饮品（恋爱党）"},
        "社团班费": {"priority": 2, "desc": "社团费、班费、活动经费"},
        "人情往来": {"priority": 3, "desc": "请客饮品、零食、小礼品"},
    },
    "医疗健康": {
        "校医院消费": {"priority": 2, "desc": "挂号费、药品费、简单诊疗费"},
        "常用药品":   {"priority": 2, "desc": "感冒药、肠胃药、消炎药、创可贴"},
        "体检防疫":   {"priority": 2, "desc": "体检费、口罩、消毒液、抗原"},
        "保健品":     {"priority": 4, "desc": "维生素、蛋白粉、代餐食品"},
        "养生用品":   {"priority": 4, "desc": "泡脚包、颈椎贴、眼罩、暖贴"},
    },
    "其他杂项": {
        "快递物流": {"priority": 3, "desc": "寄件快递费、退货运费、代收费用"},
        "维修费用": {"priority": 4, "desc": "手机、电脑、耳机及小家电维修"},
        "金融还款": {"priority": 2, "desc": "花呗/信用卡还款、手续费、小额理财"},
        "盲盒抽奖": {"priority": 5, "desc": "盲盒、抽奖、临时小额冲动消费"},
        "其他支出": {"priority": 3, "desc": "以上未涵盖的其他支出"},
    },
}

ALL_EXPENSE_SUBCATS = [sub for subs in EXPENSE_STRUCTURE.values() for sub in subs]
SUBCAT_TO_BIGCAT = {sub: big for big, subs in EXPENSE_STRUCTURE.items() for sub in subs}
SUBCAT_PRIORITY = {sub: info["priority"] for big, subs in EXPENSE_STRUCTURE.items() for sub, info in subs.items()}
ALL_CATEGORIES = INCOME_CATEGORIES + ALL_EXPENSE_SUBCATS

PRIORITY_LABEL = {1: "刚需", 2: "高频", 3: "中等", 4: "低频", 5: "可省"}
PRIORITY_COLOR = {1: "#10B981", 2: "#3B82F6", 3: "#F59E0B", 4: "#F97316", 5: "#EF4444"}

WALLET_NAMES    = ["微信零钱", "支付宝余额", "银行卡", "现金"]
WALLET_ICONS    = {"微信零钱": "💚", "支付宝余额": "💙", "银行卡": "💳", "现金": "💵"}
PAYMENT_METHODS = WALLET_NAMES

BIGCAT_RANGE = {
    "餐饮消费": (45, 65), "生活日用": (8, 18), "娱乐休闲": (3, 10),
    "学习教育": (3, 10),  "交通出行": (2, 6),  "社交人情": (3, 10),
    "医疗健康": (1, 5),   "其他杂项": (0, 5),
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
# 不理性消费规则
# ============================================================
IRRATIONAL_RULES = [
    {"keywords": ["奶茶","碳酸","可乐","饮料"], "apply_cats": ["街头小吃","零食囤货","其他支出","宿舍自炊"], "icon": "🧋", "msg": "含糖饮料累计花费惊人，建议每周不超过2次，多喝白开水，既省钱又健康。"},
    {"keywords": ["外卖"], "apply_cats": ["正餐外卖","夜宵外卖","饮品外卖"], "amount_threshold": 35, "icon": "🛵", "msg": "外卖比食堂贵30%-50%，建议每周外卖不超过3次，能去食堂就去食堂！"},
    {"keywords": ["夜宵","深夜"], "apply_cats": ["夜宵外卖","街头小吃"], "icon": "🌙", "msg": "频繁吃夜宵影响睡眠和健康，建议保持规律作息，减少深夜进食。"},
    {"keywords": ["打车","网约车","滴滴","出租"], "apply_cats": ["市内交通"], "amount_threshold": 20, "icon": "🚕", "msg": "打车比公交贵5-10倍！建议规划出行时间，多选公交、地铁或骑行。"},
    {"keywords": ["游戏","充值","内购","氪金","皮肤"], "apply_cats": ["游戏相关"], "icon": "🎮", "msg": "游戏充值极易失控！建议设定月度上限（不超过总支出5%），避免为虚拟道具大额消费。"},
    {"keywords": ["直播","打赏","礼物"], "apply_cats": ["直播打赏"], "icon": "📱", "msg": "直播打赏是高度冲动性消费！强烈建议关闭礼物功能，这类消费对你毫无实际价值。"},
    {"keywords": ["烟","香烟"], "apply_cats": None, "icon": "🚬", "msg": "购买香烟既有害健康又浪费金钱，强烈建议戒烟或不要开始吸烟。"},
    {"keywords": ["白酒","啤酒","红酒"], "apply_cats": ["朋友小聚","生日节日聚餐","街头小吃","其他支出"], "icon": "🍺", "msg": "频繁饮酒影响健康和学习状态，聚会适量即可，避免养成饮酒习惯。"},
    {"keywords": ["彩妆","口红","粉底","眼影"], "apply_cats": ["护肤美妆"], "amount_threshold": 200, "icon": "💄", "msg": "大学阶段建议以基础护肤为主，避免跟风购买网红彩妆，超出实际需求。"},
    {"keywords": ["网红","盲盒","抽奖"], "apply_cats": ["盲盒抽奖","其他支出"], "icon": "📦", "msg": "盲盒/网红商品营销溢价高，建议理性评估实际使用价值，避免冲动跟风。"},
    {"keywords": ["红包","份子钱"], "apply_cats": ["人情红包"], "amount_threshold": 150, "icon": "🧧", "msg": "大额红包/份子钱容易形成攀比压力，心意比金额重要，学生阶段量力而行即可。"},
    {"keywords": ["会员","VIP"], "apply_cats": ["视频会员","音乐会员","软件会员"], "icon": "🔑", "msg": "办会员前确认实际使用频率！多平台叠加是隐性开销，建议定期审查取消不常用订阅。"},
    {"keywords": ["演唱会","应援","专辑"], "apply_cats": ["追星周边"], "icon": "⭐", "msg": "追星消费容易失控，建议设定追星年度预算，爱豆不会因为你多买一张专辑而喜欢你。"},
    {"keywords": ["保健品","蛋白粉","代餐"], "apply_cats": ["保健品"], "icon": "💊", "msg": "学生阶段无需额外保健品，均衡饮食+规律运动是最好的保健方式，避免被营销忽悠。"},
]

CATEGORY_AMOUNT_RULES = [
    {"cat": "游戏相关",     "threshold": 100, "icon": "🎮", "msg": "单次游戏消费超100元，请反思是否为冲动充值。"},
    {"cat": "直播打赏",     "threshold": 50,  "icon": "📱", "msg": "直播打赏超50元，强烈建议立即停止！"},
    {"cat": "朋友小聚",     "threshold": 200, "icon": "🍽️","msg": "单次聚餐较高，注意聚餐频率，避免因人情压力超额消费。"},
    {"cat": "生日节日聚餐", "threshold": 300, "icon": "🎂", "msg": "节日聚餐消费偏高，建议量力而行。"},
    {"cat": "日常衣物",     "threshold": 400, "icon": "👗", "msg": "单次服装消费较高，建议列好清单避免冲动消费。"},
    {"cat": "护肤美妆",     "threshold": 300, "icon": "💄", "msg": "美妆护肤单次偏高，优先选择平价基础护肤。"},
    {"cat": "人情红包",     "threshold": 200, "icon": "🧧", "msg": "人情往来金额较高，量力而行。"},
    {"cat": "市内交通",     "threshold": 50,  "icon": "🚕", "msg": "交通单次消费偏高，请多使用公交、地铁。"},
    {"cat": "追星周边",     "threshold": 200, "icon": "⭐", "msg": "追星消费较高，建议设定年度预算。"},
    {"cat": "盲盒抽奖",     "threshold": 100, "icon": "📦", "msg": "盲盒/抽奖消费较高，强烈建议设定月度上限。"},
]

def detect_irrational(row):
    # 安全处理数据
    try:
        if row.get("type") == "收入":
            return []
        note   = str(row.get("note", "")).strip()
        cat    = str(row.get("category", ""))
        amount = float(row.get("amount", 0))
        result = []
        for rule in IRRATIONAL_RULES:
            apply_cats = rule.get("apply_cats")
            if apply_cats is not None and cat not in apply_cats:
                continue
            if rule.get("amount_threshold", 0) > 0 and amount < rule["amount_threshold"]:
                continue
            if any(kw in note for kw in rule["keywords"]):
                result.append(f"{rule['icon']} {rule['msg']}")
        for rule in CATEGORY_AMOUNT_RULES:
            if cat == rule["cat"] and amount >= rule["threshold"]:
                result.append(f"{rule['icon']} {rule['msg']}")
        if SUBCAT_PRIORITY.get(cat, 3) == 5 and amount >= 50:
            result.append(f"⚠️ 「{cat}」属于可省略消费，单次支出{amount:.0f}元，请反思是否真有必要。")
        return result
    except (KeyError, ValueError, TypeError) as e:
        # 如果任何数据异常，返回空列表
        return []

# ============================================================
# 持久化（多用户独立文件）
# ============================================================
def user_data_file(username):    return f"finance_data_{username}.json"
def user_wallets_file(username): return f"finance_wallets_{username}.json"
def user_settings_file(username):return f"finance_settings_{username}.json"

def load_wallets(username=None):
    fname = user_wallets_file(username) if username else WALLETS_FILE
    if os.path.exists(fname):
        try:
            with open(fname, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, PermissionError, UnicodeDecodeError):
            pass
    return {w: 0.0 for w in WALLET_NAMES}

def save_wallets(w, username=None):
    fname = user_wallets_file(username) if username else WALLETS_FILE
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(w, f, ensure_ascii=False, indent=2)

def load_data(username=None):
    fname = user_data_file(username) if username else DATA_FILE
    if os.path.exists(fname):
        try:
            with open(fname, "r", encoding="utf-8") as f:
                records = json.load(f)
            df = pd.DataFrame(records)
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"])
            return df
        except (json.JSONDecodeError, FileNotFoundError, PermissionError, UnicodeDecodeError, ValueError) as e:
            st.error(f"数据加载失败：{e}")
    return pd.DataFrame(columns=["id","type","category","amount","date","note","payment_method"])

def save_data(df, username=None):
    fname = user_data_file(username) if username else DATA_FILE
    records = df.to_dict("records")
    # 处理日期格式
    for rec in records:
        if isinstance(rec["date"], (pd.Timestamp, datetime)):
            rec["date"] = rec["date"].strftime("%Y-%m-%d")
        elif not isinstance(rec["date"], str):
            # 如果不是字符串，转换为字符串
            rec["date"] = str(rec["date"])
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

def load_settings(username=None):
    d = {
        "theme": "极光紫", "layout": "宽松", "default_period": "本月",
        "sort_order": "日期降序", "monthly_budget": 2000.0,
        "show_modules": {"summary":True,"wallets":True,"charts":True,"advice":True,"records":True},
        "wallets_initialized": False
    }
    fname = user_settings_file(username) if username else SETTINGS_FILE
    if os.path.exists(fname):
        try:
            with open(fname, "r", encoding="utf-8") as f:
                saved = json.load(f)
            d.update(saved)
        except (json.JSONDecodeError, FileNotFoundError, PermissionError, UnicodeDecodeError):
            pass
    return d

def save_settings(s, username=None):
    fname = user_settings_file(username) if username else SETTINGS_FILE
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

# ============================================================
# 辅助
# ============================================================
def get_period_df(df, period, cs=None, ce=None):
    if df.empty:
        return df
    now = datetime.now()
    if period == "今日":
        s = now.replace(hour=0, minute=0, second=0); e = now
    elif period == "本周":
        s = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0); e = now
    elif period == "本月":
        s = now.replace(day=1, hour=0, minute=0, second=0); e = now
    elif period == "本学期":
        s = now - timedelta(days=150); e = now
    elif period == "全部":
        return df
    elif period == "自定义" and cs and ce:
        s = pd.Timestamp(cs); e = pd.Timestamp(ce) + timedelta(days=1)
    else:
        s = now.replace(day=1, hour=0, minute=0, second=0); e = now
    # 确保 DataFrame 有 date 列
    if "date" not in df.columns:
        return df
    filtered = df[(df["date"] >= pd.Timestamp(s)) & (df["date"] <= pd.Timestamp(e))]
    return filtered

def fmt(v):    return f"¥{v:,.2f}"
def tc(n):     return THEMES.get(n, THEMES["极光紫"])
def get_bigcat(subcat): return SUBCAT_TO_BIGCAT.get(subcat, "其他杂项")

# ============================================================
# CSS 注入
# ============================================================
def inject_css(theme_name, settings):
    t = tc(theme_name)
    pad = "1rem" if settings.get("layout") == "紧凑" else "2rem"
    st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700;900&display=swap');

.stApp{{background:{t['bg']};color:{t['text']};font-family:'Noto Sans SC',sans-serif;}}
.main .block-container{{padding:{pad};max-width:1400px;}}
h1,h2,h3{{color:{t['text']} !important;font-family:'Noto Sans SC',sans-serif !important;font-weight:700 !important;}}

.login-card{{background:{t['card']};border:1px solid {t['primary']}44;border-radius:28px;padding:2.8rem 2.4rem;width:100%;max-width:440px;box-shadow:0 24px 64px rgba(0,0,0,.35);}}
.login-logo{{text-align:center;margin-bottom:1.8rem;}}
.login-logo-icon{{font-size:3.5rem;display:block;margin-bottom:.6rem;}}
.login-logo-title{{font-size:1.6rem;font-weight:900;color:{t['text']};letter-spacing:-.02em;}}
.login-logo-sub{{font-size:.82rem;opacity:.55;margin-top:.2rem;}}

.metric-card{{background:linear-gradient(135deg,{t['card']},{t['primary']}18);border:1px solid {t['primary']}44;border-radius:20px;padding:1.6rem 1.4rem;text-align:center;}}
.metric-value{{font-size:1.85rem;font-weight:700;line-height:1.2;font-family:'Noto Sans SC',sans-serif;font-variant-numeric:tabular-nums;letter-spacing:-0.01em;}}
.metric-label{{font-size:0.82rem;opacity:0.65;margin-top:0.3rem;}}
.metric-icon{{font-size:1.8rem;margin-bottom:0.4rem;}}

.wallet-card{{background:{t['card']};border:1px solid {t['primary']}33;border-radius:16px;padding:1.2rem 1.4rem;margin-bottom:.8rem;display:flex;align-items:center;justify-content:space-between;}}
.wallet-icon{{font-size:1.8rem;margin-right:.8rem;}}
.wallet-name{{font-size:.85rem;opacity:.65;}}
.wallet-amount{{font-size:1.45rem;font-weight:700;color:{t['primary']};font-family:'Noto Sans SC',sans-serif;font-variant-numeric:tabular-nums;letter-spacing:-0.01em;}}
.wallet-total{{background:linear-gradient(135deg,{t['primary']},{t['secondary']});border-radius:16px;padding:1.2rem 1.8rem;color:white;display:flex;align-items:center;justify-content:space-between;margin-bottom:1.2rem;}}
.wallet-total-label{{font-size:.82rem;opacity:.85;margin-bottom:.25rem;}}
.wallet-total-amount{{font-size:2.1rem;font-weight:900;font-family:'Noto Sans SC',sans-serif;font-variant-numeric:tabular-nums;letter-spacing:-.02em;line-height:1.15;}}

.finance-card{{background:{t['card']};border:1px solid {t['primary']}22;border-radius:16px;padding:1.4rem;margin-bottom:.9rem;}}
.budget-bar-wrap{{background:{t['primary']}22;border-radius:8px;height:10px;margin:.4rem 0;overflow:hidden;}}
.budget-bar{{height:100%;border-radius:8px;transition:width .6s;}}

.advice-card{{background:{t['card']};border-left:4px solid {t['accent']};border-radius:0 12px 12px 0;padding:.8rem 1rem;margin:.4rem 0;font-size:.88rem;}}
.warning-card{{border-left-color:{t['expense']};}}
.good-card{{border-left-color:{t['income']};}}
.urgent-card{{border-left-color:#FF0000;background:rgba(255,0,0,0.08);}}
.irrational-card{{border-left-color:#FF6B00;background:rgba(255,107,0,0.08);border-left-width:5px;}}

.record-row{{background:{t['card']};border:1px solid {t['primary']}22;border-radius:14px;padding:1rem 1.2rem;margin-bottom:.7rem;}}
.record-row-income{{border-left:4px solid {t['income']};}}
.record-row-expense{{border-left:4px solid {t['expense']};}}
.record-amount{{font-size:1.2rem;font-weight:700;font-family:'Noto Sans SC',sans-serif;font-variant-numeric:tabular-nums;letter-spacing:-0.01em;}}
.record-advice{{background:{t['primary']}10;border-radius:8px;padding:.6rem .9rem;margin-top:.5rem;font-size:.83rem;color:{t['text']};opacity:.9;}}
.record-irrational{{background:rgba(255,107,0,0.1);border:1px solid rgba(255,107,0,0.3);border-radius:8px;padding:.6rem .9rem;margin-top:.4rem;font-size:.82rem;}}

.welcome-banner{{background:linear-gradient(135deg,{t['primary']},{t['secondary']},{t['accent']});border-radius:20px;padding:1.8rem 2.4rem;margin-bottom:1.8rem;color:white;position:relative;overflow:hidden;}}
.welcome-banner::after{{content:'💰';position:absolute;right:2rem;top:50%;transform:translateY(-50%);font-size:5rem;opacity:.15;}}

.section-header{{display:flex;align-items:center;gap:.6rem;padding:.8rem 0;border-bottom:2px solid {t['primary']}33;margin-bottom:1.2rem;}}
.section-title{{font-size:1.1rem;font-weight:700;color:{t['text']};}}
.guide-tip{{background:linear-gradient(135deg,{t['primary']}15,{t['accent']}15);border:1px dashed {t['primary']}55;border-radius:14px;padding:1.1rem;margin:.7rem 0;font-size:.88rem;}}
.empty-state{{text-align:center;padding:3rem 1rem;opacity:.55;}}
.empty-icon{{font-size:3rem;margin-bottom:1rem;}}
.bigcat-badge{{display:inline-block;padding:.15rem .5rem;border-radius:4px;font-size:.72rem;opacity:.7;margin-right:.3rem;}}
.priority-tag{{display:inline-block;padding:.15rem .45rem;border-radius:4px;font-size:.72rem;font-weight:700;}}
.cat-tag{{display:inline-block;padding:.2rem .6rem;border-radius:6px;font-size:.78rem;font-weight:600;margin-right:.4rem;}}

.stSelectbox>div>div,.stTextInput>div>div>input,.stNumberInput>div>div>input,.stDateInput>div>div>input,.stTextArea>div>div>textarea{{background:{t['card']} !important;color:{t['text']} !important;border:1px solid {t['primary']}44 !important;border-radius:10px !important;}}
.stButton>button{{background:linear-gradient(135deg,{t['primary']},{t['secondary']}) !important;color:white !important;border:none !important;border-radius:10px !important;font-weight:600 !important;}}
.stSidebar{{background:{t['card']} !important;}}
.stTabs [data-baseweb="tab-list"]{{gap:8px;background:{t['card']};padding:8px;border-radius:14px;}}
.stTabs [data-baseweb="tab"]{{background:transparent;color:{t['text']}99;border-radius:10px;padding:.45rem 1rem;font-weight:500;}}
.stTabs [aria-selected="true"]{{background:{t['primary']} !important;color:white !important;}}
::-webkit-scrollbar{{width:6px;}}
::-webkit-scrollbar-track{{background:{t['bg']};}}
::-webkit-scrollbar-thumb{{background:{t['primary']}66;border-radius:3px;}}
</style>""", unsafe_allow_html=True)

# ============================================================
# 登录 / 注册页面
# ★ 核心修复：if submitted / if reg_btn 移入 with st.form 块内
#   避免重新渲染时 username/password 为空导致登录永远失败
# ============================================================
def render_auth_page():
    inject_css("极光紫", {"layout": "宽松"})
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        st.markdown("""<div class="login-card">
          <div class="login-logo">
            <span class="login-logo-icon">🎓</span>
            <div class="login-logo-title">Campus Finance</div>
            <div class="login-logo-sub">大学生财务管理系统 · 你的每一分钱都值得被记录</div>
          </div>
        </div>""", unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["🔐  登录", "📝  注册新账号"])

        # ── 登录 ──────────────────────────────────────────────
        with tab_login:
            st.markdown("")
            with st.form("login_form", clear_on_submit=False):
                username  = st.text_input("用户名", placeholder="请输入用户名", key="login_user")
                password  = st.text_input("密码",   placeholder="请输入密码",   type="password", key="login_pw")
                submitted = st.form_submit_button("🚀 登录", use_container_width=True)

                # ★ 关键：把逻辑放在 with st.form 内，保证 username/password 已读取
                if submitted:
                    if not username or not password:
                        st.error("用户名和密码不能为空")
                    elif not load_auth():
                        st.warning("系统还没有任何账号，请先注册！")
                    elif username not in load_auth():
                        st.error("用户名不存在，请先注册")
                    elif not verify_password(username, password):
                        st.error("密码错误，请重试")
                    else:
                        display = get_display_name(username)
                        st.session_state.logged_in    = True
                        st.session_state.username     = username
                        st.session_state.display_name = display
                        st.session_state.df           = load_data(username)
                        st.session_state.wallets      = load_wallets(username)
                        st.session_state.settings     = load_settings(username)
                        st.session_state.wallets_initialized = st.session_state.settings.get("wallets_initialized", False)
                        st.success(f"✅ 欢迎回来，{display}！")
                        st.rerun()

        # ── 注册 ──────────────────────────────────────────────
        with tab_register:
            st.markdown("")
            with st.form("register_form", clear_on_submit=True):
                new_user   = st.text_input("用户名（登录用）", placeholder="2-20位",   key="reg_user")
                display_nm = st.text_input("显示昵称（可选）", placeholder="空则同用户名", key="reg_disp")
                new_pw     = st.text_input("密码",     placeholder="至少6位", type="password", key="reg_pw")
                new_pw2    = st.text_input("确认密码", placeholder="再次输入密码", type="password", key="reg_pw2")
                reg_btn    = st.form_submit_button("✨ 创建账号", use_container_width=True)

                # ★ 关键：同样移入 with st.form 内
                if reg_btn:
                    if not new_user or not new_pw:
                        st.error("用户名和密码不能为空")
                    elif len(new_user) < 2 or len(new_user) > 20:
                        st.error("用户名长度需在 2-20 位之间")
                    elif len(new_pw) < 6:
                        st.error("密码至少需要 6 位")
                    elif new_pw != new_pw2:
                        st.error("两次密码输入不一致")
                    elif new_user in load_auth():
                        st.error("该用户名已被注册，请换一个")
                    else:
                        register_user(new_user, new_pw, display_nm or new_user)
                        st.success(f"🎉 账号「{new_user}」注册成功！请切换到登录标签页登录。")

        st.markdown("""<div style="text-align:center;font-size:.72rem;opacity:.35;padding:1.2rem 0 0">
          本地安全存储 · 密码 SHA-256 加密 · 数据完全私有
        </div>""", unsafe_allow_html=True)

# ============================================================
# 账户初始化向导
# ============================================================
def render_init_wizard():
    t = tc("极光紫")
    st.markdown(f"""<div style="max-width:600px;margin:3rem auto;text-align:center">
      <div style="font-size:3rem;margin-bottom:1rem">👋</div>
      <h2 style="color:{t['text']}">Hi，{st.session_state.display_name}！</h2>
      <p style="opacity:.7">首次使用，请输入您当前各账户的实际余额，之后登录将直接进入系统。</p>
    </div>""", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown('<div class="guide-tip">💡 如实填写当前各账户余额，填 0 表示该账户暂无余额或不使用。</div>', unsafe_allow_html=True)
        init_vals = {}
        for name in WALLET_NAMES:
            icon = WALLET_ICONS.get(name, "💰")
            init_vals[name] = st.number_input(f"{icon} {name} 当前余额（元）", min_value=0.0, value=0.0, step=10.0, key=f"init_{name}")
        total_init = sum(init_vals.values())
        st.markdown(f"""<div style="text-align:center;padding:1rem;background:rgba(124,58,237,0.15);border-radius:12px;margin:1rem 0">
          <div style="font-size:.82rem;opacity:.7">初始总资产</div>
          <div style="font-size:2rem;font-weight:700;color:#7C3AED;font-family:'Noto Sans SC',sans-serif;font-variant-numeric:tabular-nums">{fmt(total_init)}</div>
        </div>""", unsafe_allow_html=True)
        if st.button("✅ 确认并开始使用", use_container_width=True):
            username = st.session_state.username
            st.session_state.wallets = init_vals
            save_wallets(init_vals, username)
            settings = load_settings(username)
            settings["wallets_initialized"] = True
            save_settings(settings, username)
            st.session_state.wallets_initialized = True
            st.session_state.settings = settings
            st.session_state.df = pd.DataFrame(columns=["id","type","category","amount","date","note","payment_method"])
            save_data(st.session_state.df, username)
            st.success("初始化完成！正在进入系统...")
            st.rerun()

# ============================================================
# 钱包面板
# ============================================================
def render_wallet_panel(theme_name):
    username = st.session_state.username
    wallets  = st.session_state.wallets
    total    = sum(wallets.values())
    st.markdown(f"""<div class="wallet-total">
      <div>
        <div class="wallet-total-label">💰 当前总资产</div>
        <div class="wallet-total-amount">{fmt(total)}</div>
      </div>
      <div style="font-size:2.5rem;opacity:.4">🏦</div>
    </div>""", unsafe_allow_html=True)
    cols = st.columns(2)
    for i, (name, amount) in enumerate(wallets.items()):
        icon = WALLET_ICONS.get(name, "💰")
        with cols[i % 2]:
            st.markdown(f"""<div class="wallet-card">
              <div style="display:flex;align-items:center">
                <span class="wallet-icon">{icon}</span>
                <span class="wallet-name">{name}</span>
              </div>
              <span class="wallet-amount">{fmt(amount)}</span>
            </div>""", unsafe_allow_html=True)

    with st.expander("✏️ 修改账户余额", expanded=False):
        st.markdown('<div class="guide-tip">💡 充值/提现/转账等账外变动时，直接更新余额，系统自动记录差额。</div>', unsafe_allow_html=True)
        edit_cols = st.columns(2)
        new_vals = {}
        for i, name in enumerate(WALLET_NAMES):
            with edit_cols[i % 2]:
                new_vals[name] = st.number_input(
                    f"{WALLET_ICONS.get(name,'')} {name}（元）",
                    min_value=0.0, value=float(wallets.get(name, 0.0)),
                    step=1.0, key=f"wallet_edit_{name}"
                )
        if st.button("💾 保存余额", use_container_width=True, key="save_wallets"):
            diff = sum(new_vals.values()) - sum(st.session_state.wallets.values())
            st.session_state.wallets = new_vals
            save_wallets(new_vals, username)
            if abs(diff) > 0.01:
                adj_row = pd.DataFrame([{
                    "id": f"adj_{int(datetime.now().timestamp()*1000)}",
                    "type": "收入" if diff > 0 else "支出",
                    "category": "其他收入" if diff > 0 else "其他支出",
                    "amount": round(abs(diff), 2),
                    "date": pd.Timestamp(date.today()),
                    "note": "余额手动调整",
                    "payment_method": "银行卡"
                }])
                st.session_state.df = pd.concat([st.session_state.df, adj_row], ignore_index=True)
                save_data(st.session_state.df, username)
            st.success(f"✅ 余额已更新！总资产：{fmt(sum(new_vals.values()))}")
            st.rerun()

# ============================================================
# 统计总览
# ============================================================
def render_summary_cards(df, theme_name):
    t = tc(theme_name)
    # 安全地处理空数据
    if df.empty or "type" not in df.columns or "amount" not in df.columns:
        income = expense = balance = 0.0
    else:
        income  = df[df["type"] == "收入"]["amount"].sum()
        expense = df[df["type"] == "支出"]["amount"].sum()
        balance = income - expense
    bcol = t["income"] if balance >= 0 else t["expense"]
    total_assets = sum(st.session_state.wallets.values())
    c1, c2, c3, c4 = st.columns(4)
    for col, icon, val, color, label in [
        (c1, "📥", fmt(income),   t["income"],  "期间收入"),
        (c2, "📤", fmt(expense),  t["expense"], "期间支出"),
        (c3, "💰", ("+" if balance >= 0 else "") + fmt(balance), bcol, "期间结余"),
        (c4, "🏦", fmt(total_assets), t["primary"], "当前总资产"),
    ]:
        col.markdown(f"""<div class="metric-card">
          <div class="metric-icon">{icon}</div>
          <div class="metric-value" style="color:{color}">{val}</div>
          <div class="metric-label">{label}</div>
        </div>""", unsafe_allow_html=True)

# ============================================================
# 图表
# ============================================================
def apply_layout(fig, t, title_text="", has_axes=False, grid_color=None):
    kwargs = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=16, r=16, t=48 if title_text else 24, b=16),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
        font=dict(color=t["text"], family="Noto Sans SC, sans-serif", size=13),
    )
    if title_text:
        kwargs["title"] = dict(text=title_text, font=dict(color=t["text"], size=16), x=0.02, xanchor="left")
    fig.update_layout(**kwargs)
    if has_axes and grid_color:
        fig.update_xaxes(gridcolor=grid_color, zerolinecolor=grid_color)
        fig.update_yaxes(gridcolor=grid_color, zerolinecolor=grid_color)
    return fig

def render_charts(df, theme_name):
    t = tc(theme_name)
    template = "plotly_dark" if t["mode"] == "dark" else "plotly_white"
    exp_df   = df[df["type"] == "支出"]
    grid     = hex_alpha(t["primary"], 0.2)
    data_sig = f"{len(df)}_{df['id'].iloc[-1] if not df.empty else 'empty'}"

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["🥧 子类分布", "🗂️ 大类分布", "📊 月度对比", "📈 趋势变化", "🗓️ 消费频次", "🎯 消费结构"]
    )

    with tab1:
        if exp_df.empty:
            st.markdown('<div class="empty-state"><div class="empty-icon">📊</div><p>暂无支出数据</p></div>', unsafe_allow_html=True)
        else:
            cat_sum = exp_df.groupby("category")["amount"].sum().reset_index()
            fig = px.pie(cat_sum, values="amount", names="category", hole=.42,
                         color_discrete_sequence=px.colors.qualitative.Set3, template=template)
            fig.update_traces(textposition="outside", textinfo="percent+label",
                              hovertemplate="<b>%{label}</b><br>¥%{value:.2f} · %{percent}<extra></extra>")
            apply_layout(fig, t, "支出子类占比")
            st.plotly_chart(fig, use_container_width=True, key=f"pie_sub_{data_sig}")

    with tab2:
        if exp_df.empty:
            st.markdown('<div class="empty-state"><div class="empty-icon">📊</div><p>暂无支出数据</p></div>', unsafe_allow_html=True)
        else:
            ec = exp_df.copy()
            ec["大类"] = ec["category"].map(get_bigcat)
            bigcat_sum = ec.groupby("大类")["amount"].sum().reset_index().sort_values("amount", ascending=False)
            fig = px.bar(bigcat_sum, x="大类", y="amount", color="大类",
                         color_discrete_sequence=px.colors.qualitative.Pastel,
                         template=template, text_auto=".0f")
            apply_layout(fig, t, "支出大类汇总", has_axes=True, grid_color=grid)
            st.plotly_chart(fig, use_container_width=True, key=f"bigcat_{data_sig}")

    with tab3:
        if df.empty:
            st.markdown('<div class="empty-state"><div class="empty-icon">📊</div><p>暂无数据</p></div>', unsafe_allow_html=True)
        else:
            dc = df.copy()
            dc["month"] = dc["date"].dt.to_period("M").astype(str)
            monthly = dc.groupby(["month","type"])["amount"].sum().reset_index()
            fig = px.bar(monthly, x="month", y="amount", color="type", barmode="group",
                         color_discrete_map={"收入": t["income"], "支出": t["expense"]},
                         template=template, text_auto=".0f")
            apply_layout(fig, t, "月度收支对比", has_axes=True, grid_color=grid)
            st.plotly_chart(fig, use_container_width=True, key=f"bar_{data_sig}")

    with tab4:
        if df.empty:
            st.markdown('<div class="empty-state"><div class="empty-icon">📈</div><p>暂无数据</p></div>', unsafe_allow_html=True)
        else:
            dc = df.copy()
            dc["week"] = dc["date"].dt.to_period("W").apply(lambda r: r.start_time)
            weekly = dc.groupby(["week","type"])["amount"].sum().reset_index()
            fig = go.Figure()
            for tp, color in [("收入", t["income"]), ("支出", t["expense"])]:
                sub = weekly[weekly["type"] == tp]
                if sub.empty: continue
                fill_c = hex_alpha(color, 0.13)
                fig.add_trace(go.Scatter(
                    x=sub["week"], y=sub["amount"], name=tp,
                    mode="lines+markers",
                    line=dict(color=color, width=2.5, shape="spline"),
                    marker=dict(size=7, color=color),
                    fill="tozeroy", fillcolor=fill_c,
                    hovertemplate="<b>%{x|%Y-%m-%d}</b><br>¥%{y:.2f}<extra></extra>"
                ))
            apply_layout(fig, t, "周度收支趋势", has_axes=True, grid_color=grid)
            st.plotly_chart(fig, use_container_width=True, key=f"line_{data_sig}")

    with tab5:
        if exp_df.empty:
            st.markdown('<div class="empty-state"><div class="empty-icon">🗓️</div><p>暂无支出数据</p></div>', unsafe_allow_html=True)
        else:
            dc = exp_df.copy()
            dc["dow"] = dc["date"].dt.dayofweek
            counts = dc.groupby("dow").size().reindex(range(7), fill_value=0)
            days_cn = ["周一","周二","周三","周四","周五","周六","周日"]
            fig = go.Figure(go.Bar(
                x=days_cn, y=counts.values,
                marker_color=[t["primary"]] * 5 + [t["accent"]] * 2,
                text=counts.values, textposition="outside",
                hovertemplate="<b>%{x}</b><br>消费%{y}次<extra></extra>"
            ))
            apply_layout(fig, t, "各星期消费频次", has_axes=True, grid_color=grid)
            st.plotly_chart(fig, use_container_width=True, key=f"dow_{data_sig}")

    with tab6:
        if exp_df.empty:
            st.markdown('<div class="empty-state"><div class="empty-icon">🎯</div><p>暂无支出数据</p></div>', unsafe_allow_html=True)
        else:
            total_exp = exp_df["amount"].sum()
            ec = exp_df.copy()
            ec["大类"] = ec["category"].map(get_bigcat)
            bigcat_sum = ec.groupby("大类")["amount"].sum()
            rows = []
            for bigcat, (lo, hi) in BIGCAT_RANGE.items():
                actual = bigcat_sum.get(bigcat, 0)
                ar = (actual / total_exp * 100) if total_exp > 0 else 0
                status = "✅ 合理" if lo <= ar <= hi else ("⚠️ 偏高" if ar > hi else ("📉 偏低" if ar > 0 else "—"))
                rows.append({"大类": bigcat, "实际占比": f"{ar:.1f}%", "建议区间": f"{lo}%～{hi}%", "状态": status, "金额": fmt(actual)})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ============================================================
# 消费建议
# ============================================================
def get_record_advice(row, all_expense_df):
    cat = row["category"]; amount = row["amount"]; tx_type = row["type"]
    bigcat = get_bigcat(cat); priority = SUBCAT_PRIORITY.get(cat, 3)
    if tx_type == "收入":
        return {"兼职收入": f"💪 兼职收入 {fmt(amount)}！建议将20%存入备用金。",
                "奖学金":   f"🏆 奖学金 {fmt(amount)}，恭喜！"}.get(cat, f"✅ 已到账 {fmt(amount)}，合理规划支出。")
    # 安全地计算总支出和分类支出
    total_exp = 0
    cat_total = 0
    if not all_expense_df.empty and "amount" in all_expense_df.columns:
        total_exp = all_expense_df["amount"].sum()
        if "category" in all_expense_df.columns:
            cat_total = all_expense_df[all_expense_df["category"] == cat]["amount"].sum() if not all_expense_df[all_expense_df["category"] == cat].empty else 0
    ratio = (cat_total / total_exp * 100) if total_exp > 0 else 0
    advice_map = {
        "食堂正餐":   f"🍱 食堂正餐 {fmt(amount)}，是最经济实惠的选择！",
        "奶茶咖啡":   f"🧋 奶茶/咖啡 {fmt(amount)}，适量享受即可，每周不超过3次。",
        "正餐外卖":   f"🛵 外卖 {fmt(amount)}，比食堂贵30%-50%，注意控制频率。",
        "夜宵外卖":   f"🌙 夜宵 {fmt(amount)}，频繁吃夜宵影响健康，注意控制频率。",
        "游戏相关":   f"🎮 游戏消费 {fmt(amount)}，建议设月度上限，不超过总支出5%。",
        "直播打赏":   f"📱 直播打赏 {fmt(amount)}，无实际价值回报，建议关闭礼物功能。",
        "视频会员":   f"🎬 视频会员 {fmt(amount)}，可和室友合租降低人均成本。",
        "市内交通":   f"🚇 市内交通 {fmt(amount)}，优先选择公交地铁，打车仅用于紧急情况。",
        "往返家乡":   f"🚆 回家路费 {fmt(amount)}，提前购票可以抢到更实惠的价格。",
        "生日礼品":   f"🎁 生日礼物 {fmt(amount)}，心意比金额重要！",
        "校医院消费": f"🏥 就医 {fmt(amount)}，身体健康最重要！",
        "金融还款":   f"💳 还款 {fmt(amount)}，按时还款保护信用，避免过度使用信贷。",
        "盲盒抽奖":   f"🎲 盲盒 {fmt(amount)}，娱乐性大于实用性，建议设月度上限。",
    }
    return advice_map.get(cat, f"💡 「{bigcat}·{cat}」{fmt(amount)}（P{priority} {PRIORITY_LABEL[priority]}）· 该类占总支出 {ratio:.1f}%。")

# ============================================================
# 整体建议
# ============================================================
def render_advice(df, settings, theme_name):
    t = tc(theme_name)
    wallets = st.session_state.wallets
    total_assets = sum(wallets.values())

    # 安全处理 DataFrame
    if df.empty or "type" not in df.columns:
        exp_df = pd.DataFrame(columns=["id", "type", "category", "amount", "date", "note", "payment_method"])
    else:
        exp_df = df[df["type"] == "支出"]

    budget = settings.get("monthly_budget", 2000.0)

    st.markdown('<div class="section-header"><span>🏦</span><span class="section-title">资产健康状态</span></div>', unsafe_allow_html=True)
    if total_assets < 200:
        st.markdown(f'<div class="advice-card urgent-card">🚨 <b>紧急预警</b>：总资产仅 {fmt(total_assets)}！建议立即联系家人补充生活费。</div>', unsafe_allow_html=True)
    elif total_assets < 500:
        st.markdown(f'<div class="advice-card warning-card">⚠️ 余额偏低：总资产 {fmt(total_assets)}，优先保障餐饮和交通。</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="advice-card good-card">✅ 资产良好：总资产 {fmt(total_assets)}，继续保持理性消费。</div>', unsafe_allow_html=True)

    if not exp_df.empty:
        # 检查必要列是否存在
        if "amount" in exp_df.columns:
            st.markdown('<div class="section-header" style="margin-top:1.5rem"><span>💡</span><span class="section-title">本月预算监控</span></div>', unsafe_allow_html=True)
            total_exp = exp_df["amount"].sum()
            ratio = (total_exp / budget * 100) if budget > 0 else 0
            bar_c = t["income"] if ratio < 80 else (t["accent"] if ratio < 100 else t["expense"])
            st.markdown(f"""<div class="finance-card">
              <div style="display:flex;justify-content:space-between;margin-bottom:.5rem">
                <span>月度预算执行</span><span style="color:{bar_c};font-weight:700">{ratio:.1f}%</span></div>
              <div class="budget-bar-wrap"><div class="budget-bar" style="width:{min(ratio,100):.1f}%;background:{bar_c}"></div></div>
              <div style="display:flex;justify-content:space-between;font-size:.8rem;opacity:.65;margin-top:.4rem">
                <span>已支出 {fmt(total_exp)}</span><span>预算 {fmt(budget)}</span></div>
            </div>""", unsafe_allow_html=True)
            if ratio >= 100:   st.error(f"⚠️ 已超预算 {fmt(total_exp - budget)}！")
            elif ratio >= 80:  st.warning(f"⚡ 预算已用 {ratio:.1f}%，剩余 {fmt(budget - total_exp)}")
            else:              st.success(f"✅ 预算良好！剩余 {fmt(budget - total_exp)}")

        st.markdown('<div class="section-header" style="margin-top:1.5rem"><span>🚨</span><span class="section-title">不理性消费扫描</span></div>', unsafe_allow_html=True)
        found_any = False
        for _, row in exp_df.iterrows():
            # 检查行是否包含必要数据
            try:
                warnings_list = detect_irrational(row)
                if warnings_list:
                    found_any = True
                    if "date" in row and "category" in row and "amount" in row:
                        date_str = row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"])
                        for w in warnings_list:
                            st.markdown(f'<div class="advice-card irrational-card">{w}<br><span style="font-size:.78rem;opacity:.6">{row["category"]} · {fmt(row["amount"])} · {date_str}</span></div>', unsafe_allow_html=True)
            except (KeyError, ValueError, AttributeError):
                continue
        if not found_any:
            st.markdown('<div class="advice-card good-card">🎉 未检测到明显不良消费行为，继续保持！</div>', unsafe_allow_html=True)

# ============================================================
# 记录管理
# ============================================================
def render_records_management(df, settings, theme_name):
    t = tc(theme_name)
    username = st.session_state.username
    tab1, tab2, tab3 = st.tabs(["➕ 新增记录", "📝 查看记录", "📤 导入/导出"])

    with tab1:
        st.markdown('<div class="guide-tip">💡 先选大类，再选具体子类，系统将给出精准消费建议。</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            tx_type = st.selectbox("类型 *", ["支出", "收入"], key="a_type")
            if tx_type == "支出":
                bigcat_list = list(EXPENSE_STRUCTURE.keys())
                bigcat = st.selectbox("大类 *", bigcat_list, key="a_bigcat")
                subcat_list = list(EXPENSE_STRUCTURE[bigcat].keys())
                cat = st.selectbox("子类 *", subcat_list, key="a_subcat",
                                   format_func=lambda x: f"{'⭐'*EXPENSE_STRUCTURE[bigcat][x]['priority']} {x}")
            else:
                cat    = st.selectbox("收入类别 *", INCOME_CATEGORIES, key="a_inc_cat")
                bigcat = None
            amount = st.number_input("金额（元）*", min_value=0.01, value=10.0, step=0.01, key="a_amt")
        with c2:
            tx_date = st.date_input("日期 *", value=date.today(), key="a_date")
            payment = st.selectbox("支付账户 *", PAYMENT_METHODS, key="a_pay")
            note    = st.text_input("备注", placeholder="如：外卖、打车、游戏充值...", key="a_note")

        if tx_type == "支出" and bigcat and cat in EXPENSE_STRUCTURE.get(bigcat, {}):
            info = EXPENSE_STRUCTURE[bigcat][cat]
            priority = info["priority"]
            pc = PRIORITY_COLOR.get(priority, "#888")
            pl = PRIORITY_LABEL.get(priority, "")
            st.markdown(f"""<div class="guide-tip">
              <b>「{bigcat}」→「{cat}」</b>
              &nbsp;<span class="priority-tag" style="background:{pc}22;color:{pc}">P{priority} {pl}</span><br>
              <span style="opacity:.75">{info['desc']}</span>
            </div>""", unsafe_allow_html=True)

        if st.button("💾 保存记录", use_container_width=True):
            wallets = st.session_state.wallets.copy()
            if tx_type == "支出":
                if wallets.get(payment, 0) < amount:
                    st.warning(f"⚠️ {payment} 余额不足（当前 {fmt(wallets.get(payment,0))}），记录已保存。")
                wallets[payment] = max(0.0, wallets.get(payment, 0) - amount)
            else:
                wallets[payment] = wallets.get(payment, 0) + amount
            st.session_state.wallets = wallets
            save_wallets(wallets, username)

            new_row = pd.DataFrame([{
                "id": str(int(datetime.now().timestamp() * 1000)),
                "type": tx_type, "category": cat, "amount": round(amount, 2),
                "date": pd.Timestamp(tx_date), "note": note, "payment_method": payment
            }])
            # 先计算建议，再保存
            exp_all     = st.session_state.df[st.session_state.df["type"] == "支出"]
            advice_text = get_record_advice(new_row.iloc[0], exp_all)

            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            save_data(st.session_state.df, username)
            st.success(f"✅ {tx_type} · {cat} · {fmt(amount)}  →  {payment} 余额：{fmt(wallets[payment])}")
            st.info(f"💡 {advice_text}")
            if tx_type == "支出":
                for w in detect_irrational(new_row.iloc[0]):
                    st.warning(f"🚨 {w}")
            st.rerun()

    with tab2:
        if df.empty:
            st.markdown('<div class="empty-state"><div class="empty-icon">📝</div><p>还没有任何记录</p></div>', unsafe_allow_html=True)
            return

        with st.expander("🔍 筛选条件", expanded=False):
            fa, fb, fc = st.columns(3)
            with fa: f_type = st.multiselect("类型", ["收入","支出"], default=["收入","支出"])
            with fb:
                bigcat_opts = ["全部大类"] + list(EXPENSE_STRUCTURE.keys())
                f_bigcat    = st.selectbox("大类筛选", bigcat_opts)
                f_cat = []
                if f_bigcat != "全部大类":
                    sub_opts = list(EXPENSE_STRUCTURE[f_bigcat].keys())
                    f_cat    = st.multiselect("子类筛选", sub_opts, default=[])
            with fc:
                amt_min = st.number_input("最低金额", value=0.0, step=1.0)
                amt_max = st.number_input("最高金额", value=99999.0, step=1.0)
            # 安全处理日期范围
            if df.empty or "date" not in df.columns:
                dr = (date.today(), date.today())
            else:
                dr = st.date_input("日期范围", value=(df["date"].min().date(), df["date"].max().date()))

        # 安全地过滤数据
        filt = df
        if not df.empty and "type" in df.columns:
            filt = df[df["type"].isin(f_type or ["收入","支出"])]
            if f_cat and "category" in filt.columns:
                filt = filt[filt["category"].isin(f_cat)]
            elif f_bigcat != "全部大类" and "category" in filt.columns:
                valid_subcats = list(EXPENSE_STRUCTURE.get(f_bigcat, {}).keys())
                filt = filt[filt["category"].isin(valid_subcats) | (filt["type"] == "收入")]
            if "amount" in filt.columns:
                filt = filt[(filt["amount"] >= amt_min) & (filt["amount"] <= amt_max)]
            if len(dr) == 2 and "date" in filt.columns:
                filt = filt[(filt["date"] >= pd.Timestamp(dr[0])) & (filt["date"] <= pd.Timestamp(dr[1]) + timedelta(days=1))]

        sort_map = {"日期降序": ("date", False), "日期升序": ("date", True), "金额降序": ("amount", False), "金额升序": ("amount", True)}
        sc, asc  = sort_map.get(settings.get("sort_order", "日期降序"), ("date", False))
        if not filt.empty and sc in filt.columns:
            filt = filt.sort_values(sc, ascending=asc)

        exp_all = df[df["type"] == "支出"] if df.empty or "type" not in df.columns else df[df["type"] == "支出"]
        st.caption(f"共 {len(filt)} 条记录")

        for _, row in filt.iterrows():
            try:
                is_income  = row.get("type") == "收入"
                row_class  = "record-row-income" if is_income else "record-row-expense"
                color      = tc(theme_name)["income"] if is_income else tc(theme_name)["expense"]
                sign       = "+" if is_income else "-"
                advice_text = get_record_advice(row, exp_all)
                date_str   = row["date"].strftime("%Y-%m-%d") if hasattr(row.get("date"), "strftime") else str(row.get("date", ""))
                note_html  = f'<span style="opacity:.55;font-size:.8rem"> · {row.get("note", "")}</span>' if row.get("note") else ""
                category = str(row.get("category", ""))
                bigcat     = get_bigcat(category) if not is_income else ""
                bigcat_html= f'<span class="bigcat-badge" style="background:{tc(theme_name)["primary"]}22">{bigcat}</span>' if bigcat else ""
                irrational_warnings = detect_irrational(row) if not is_income else []
                irrational_html = ""
                if irrational_warnings:
                    items = "".join([f'<div style="margin:.2rem 0">{w}</div>' for w in irrational_warnings])
                    irrational_html = f'<div class="record-irrational"><b>⚠️ 消费行为提醒</b>{items}</div>'
            except (KeyError, ValueError, AttributeError):
                continue  # 跳过有问题的行
            st.markdown(f"""<div class="record-row {row_class}">
              <div style="display:flex;justify-content:space-between;align-items:flex-start">
                <div>{bigcat_html}<span class="cat-tag" style="background:{color}22;color:{color}">{row['category']}</span>
                  <span style="font-size:.82rem;opacity:.6">{date_str}</span>{note_html}
                  <span style="font-size:.8rem;opacity:.5;margin-left:.4rem">via {row['payment_method']}</span>
                </div>
                <div class="record-amount" style="color:{color}">{sign}{fmt(row['amount'])}</div>
              </div>
              <div class="record-advice">💡 {advice_text}</div>
              {irrational_html}
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        del_id = st.text_input("输入要删除的行号（从 0 开始）", placeholder="如: 0", key="del_idx")
        if st.button("🗑️ 删除该记录", type="secondary"):
            try:
                idx = int(del_id)
                filt_list = filt.reset_index(drop=True)
                if 0 <= idx < len(filt_list):
                    row = filt_list.iloc[idx]
                    wallets = st.session_state.wallets.copy()
                    pm = row["payment_method"]
                    if pm in wallets:
                        wallets[pm] = (wallets[pm] + row["amount"]) if row["type"] == "支出" else max(0.0, wallets[pm] - row["amount"])
                        st.session_state.wallets = wallets
                        save_wallets(wallets, username)
                    st.session_state.df = st.session_state.df[st.session_state.df["id"] != row["id"]]
                    save_data(st.session_state.df, username)
                    st.success("记录已删除"); st.rerun()
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
                    imp = pd.read_csv(up).rename(columns={"类型":"type","子类":"category","金额(元)":"amount","日期":"date","备注":"note","支付账户":"payment_method"})
                    imp["date"] = pd.to_datetime(imp["date"])
                    imp["id"]   = [f"imp_{i}" for i in range(len(imp))]
                    st.dataframe(imp.head())
                    if st.button("确认导入"):
                        st.session_state.df = pd.concat([st.session_state.df, imp], ignore_index=True)
                        save_data(st.session_state.df, username)
                        st.success(f"成功导入 {len(imp)} 条"); st.rerun()
                except Exception as e:
                    st.error(f"导入失败：{e}")
        with c2:
            st.markdown("**📤 导出数据**")
            if not df.empty:
                exp = df.copy(); exp["date"] = exp["date"].dt.strftime("%Y-%m-%d")
                exp["大类"] = exp["category"].map(get_bigcat)
                exp = exp.rename(columns={"type":"类型","category":"子类","amount":"金额(元)","date":"日期","note":"备注","payment_method":"支付账户"})
                exp = exp[["日期","类型","大类","子类","金额(元)","支付账户","备注"]]
                buf = io.StringIO(); exp.to_csv(buf, index=False, encoding="utf-8-sig")
                st.download_button("⬇️ 下载 CSV", data=buf.getvalue().encode("utf-8-sig"),
                    file_name=f"finance_{username}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv", use_container_width=True)

# ============================================================
# 侧边栏
# ============================================================
def render_sidebar(settings):
    username     = st.session_state.username
    display_name = st.session_state.display_name

    with st.sidebar:
        st.markdown("""<div style="text-align:center;padding:1.2rem 0 .8rem">
          <div style="font-size:2.5rem">🎓</div>
          <div style="font-size:1.1rem;font-weight:700;margin:.3rem 0">Campus Finance</div>
          <div style="font-size:.78rem;opacity:.55">v9.2 · 多账号安全版</div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""<div style="background:rgba(124,58,237,0.15);border-radius:12px;padding:.8rem 1rem;margin-bottom:1rem;text-align:center">
          <div style="font-size:1.5rem">👤</div>
          <div style="font-weight:700;margin:.2rem 0">{display_name}</div>
          <div style="font-size:.75rem;opacity:.55">@{username}</div>
        </div>""", unsafe_allow_html=True)
        st.divider()

        st.markdown("**📅 数据周期**")
        period_opts = ["本月","本周","今日","本学期","全部","自定义"]
        dp = settings.get("default_period", "本月")
        if dp not in period_opts: dp = "本月"
        period = st.selectbox("查看时段", period_opts, index=period_opts.index(dp), label_visibility="collapsed")
        custom_start = custom_end = None
        if period == "自定义":
            custom_start = st.date_input("开始", value=date.today() - timedelta(days=30))
            custom_end   = st.date_input("结束", value=date.today())
        st.divider()

        st.markdown("**🎨 主题**")
        theme_keys = list(THEMES.keys())
        cur_theme  = settings.get("theme", "极光紫")
        if cur_theme not in theme_keys: cur_theme = "极光紫"
        theme  = st.selectbox("主题", theme_keys, index=theme_keys.index(cur_theme))
        layout = st.radio("布局", ["宽松","紧凑"], index=["宽松","紧凑"].index(settings.get("layout","宽松")), horizontal=True)
        sort_opts = ["日期降序","日期升序","金额降序","金额升序"]
        cur_sort  = settings.get("sort_order", "日期降序")
        if cur_sort not in sort_opts: cur_sort = "日期降序"
        sort_order = st.selectbox("记录排序", sort_opts, index=sort_opts.index(cur_sort))
        st.divider()

        st.markdown("**💰 月度预算（元）**")
        budget = st.number_input("", min_value=0.0, value=float(settings.get("monthly_budget", 2000.0)), step=100.0, label_visibility="collapsed")
        st.divider()

        st.markdown("**📦 显示模块**")
        sm = settings.get("show_modules", {})
        show_wallets = st.checkbox("账户余额",   value=sm.get("wallets", True))
        show_summary = st.checkbox("统计总览",   value=sm.get("summary", True))
        show_charts  = st.checkbox("可视化图表", value=sm.get("charts",  True))
        show_advice  = st.checkbox("资金建议",   value=sm.get("advice",  True))
        show_records = st.checkbox("记录管理",   value=sm.get("records", True))
        st.divider()

        with st.expander("🔑 修改密码", expanded=False):
            old_pw  = st.text_input("当前密码",   type="password", key="chpw_old")
            new_pw1 = st.text_input("新密码",     type="password", key="chpw_new1")
            new_pw2 = st.text_input("确认新密码", type="password", key="chpw_new2")
            if st.button("更新密码", use_container_width=True):
                if not old_pw or not new_pw1:       st.error("请填写完整")
                elif new_pw1 != new_pw2:            st.error("两次新密码不一致")
                elif len(new_pw1) < 6:              st.error("新密码至少6位")
                elif change_password(username, old_pw, new_pw1): st.success("✅ 密码已更新！")
                else:                               st.error("当前密码错误")

        st.divider()
        st.markdown("**🗄️ 数据操作**")
        if st.button("🏁 重置账户初始化", use_container_width=True, type="secondary"):
            s2 = load_settings(username); s2["wallets_initialized"] = False
            save_settings(s2, username)
            st.session_state.wallets_initialized = False; st.rerun()
        if st.button("🗑️ 清空所有记录", use_container_width=True, type="secondary"):
            if st.session_state.get("confirm_clear"):
                st.session_state.df = pd.DataFrame(columns=["id","type","category","amount","date","note","payment_method"])
                save_data(st.session_state.df, username)
                st.session_state.confirm_clear = False; st.rerun()
            else:
                st.session_state.confirm_clear = True
                st.warning("再次点击确认清空！")
        st.divider()

        if st.button("🚪 退出登录", use_container_width=True):
            for key in ["logged_in","username","display_name","df","wallets","settings","wallets_initialized","confirm_clear"]:
                st.session_state.pop(key, None)
            st.rerun()

        st.markdown('<div style="text-align:center;font-size:.7rem;opacity:.35;padding:.8rem 0">密码 SHA-256 加密 · 数据本地存储<br>Made with ❤️ for Students</div>', unsafe_allow_html=True)

    new_settings = {
        "theme": theme, "layout": layout, "default_period": period,
        "sort_order": sort_order, "monthly_budget": budget,
        "show_modules": {
            "wallets": show_wallets, "summary": show_summary,
            "charts":  show_charts,  "advice":  show_advice, "records": show_records
        },
        "wallets_initialized": settings.get("wallets_initialized", False),
    }
    if new_settings != settings:
        save_settings(new_settings, username)
        st.session_state.settings = new_settings
    return new_settings, period, custom_start, custom_end

# ============================================================
# 主程序
# ============================================================
def main():
    st.set_page_config(
        page_title="Campus Finance · 大学生财务管理",
        page_icon="🎓", layout="wide", initial_sidebar_state="expanded"
    )

    if not st.session_state.get("logged_in", False):
        render_auth_page()
        return

    username = st.session_state.username
    settings = st.session_state.get("settings") or load_settings(username)

    if not st.session_state.get("wallets_initialized", False):
        inject_css(settings.get("theme", "极光紫"), settings)
        render_init_wizard()
        return

    if "df" not in st.session_state:
        df_loaded = load_data(username)
        st.session_state.df = df_loaded if not df_loaded.empty else pd.DataFrame(columns=["id","type","category","amount","date","note","payment_method"])
    else:
        df_loaded = st.session_state.df
    if "wallets" not in st.session_state:
        st.session_state.wallets = load_wallets(username)

    df = st.session_state.df

    inject_css(settings["theme"], settings)
    settings, period, custom_start, custom_end = render_sidebar(settings)
    filtered = get_period_df(df, period, custom_start, custom_end)

    period_label = period if period != "自定义" else f"{custom_start} ~ {custom_end}"
    total_assets = sum(st.session_state.wallets.values())
    display_name = st.session_state.display_name

    st.markdown(f"""<div class="welcome-banner">
      <div style="font-size:.82rem;opacity:.8;margin-bottom:.3rem">欢迎回来，{display_name} 👋</div>
      <div style="font-size:1.8rem;font-weight:900;letter-spacing:-.02em">Campus Finance</div>
      <div style="font-size:.88rem;opacity:.8;margin-top:.4rem">
        {period_label} · {len(filtered)} 条记录 · 总资产 {fmt(total_assets)}
      </div>
    </div>""", unsafe_allow_html=True)

    if df.empty:
        st.markdown("""<div class="guide-tip">🎉 <b>登录成功！开始记账吧。</b><br>
        ① 在「收支记录管理」→「新增记录」开始记录<br>
        ② 先选大类，再选子类，系统给出精准消费建议<br>
        ③ 备注中填具体内容，触发不理性消费检测</div>""", unsafe_allow_html=True)

    sm = settings["show_modules"]

    if sm.get("wallets", True):
        with st.expander("🏦 账户余额", expanded=True):
            render_wallet_panel(settings["theme"])

    if sm.get("summary", True):
        with st.expander("📊 统计总览", expanded=True):
            render_summary_cards(filtered, settings["theme"])

    if sm.get("charts", True):
        with st.expander("📈 可视化图表", expanded=not df.empty):
            if df.empty:
                st.markdown('<div class="empty-state"><div class="empty-icon">📈</div><p>添加记录后图表将在此显示</p></div>', unsafe_allow_html=True)
            else:
                render_charts(st.session_state.df, settings["theme"])

    if sm.get("advice", True):
        with st.expander("💡 整体资金建议", expanded=True):
            render_advice(filtered, settings, settings["theme"])

    if sm.get("records", True):
        with st.expander("📂 收支记录管理", expanded=True):
            render_records_management(df, settings, settings["theme"])

if __name__ == "__main__":
    main()