-- ============================================================
-- 大学生财务管理系统 - Supabase 数据库初始化脚本
-- 在 Supabase Dashboard > SQL Editor 中运行此脚本
-- ============================================================

-- 1. 用户配置表（扩展 Supabase Auth 用户信息）
CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name VARCHAR(50),
  wallets_initialized BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 钱包表
CREATE TABLE IF NOT EXISTS wallets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name VARCHAR(50) NOT NULL,
  balance DECIMAL(12,2) DEFAULT 0,
  icon VARCHAR(10),
  UNIQUE(user_id, name)
);

-- 3. 交易记录表
CREATE TABLE IF NOT EXISTS transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  type VARCHAR(10) NOT NULL CHECK (type IN ('收入', '支出')),
  category VARCHAR(50) NOT NULL,
  bigcat VARCHAR(50),
  amount DECIMAL(12,2) NOT NULL,
  date DATE NOT NULL,
  note TEXT,
  payment_method VARCHAR(50),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. 用户设置表
CREATE TABLE IF NOT EXISTS settings (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  theme VARCHAR(20) DEFAULT '极光紫',
  layout VARCHAR(10) DEFAULT '宽松',
  default_period VARCHAR(20) DEFAULT '本月',
  sort_order VARCHAR(20) DEFAULT '日期降序',
  monthly_budget DECIMAL(10,2) DEFAULT 2000,
  show_modules JSONB DEFAULT '{"summary":true,"wallets":true,"charts":true,"advice":true,"records":true}'
);

-- ============================================================
-- 索引优化
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions(user_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_user_type ON transactions(user_id, type);
CREATE INDEX IF NOT EXISTS idx_wallets_user ON wallets(user_id);

-- ============================================================
-- Row Level Security (RLS) 策略
-- ============================================================

-- 启用 RLS
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;

-- user_profiles 策略
CREATE POLICY "用户可以查看自己的配置" ON user_profiles
  FOR SELECT USING (auth.uid() = id);
CREATE POLICY "用户可以插入自己的配置" ON user_profiles
  FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "用户可以更新自己的配置" ON user_profiles
  FOR UPDATE USING (auth.uid() = id);

-- wallets 策略
CREATE POLICY "用户可以查看自己的钱包" ON wallets
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "用户可以插入自己的钱包" ON wallets
  FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "用户可以更新自己的钱包" ON wallets
  FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "用户可以删除自己的钱包" ON wallets
  FOR DELETE USING (auth.uid() = user_id);

-- transactions 策略
CREATE POLICY "用户可以查看自己的交易" ON transactions
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "用户可以插入自己的交易" ON transactions
  FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "用户可以更新自己的交易" ON transactions
  FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "用户可以删除自己的交易" ON transactions
  FOR DELETE USING (auth.uid() = user_id);

-- settings 策略
CREATE POLICY "用户可以查看自己的设置" ON settings
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "用户可以插入自己的设置" ON settings
  FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "用户可以更新自己的设置" ON settings
  FOR UPDATE USING (auth.uid() = user_id);

-- ============================================================
-- 自动创建用户配置的触发器
-- ============================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.user_profiles (id, display_name)
  VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1)));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 删除已存在的触发器（如果有）
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- 创建触发器
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- 完成！
-- ============================================================
-- 运行此脚本后：
-- 1. 表结构已创建
-- 2. RLS 策略已启用
-- 3. 新用户注册时会自动创建 user_profiles 记录
