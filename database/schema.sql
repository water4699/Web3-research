-- Crypto Research System 数据库表结构
-- PostgreSQL

-- 1. 项目信息表
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    rootdata_id INTEGER UNIQUE,
    name VARCHAR(255),
    logo VARCHAR(500),
    token_symbol VARCHAR(50),
    establishment_date VARCHAR(50),
    one_liner TEXT,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    total_funding DECIMAL(20, 2),
    tags JSONB,
    investors JSONB,
    social_media JSONB,
    similar_project JSONB,
    
    -- Pro版本字段
    ecosystem JSONB,
    on_main_net JSONB,
    plan_to_launch JSONB,
    on_test_net JSONB,
    fully_diluted_market_cap VARCHAR(50),
    market_cap VARCHAR(50),
    price VARCHAR(50),
    event JSONB,
    reports JSONB,
    team_members JSONB,
    token_launch_time VARCHAR(50),
    contracts JSONB,
    support_exchanges JSONB,
    heat VARCHAR(50),
    heat_rank INTEGER,
    influence VARCHAR(50),
    influence_rank INTEGER,
    followers INTEGER,
    following INTEGER,
    
    -- 元数据
    raw_json JSONB,
    fetch_mode VARCHAR(20),  -- 'basic' or 'full'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_projects_rootdata_id ON projects(rootdata_id);
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
CREATE INDEX IF NOT EXISTS idx_projects_token_symbol ON projects(token_symbol);


-- 2. Surf账号池表
CREATE TABLE IF NOT EXISTS surf_accounts (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_encrypted TEXT NOT NULL,
    cookie_data TEXT,
    
    -- 每周免费额度 (每周2次)
    weekly_quota_used INTEGER DEFAULT 0,
    weekly_quota_limit INTEGER DEFAULT 2,
    week_start_date TIMESTAMP,
    
    status VARCHAR(20) DEFAULT 'active',  -- active/exhausted/disabled
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_surf_accounts_email ON surf_accounts(email);
CREATE INDEX IF NOT EXISTS idx_surf_accounts_status ON surf_accounts(status);


-- 3. 投研报告表
CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    surf_account_id INTEGER REFERENCES surf_accounts(id) ON DELETE SET NULL,
    
    report_content TEXT,
    report_pdf_path VARCHAR(500),
    report_url VARCHAR(500),
    
    feishu_record_id VARCHAR(100),
    
    status VARCHAR(20) DEFAULT 'pending',  -- pending/generating/completed/failed
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reports_project_id ON reports(project_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);


-- 4. 任务状态表
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    task_type VARCHAR(50),  -- fetch_projects/generate_report/push_feishu
    task_params JSONB,
    status VARCHAR(20) DEFAULT 'pending',  -- pending/running/completed/failed
    result JSONB,
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tasks_task_type ON tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);


-- 5. 更新时间触发器（可选）
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
