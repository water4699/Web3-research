# 代理池使用指南

## 概述

本项目实现了代理池+轮询重试机制，专门用于解决 rambler.ru 邮箱在中国大陆地区的网络访问限制问题。

## 核心组件

### 1. 代理管理器 (`proxy_manager.py`)
- **代理池管理**：管理多个代理IP
- **健康检查**：自动检测代理可用性
- **轮询重试**：智能切换代理
- **统计监控**：代理使用统计

### 2. 代理配置文件 (`config/proxy_list.txt`)
```
# 代理列表格式
http://123.45.67.89:8080
https://98.76.54.32:3128#US
socks5://192.168.1.1:1080#CN
```

### 3. Surf自动登录集成 (`surf_auto_login.py`)
- 自动检测 rambler.ru 邮箱
- 智能使用代理池进行连接
- 失败时自动切换代理

## 使用方法

### 1. 添加代理IP

编辑 `config/proxy_list.txt` 文件：

```bash
# 添加你的代理IP
http://your-proxy-ip:port
https://another-proxy:3128#US
socks5://socks-proxy:1080
```

### 2. 安装依赖

```bash
pip install PySocks==1.7.1
```

### 3. 测试代理池

```bash
python test_proxy.py
```

### 4. 使用Surf自动登录

```python
from surf_auto_login import SurfAutoLogin, SurfAccount

# 创建rambler.ru邮箱账户
account = SurfAccount(
    email="your-email@rambler.ru",
    email_password="your-password"
)

# 自动使用代理池
login_tool = SurfAutoLogin(account)
success = await login_tool.auto_login()
```

## 代理IP来源

### 1. 付费代理服务
- **Luminati (Bright Data)**: 高质量住宅代理
- **Oxylabs**: 数据中心代理
- **Smartproxy**: 混合代理池

### 2. 免费代理
- **网站采集**：proxyscrape.com, free-proxy-list.net
- **API接口**：github.com/clarketm/proxy-list

### 3. 自建代理
- **VPS服务器** + Squid/Tinyproxy
- **Docker容器**部署

## 技术特性

### 轮询策略
- **Round Robin**: 顺序轮询
- **Random**: 随机选择
- **Best First**: 优先选择成功率最高的代理

### 健康检查
- 自动检测代理响应时间
- 统计成功率和失败次数
- 自动禁用失效代理

### 错误处理
- 连接超时自动重试
- SSL证书验证跳过
- 多层fallback机制

## 配置选项

### 代理管理器配置
```python
config = {
    'proxy_file': 'config/proxy_list.txt',
    'max_fail_count': 3,           # 最大失败次数
    'health_check_interval': 300,  # 健康检查间隔(秒)
    'rotation_mode': 'round_robin', # 轮询模式
    'test_url': 'http://httpbin.org/ip'  # 测试URL
}
```

## 故障排除

### 常见问题

1. **代理连接失败**
   - 检查代理IP格式
   - 确认代理服务可用
   - 尝试不同地理位置的代理

2. **编码问题**
   - 确保代理列表文件使用UTF-8编码
   - 避免在代理URL中使用特殊字符

3. **性能问题**
   - 减少代理池大小
   - 增加健康检查间隔
   - 使用更快的代理

### 调试方法

1. **查看代理统计**：
```python
proxy_manager = ProxyManager()
stats = proxy_manager.get_stats()
print(stats)
```

2. **手动测试代理**：
```python
proxy = ProxyInfo(url="http://test-proxy:8080")
success, response_time = proxy_manager.test_proxy(proxy)
```

3. **查看详细日志**：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 最佳实践

### 1. 代理选择
- **rambler.ru**: 优先选择欧洲/美国代理
- **稳定性**: 选择数据中心代理而不是住宅代理
- **速度**: 选择响应时间<2秒的代理

### 2. 维护策略
- **定期更新**: 每周更新代理列表
- **监控告警**: 代理池可用率<50%时告警
- **备用方案**: 准备多个代理来源

### 3. 成本控制
- **按需使用**: 只在需要时启用代理
- **智能切换**: 优先使用免费代理，付费作为备用
- **使用量限制**: 避免过度消耗付费代理

## 扩展功能

### 计划中的功能
- [ ] 代理自动采集脚本
- [ ] 代理性能监控面板
- [ ] 多线程健康检查
- [ ] 代理IP地理位置分析
- [ ] 智能代理推荐算法

这个代理池系统为解决 rambler.ru 邮箱访问问题提供了完整的解决方案，既保证了连接的稳定性，又提供了灵活的配置和管理能力。
