-- Crypto Research System 数据库表结构
-- MySQL 版本

-- 1. 项目信息表
CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rootdata_id INT UNIQUE,
    name VARCHAR(255),
    logo VARCHAR(500),
    token_symbol VARCHAR(50),
    establishment_date VARCHAR(50),
    one_liner TEXT,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    total_funding DECIMAL(20, 2),
    tags JSON,
    investors JSON,
    social_media JSON,
    similar_project JSON,
    
    -- Pro版本字段
    ecosystem JSON,
    on_main_net JSON,
    plan_to_launch JSON,
    on_test_net JSON,
    fully_diluted_market_cap VARCHAR(50),
    market_cap VARCHAR(50),
    price VARCHAR(50),
    event JSON,
    reports JSON,
    team_members JSON,
    token_launch_time VARCHAR(50),
    contracts JSON,
    support_exchanges JSON,
    heat VARCHAR(50),
    heat_rank INT,
    influence VARCHAR(50),
    influence_rank INT,
    followers INT,
    following INT,
    
    -- 元数据
    raw_json JSON,
    fetch_mode VARCHAR(20) COMMENT 'basic or full',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_rootdata_id (rootdata_id),
    INDEX idx_name (name),
    INDEX idx_token_symbol (token_symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 2. Surf账号池表
CREATE TABLE IF NOT EXISTS surf_accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_encrypted TEXT NOT NULL,
    cookie_data TEXT,
    
    -- 每周免费额度 (每周2次)
    weekly_quota_used INT DEFAULT 0,
    weekly_quota_limit INT DEFAULT 2,
    week_start_date TIMESTAMP NULL,
    
    status VARCHAR(20) DEFAULT 'active' COMMENT 'active/exhausted/disabled',
    last_used_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_email (email),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 3. 投研报告表
CREATE TABLE IF NOT EXISTS reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT,
    surf_account_id INT,
    
    report_content TEXT,
    report_pdf_path VARCHAR(500),
    report_url VARCHAR(500),
    
    feishu_record_id VARCHAR(100),
    
    status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending/generating/completed/failed',
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    
    INDEX idx_project_id (project_id),
    INDEX idx_status (status),
    
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (surf_account_id) REFERENCES surf_accounts(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 4. 任务状态表
CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_type VARCHAR(50) COMMENT 'fetch_projects/generate_report/push_feishu',
    task_params JSON,
    status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending/running/completed/failed',
    result JSON,
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    
    INDEX idx_task_type (task_type),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
