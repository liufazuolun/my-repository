# 大学生财务管理系统 - Supabase 迁移与优化设计

## 概述

将现有的 Streamlit 财务管理应用从本地 JSON 存储迁移到 Supabase，实现云端部署和数据持久化，同时全面优化代码质量、安全性和用户体验。

## 设计决策

| 决策项 | 选择 |
|--------|------|
| 数据存储 | Supabase (PostgreSQL) |
| 用户认证 | Supabase Auth |
| 部署平台 | Streamlit Cloud |
| 迁移策略 | 一次性完全迁移 |
| 数据兼容 | 提供旧数据迁移工具 |

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit Cloud                       │
├─────────────────────────────────────────────────────────┤
│  app.py                                                  │
│  ├── 认证模块 (Supabase Auth)                            │
│  ├── 数据模块 (Supabase Client)                          │
│  ├── UI 模块                                             │
│  └── 工具模块                                            │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                    Supabase                              │
├─────────────────────────────────────────────────────────┤
│  Auth Service          │  PostgreSQL Database           │
│  ├── 用户认证           │  ├── user_profiles             │
│  ├── 密码加盐           │  ├── transactions              │
│  └── 密码重置           │  ├── wallets                   │
│                        │  └── settings                   │
└─────────────────────────────────────────────────────────┘
```

## 数据库设计

### 表结构

```sql
-- 用户配置表
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  display_name VARCHAR(50),
  wallets_initialized BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 钱包表
CREATE TABLE wallets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name VARCHAR(50) NOT NULL,
  balance DECIMAL(12,2) DEFAULT 0,
  icon VARCHAR(10),
  UNIQUE(user_id, name)
);

-- 交易记录表
CREATE TABLE transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  type VARCHAR(10) NOT NULL,
  category VARCHAR(50) NOT NULL,
  bigcat VARCHAR(50),
  amount DECIMAL(12,2) NOT NULL,
  date DATE NOT NULL,
  note TEXT,
  payment_method VARCHAR(50),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 用户设置表
CREATE TABLE settings (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  theme VARCHAR(20) DEFAULT '极光紫',
  layout VARCHAR(10) DEFAULT '宽松',
  default_period VARCHAR(20) DEFAULT '本月',
  sort_order VARCHAR(20) DEFAULT '日期降序',
  monthly_budget DECIMAL(10,2) DEFAULT 2000,
  show_modules JSONB DEFAULT '{"summary":true,"wallets":true,"charts":true,"advice":true,"records":true}'
);

-- 索引
CREATE INDEX idx_transactions_user_date ON transactions(user_id, date DESC);
CREATE INDEX idx_transactions_user_type ON transactions(user_id, type);
```

### Row Level Security 策略

```sql
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "用户只能访问自己的交易" ON transactions
  FOR ALL USING (auth.uid() = user_id);

ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "用户只能访问自己的钱包" ON wallets
  FOR ALL USING (auth.uid() = user_id);

ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "用户只能访问自己的设置" ON settings
  FOR ALL USING (auth.uid() = user_id);

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "用户只能访问自己的配置" ON user_profiles
  FOR ALL USING (auth.uid() = user_id);
```

## 数据迁移策略

```
首次登录时检测：
├── 用户在 Supabase Auth 中存在？
│   ├── 是 → 直接登录
│   └── 否 → 检测本地是否有旧数据文件
│       ├── 有 → 显示迁移向导，一键导入
│       └── 无 → 显示新用户初始化向导
```

迁移完成后，原 JSON 文件重命名为 `*.json.bak` 保留备份。

## 代码结构

```
app.py (约 800 行)
│
├── 1. 配置与常量 (约 50 行)
├── 2. 数据库层 (约 120 行)
├── 3. 认证模块 (约 80 行)
├── 4. 业务逻辑 (约 150 行)
├── 5. UI 组件 (约 300 行)
└── 6. 页面渲染 (约 100 行)
```

## 用户体验优化

### 删除记录改进
- 每条记录卡片添加删除按钮
- 点击删除 → 弹出确认对话框 → 确认后删除

### 加载状态
- 数据操作时显示 `st.spinner()`
- 成功操作显示 `st.toast()`

### 错误提示优化
- 网络断开：顶部横幅提示
- 数据加载失败：友好提示 + 重试按钮
- 登录失败：显示剩余尝试次数

### 其他改进
- 金额输入支持快捷金额按钮
- 图表交互：点击扇区筛选记录

## 部署配置

### 文件结构
```
streamlit-app/
├── app.py
├── requirements.txt
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml (本地开发)
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-03-29-supabase-migration-design.md
```

### requirements.txt
```
streamlit>=1.30.0
plotly>=5.18.0
pandas>=2.0.0
supabase>=2.0.0
```

### Streamlit Cloud Secrets 配置
```
SUPABASE_URL = "https://jqlpbpjgrggamrhbwixs.supabase.co"
SUPABASE_KEY = "<anon_key>"
```

## 安全注意事项

1. **密钥管理**：Secret Key 不写入代码，使用 Streamlit Secrets
2. **RLS 策略**：确保用户只能访问自己的数据
3. **注册控制**：可在 Supabase 后台关闭公开注册

## 实施清单

- [ ] 创建 Supabase 数据库表
- [ ] 配置 RLS 策略
- [ ] 重构 app.py 代码
- [ ] 实现数据迁移功能
- [ ] 优化用户体验
- [ ] 创建部署配置文件
- [ ] 测试部署
