from sqlalchemy import Column, Integer, String, Text, DECIMAL, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Project(Base):
    """项目信息表"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    rootdata_id = Column(Integer, unique=True, index=True)
    name = Column(String(255), index=True)
    logo = Column(String(500))
    rootdataurl = Column(String(500))  # RootData项目链接
    token_symbol = Column(String(50))
    establishment_date = Column(String(50))
    one_liner = Column(Text)
    description = Column(Text)
    active = Column(Boolean, default=True)
    total_funding = Column(DECIMAL(20, 2))
    tags = Column(JSON)
    investors = Column(JSON)
    social_media = Column(JSON)
    similar_project = Column(JSON)
    
    # Pro版本字段
    ecosystem = Column(JSON)
    on_main_net = Column(JSON)
    plan_to_launch = Column(JSON)
    on_test_net = Column(JSON)
    fully_diluted_market_cap = Column(String(50))
    market_cap = Column(String(50))
    price = Column(String(50))
    event = Column(JSON)
    reports = Column(JSON)
    team_members = Column(JSON)
    token_launch_time = Column(String(50))
    contracts = Column(JSON)
    support_exchanges = Column(JSON)
    heat = Column(String(50))
    heat_rank = Column(Integer)
    influence = Column(String(50))
    influence_rank = Column(Integer)
    followers = Column(Integer)
    following = Column(Integer)
    
    # 原始JSON备份
    raw_json = Column(JSON)
    fetch_mode = Column(String(20))  # 'basic' or 'full'
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    research_reports = relationship("Report", back_populates="project")


class SurfAccount(Base):
    """Surf账号池表"""
    __tablename__ = "surf_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password_encrypted = Column(Text)
    cookie_data = Column(Text)
    
    # 每周免费额度 (每周2次)
    weekly_quota_used = Column(Integer, default=0)
    weekly_quota_limit = Column(Integer, default=2)
    week_start_date = Column(DateTime)  # 当前周期开始时间
    
    status = Column(String(20), default='active')  # active/exhausted/disabled
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    reports = relationship("Report", back_populates="surf_account")


class Report(Base):
    """投研报告表"""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    surf_account_id = Column(Integer, ForeignKey("surf_accounts.id"))
    
    report_content = Column(Text)
    report_pdf_path = Column(String(500))  # PDF文件路径
    report_url = Column(String(500))  # Surf上的报告链接
    
    feishu_record_id = Column(String(100))  # 飞书多维表格记录ID
    
    status = Column(String(20), default='pending')  # pending/generating/completed/failed
    error_message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # 关联
    project = relationship("Project", back_populates="research_reports")
    surf_account = relationship("SurfAccount", back_populates="reports")


class Task(Base):
    """任务状态表"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(50))  # fetch_projects/generate_report/push_feishu
    task_params = Column(JSON)
    status = Column(String(20), default='pending')  # pending/running/completed/failed
    result = Column(JSON)
    error_message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)


class VC(Base):
    """VC/机构信息表"""
    __tablename__ = "vcs"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, unique=True, index=True)  # RootData机构ID
    org_name = Column(String(255), index=True)
    logo = Column(String(500))
    rootdataurl = Column(String(500))
    establishment_date = Column(String(50))
    description = Column(Text)
    active = Column(Boolean, default=True)
    category = Column(JSON)  # 投资者类型
    social_media = Column(JSON)  # {website, twitter, linkedin}
    investments = Column(JSON)  # 投资项目列表
    team_members = Column(JSON)  # PRO: 团队成员
    
    # X数据 (PRO)
    heat = Column(String(50))
    heat_rank = Column(Integer)
    influence = Column(String(50))
    influence_rank = Column(Integer)
    followers = Column(Integer)
    following = Column(Integer)
    
    # 投资统计 (来自get_invest)
    invest_overview = Column(JSON)  # {lead_invest_num, last_invest_round, his_invest_round, invest_num}
    invest_range = Column(JSON)  # 投资规模分布
    invest_stics = Column(JSON)  # 投资赛道分布
    area = Column(JSON)  # 地区
    last_fac_date = Column(String(50))  # 最近投资时间
    last_invest_num = Column(Integer)  # 近一年投资数量
    
    raw_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class People(Base):
    """人物信息表"""
    __tablename__ = "people"
    
    id = Column(Integer, primary_key=True, index=True)
    people_id = Column(Integer, unique=True, index=True)  # RootData人物ID
    people_name = Column(String(255), index=True)
    head_img = Column(String(500))  # 头像
    one_liner = Column(Text)  # 一句话介绍
    introduce = Column(Text)  # 详细介绍
    x = Column(String(500))  # X链接
    linkedin = Column(String(500))  # LinkedIn链接
    
    # X数据 (PRO)
    heat = Column(String(50))
    heat_rank = Column(Integer)
    influence = Column(String(50))
    influence_rank = Column(Integer)
    followers = Column(Integer)
    following = Column(Integer)
    
    # 职位信息 (来自job_changes)
    company = Column(String(255))  # 当前公司
    position = Column(String(255))  # 当前职位
    
    raw_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FundingRound(Base):
    """投资轮次表"""
    __tablename__ = "funding_rounds"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, index=True)  # RootData项目ID
    project_name = Column(String(255))
    logo = Column(String(500))
    rounds = Column(String(100))  # 轮次名称 (Pre-Seed, Seed, Series A等)
    published_time = Column(String(50))  # 公布时间
    amount = Column(DECIMAL(20, 2))  # 融资金额(USD)
    valuation = Column(DECIMAL(20, 2))  # 估值(USD)
    invests = Column(JSON)  # 投资者列表 [{name, logo}]
    
    raw_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class Ecosystem(Base):
    """生态表"""
    __tablename__ = "ecosystems"
    
    id = Column(Integer, primary_key=True, index=True)
    ecosystem_id = Column(Integer, unique=True, index=True)  # RootData生态ID
    ecosystem_name = Column(String(255), index=True)
    project_num = Column(Integer)  # 项目数量
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Tag(Base):
    """标签表"""
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    tag_id = Column(Integer, unique=True, index=True)  # RootData标签ID
    tag_name = Column(String(255), index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class XData(Base):
    """X(Twitter)数据表 - 存储批量X数据"""
    __tablename__ = "x_data"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, index=True)  # 实体ID (项目/机构/人物)
    entity_type = Column(Integer)  # 1=项目, 2=机构, 3=人物
    name = Column(String(255))
    x = Column(String(500))  # X链接
    followers = Column(Integer)
    following = Column(Integer)
    heat = Column(String(50))
    influence = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SearchResult(Base):
    """搜索结果表 - 存储搜索接口返回的数据"""
    __tablename__ = "search_results"
    
    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(255), index=True)  # 搜索关键词
    entity_id = Column(Integer, index=True)  # RootData实体ID
    entity_type = Column(Integer)  # 1=项目, 2=机构, 3=人物
    name = Column(String(255))
    logo = Column(String(500))
    introduce = Column(Text)
    active = Column(Boolean, default=True)
    rootdataurl = Column(String(500))
    raw_json = Column(JSON)  # 原始JSON数据
    
    created_at = Column(DateTime, default=datetime.utcnow)
