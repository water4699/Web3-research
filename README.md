# Crypto Research System (加密项目投研系统)

## 功能概述

1. **RootData 数据抓取**
   - 支持两种模式：`basic`（基本信息）和 `full`（全部信息含Pro字段）
   - 通过项目ID抓取指定项目
   - 批量抓取热门项目Top100

2. **Surf 投研报告生成**
   - 自动化网页操作生成PDF报告
   - 账号池管理（每账号每周2次免费额度）
   - 自动切换账号

3. **飞书多维表格推送**
   - 自动推送项目信息和报告到飞书

4. **定时任务**
   - 每日自动抓取热门项目
   - 自动生成待处理报告
   - 每周自动重置Surf配额

## 快速开始

### 1. 安装依赖

```bash
cd crypto-research-system
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的配置
```

### 3. 启动PostgreSQL数据库

```bash
# 使用Docker
docker run -d --name postgres -e POSTGRES_PASSWORD=password -e POSTGRES_DB=crypto_research -p 5432:5432 postgres:15
```

### 4. 启动服务

```bash
python run.py
```

访问 http://localhost:8000/docs 查看API文档

## API 使用示例

### 搜索项目
```bash
curl -X POST http://localhost:8000/api/projects/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Ethereum"}'
```

### 抓取项目（基本信息）
```bash
curl -X POST http://localhost:8000/api/projects/fetch \
  -H "Content-Type: application/json" \
  -d '{"project_id": 12, "mode": "basic"}'
```

### 抓取项目（全部信息）
```bash
curl -X POST http://localhost:8000/api/projects/fetch \
  -H "Content-Type: application/json" \
  -d '{"project_id": 12, "mode": "full"}'
```

### 添加Surf账号
```bash
curl -X POST http://localhost:8000/api/surf/accounts \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}'
```

### 生成投研报告
```bash
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1}'
```

### 推送到飞书
```bash
curl -X POST http://localhost:8000/api/feishu/push/1
```

## 项目结构

```
crypto-research-system/
├── app/
│   ├── __init__.py
│   ├── config.py           # 配置管理
│   ├── database.py         # 数据库连接
│   ├── models.py           # 数据库模型
│   ├── main.py             # FastAPI入口
│   ├── scheduler.py        # 定时任务
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py       # API路由
│   └── services/
│       ├── __init__.py
│       ├── rootdata_client.py      # RootData API客户端
│       ├── surf_account_pool.py    # Surf账号池管理
│       ├── surf_report_generator.py # Surf报告生成器
│       ├── feishu_client.py        # 飞书API客户端
│       └── project_service.py      # 项目服务
├── data/
│   ├── projects/           # 导出的项目JSON
│   └── reports/            # 生成的PDF报告
├── .env.example
├── requirements.txt
├── run.py
└── README.md
```

## 数据库表说明

| 表名 | 说明 |
|------|------|
| projects | 项目信息（含RootData原始数据） |
| surf_accounts | Surf账号池 |
| reports | 生成的投研报告 |
| tasks | 任务状态跟踪 |

## 注意事项

1. **RootData API Credits**
   - 搜索接口免费不限次数
   - 获取项目详情 2 credits/次
   - 热门项目Top100 10 credits/次

2. **Surf 配额管理**
   - 每个账号每周2次免费额度
   - 每周一自动重置
   - 建议准备多个账号

3. **飞书权限**
   - 需要申请 `bitable:app` 读写权限
   - 应用需要发布才能生效
