"""
代理池管理器 - 支持轮询重试机制
用于解决rambler.ru等邮箱的网络访问限制问题
"""

import time
import random
import requests
import threading
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProxyInfo:
    """代理信息"""
    url: str                    # 代理URL (http://ip:port 或 ip:port)
    protocol: str = 'http'      # 协议类型
    country: str = 'unknown'    # 国家
    anonymity: str = 'unknown'  # 匿名级别
    username: str = ''          # 代理用户名
    password: str = ''          # 代理密码
    response_time: float = 0.0  # 响应时间(秒)
    last_check: Optional[datetime] = None  # 最后检查时间
    status: str = 'unknown'     # 状态: active/inactive/failed
    fail_count: int = 0         # 失败次数
    success_count: int = 0      # 成功次数

    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.fail_count + self.success_count
        return self.success_count / total if total > 0 else 0.0

    @property
    def is_active(self) -> bool:
        """是否活跃"""
        return self.status == 'active' and self.fail_count < 3

    def test_protocols(self, test_url: str = "http://httpbin.org/ip", timeout: int = 10) -> str:
        """测试代理协议类型，返回最适合的协议"""
        import requests
        import socks
        import socket

        if ':' not in self.url:
            return 'unknown'

        ip, port_str = self.url.split(':')
        port = int(port_str)

        protocols_to_test = ['socks5', 'http']
        working_protocols = []

        for protocol in protocols_to_test:
            try:
                # 设置代理
                if protocol == 'socks5':
                    socks.set_default_proxy(socks.SOCKS5, ip, port,
                                          username=self.username,
                                          password=self.password)
                elif protocol == 'http':
                    socks.set_default_proxy(socks.HTTP, ip, port,
                                          username=self.username,
                                          password=self.password)

                # 创建代理化的session
                session = requests.Session()
                session.proxies = {
                    'http': f'{protocol}://{self.username}:{self.password}@{ip}:{port}',
                    'https': f'{protocol}://{self.username}:{self.password}@{ip}:{port}'
                }

                # 测试连接
                response = session.get(test_url, timeout=timeout)
                if response.status_code == 200:
                    working_protocols.append(protocol)
                    print(f"代理 {ip}:{port} 支持 {protocol} 协议")
                    break  # 找到第一个工作的协议就停止

            except Exception as e:
                print(f"代理 {ip}:{port} {protocol} 协议测试失败: {str(e)[:50]}...")
                continue
            finally:
                # 清理代理设置
                socks.setdefaultproxy()

        # 返回最佳协议
        if 'socks5' in working_protocols:
            return 'socks5'  # 优先选择SOCKS5，因为它支持更多类型的连接
        elif 'http' in working_protocols:
            return 'http'
        else:
            return 'unknown'

class ProxyManager:
    """代理池管理器"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.proxies: List[ProxyInfo] = []
        self.current_index = 0
        self.lock = threading.Lock()

        # 启动健康检查线程
        self.health_check_thread = None
        self.running = False

        # 加载代理
        self.load_proxies()

        # 启动健康检查
        self.start_health_check()

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'proxy_file': 'config/proxy_list.txt',
            'max_fail_count': 3,
            'health_check_interval': 300,  # 5分钟
            'health_check_timeout': 10,
            'rotation_mode': 'round_robin',  # round_robin/random
            'test_url': 'http://httpbin.org/ip',
            # 协议测试配置
            'auto_test_protocols': False,  # 是否自动测试协议
            'protocol_test_url': 'http://httpbin.org/ip',  # 协议测试URL
            'protocol_test_timeout': 10,  # 协议测试超时时间
        }

    def load_proxies(self):
        """加载代理列表"""
        try:
            with open(self.config['proxy_file'], 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxy_info = self._parse_proxy_line(line)
                    if proxy_info:
                        self.proxies.append(proxy_info)

            logger.info(f"加载了 {len(self.proxies)} 个代理")

            # 自动测试代理协议（如果启用）
            if self.config.get('auto_test_protocols', False):
                logger.info("开始自动测试代理协议...")
                self.test_all_protocols()

        except FileNotFoundError:
            logger.warning(f"代理配置文件不存在: {self.config['proxy_file']}")
            self._create_default_proxy_file()
        except Exception as e:
            logger.error(f"加载代理配置失败: {e}")

    def _parse_proxy_line(self, line: str) -> Optional[ProxyInfo]:
        """解析代理行"""
        try:
            # 支持格式: http://ip:port 或 http://ip:port#country 或 http://user:pass@ip:port
            if '#' in line:
                url_part, country = line.split('#', 1)
            else:
                url_part = line
                country = 'unknown'

            username = ''
            password = ''

            # 解析认证信息和协议
            if '@' in url_part:
                # 格式: protocol://user:pass@ip:port
                auth_part, addr_part = url_part.split('@', 1)
                url = addr_part  # ip:port部分

                if ':' in auth_part:
                    if auth_part.startswith('http://'):
                        protocol = 'http'
                        username, password = auth_part[7:].split(':', 1)
                    elif auth_part.startswith('https://'):
                        protocol = 'https'
                        username, password = auth_part[8:].split(':', 1)
                    elif auth_part.startswith('socks4://'):
                        protocol = 'socks4'
                        username, password = auth_part[9:].split(':', 1)
                    elif auth_part.startswith('socks5://'):
                        protocol = 'socks5'
                        username, password = auth_part[9:].split(':', 1)
                    else:
                        # 无协议前缀的认证信息
                        username, password = auth_part.split(':', 1)
                        protocol = 'http'  # 默认
                else:
                    # 只有用户名没有密码
                    if auth_part.startswith('http://'):
                        protocol = 'http'
                        username = auth_part[7:]
                    elif auth_part.startswith('https://'):
                        protocol = 'https'
                        username = auth_part[8:]
                    elif auth_part.startswith('socks4://'):
                        protocol = 'socks4'
                        username = auth_part[9:]
                    elif auth_part.startswith('socks5://'):
                        protocol = 'socks5'
                        username = auth_part[9:]
                    else:
                        protocol = 'http'
                        username = auth_part
                    password = ''
            else:
                # 无认证信息的URL
                username = ''
                password = ''
                if url_part.startswith('http://'):
                    protocol = 'http'
                    url = url_part[7:]
                elif url_part.startswith('https://'):
                    protocol = 'https'
                    url = url_part[8:]
                elif url_part.startswith('socks4://'):
                    protocol = 'socks4'
                    url = url_part[9:]
                elif url_part.startswith('socks5://'):
                    protocol = 'socks5'
                    url = url_part[9:]
                else:
                    # 默认
                    url = url_part
                    protocol = 'http'

            return ProxyInfo(
                url=url,
                protocol=protocol,
                country=country.strip(),
                username=username,
                password=password,
                status='active'  # 默认设置为活跃状态，使其可以被使用
            )
        except Exception as e:
            logger.warning(f"解析代理行失败: {line}, 错误: {e}")
            return None

    def _create_default_proxy_file(self):
        """创建默认的代理配置文件"""
        try:
            import os
            os.makedirs('config', exist_ok=True)

            default_content = """# 代理列表配置文件
# 格式: protocol://ip:port 或 protocol://ip:port#country
# 示例:
# http://123.45.67.89:8080
# https://98.76.54.32:3128#US
# socks5://192.168.1.1:1080

# 这里添加你的代理IP列表
# 注意：rambler.ru邮箱建议使用欧洲或美国代理

"""

            with open(self.config['proxy_file'], 'w', encoding='utf-8') as f:
                f.write(default_content)

            logger.info(f"创建了默认代理配置文件: {self.config['proxy_file']}")
        except Exception as e:
            logger.error(f"创建默认代理配置文件失败: {e}")

    def add_proxy(self, proxy_info: ProxyInfo):
        """添加单个代理"""
        with self.lock:
            self.proxies.append(proxy_info)
            logger.info(f"添加代理: {proxy_info.url}")

    def add_proxies_from_list(self, proxy_list: List[str]):
        """从字符串列表添加多个代理"""
        for proxy_str in proxy_list:
            proxy_info = self._parse_proxy_line(proxy_str)
            if proxy_info:
                self.add_proxy(proxy_info)

    def remove_proxy(self, proxy_info: ProxyInfo):
        """移除代理"""
        with self.lock:
            if proxy_info in self.proxies:
                self.proxies.remove(proxy_info)
                logger.info(f"移除代理: {proxy_info.url}")

    def get_proxy_rotation(self) -> List[ProxyInfo]:
        """获取代理轮询列表"""
        with self.lock:
            # 只返回活跃的代理
            active_proxies = [p for p in self.proxies if p.is_active]

            if not active_proxies:
                logger.warning("没有活跃的代理，返回所有代理")
                active_proxies = self.proxies

            if not active_proxies:
                return []

            if self.config['rotation_mode'] == 'random':
                # 随机模式
                return random.sample(active_proxies, len(active_proxies))
            else:
                # 轮询模式：从当前位置开始
                if self.current_index >= len(active_proxies):
                    self.current_index = 0

                rotation = active_proxies[self.current_index:] + active_proxies[:self.current_index]
                self.current_index = (self.current_index + 1) % len(active_proxies) if active_proxies else 0
                return rotation

    def get_best_proxy(self) -> Optional[ProxyInfo]:
        """获取最佳代理（响应最快且成功率最高）"""
        with self.lock:
            active_proxies = [p for p in self.proxies if p.is_active]
            if not active_proxies:
                return None

            # 按成功率和响应时间排序
            sorted_proxies = sorted(active_proxies,
                                  key=lambda p: (p.success_rate, -p.response_time),
                                  reverse=True)
            return sorted_proxies[0]

    def mark_proxy_success(self, proxy: ProxyInfo):
        """标记代理成功"""
        with self.lock:
            proxy.success_count += 1
            proxy.fail_count = 0
            proxy.status = 'active'
            proxy.last_check = datetime.now()

    def mark_proxy_failed(self, proxy: ProxyInfo):
        """标记代理失败"""
        with self.lock:
            proxy.fail_count += 1
            if proxy.fail_count >= self.config['max_fail_count']:
                proxy.status = 'failed'
                logger.warning(f"代理失败次数过多，已禁用: {proxy.url}")
            proxy.last_check = datetime.now()

    def test_proxy(self, proxy: ProxyInfo) -> Tuple[bool, float]:
        """测试代理可用性"""
        try:
            start_time = time.time()

            response = requests.get(
                self.config['test_url'],
                proxies={proxy.protocol: proxy.url},
                timeout=self.config['health_check_timeout'],
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )

            response_time = time.time() - start_time

            if response.status_code == 200:
                return True, response_time
            else:
                return False, response_time

        except Exception as e:
            logger.debug(f"代理测试失败 {proxy.url}: {e}")
            return False, 0.0

    def health_check_all(self):
        """健康检查所有代理"""
        logger.info("开始代理健康检查...")

        for proxy in self.proxies:
            success, response_time = self.test_proxy(proxy)

            if success:
                self.mark_proxy_success(proxy)
                proxy.response_time = response_time
                logger.debug(f"✅ 代理正常: {proxy.url} ({response_time:.2f}s)")
            else:
                self.mark_proxy_failed(proxy)
                logger.debug(f"❌ 代理失败: {proxy.url}")

        active_count = len([p for p in self.proxies if p.is_active])
        logger.info(f"健康检查完成，活跃代理: {active_count}/{len(self.proxies)}")

    def test_all_protocols(self, max_workers: int = 10):
        """批量测试所有代理的协议类型"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        if not self.proxies:
            logger.warning("没有代理需要测试")
            return

        logger.info(f"开始测试 {len(self.proxies)} 个代理的协议类型...")

        test_url = self.config.get('protocol_test_url', 'http://httpbin.org/ip')
        timeout = self.config.get('protocol_test_timeout', 10)

        def test_single_proxy(proxy_info):
            """测试单个代理的协议"""
            try:
                logger.debug(f"测试代理协议: {proxy_info.url}")
                detected_protocol = proxy_info.test_protocols(test_url, timeout)
                if detected_protocol != 'unknown':
                    proxy_info.protocol = detected_protocol
                    proxy_info.status = 'active'
                    logger.info(f"代理 {proxy_info.url} 检测为 {detected_protocol} 协议")
                    return proxy_info, True
                else:
                    proxy_info.status = 'failed'
                    logger.warning(f"代理 {proxy_info.url} 协议检测失败")
                    return proxy_info, False
            except Exception as e:
                logger.error(f"测试代理 {proxy_info.url} 时出错: {e}")
                proxy_info.status = 'failed'
                return proxy_info, False

        # 使用线程池进行并发测试
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(test_single_proxy, proxy) for proxy in self.proxies]
            successful_tests = 0

            for future in as_completed(futures):
                proxy_info, success = future.result()
                if success:
                    successful_tests += 1

        logger.info(f"协议测试完成: {successful_tests}/{len(self.proxies)} 个代理成功检测到协议")

    def start_health_check(self):
        """启动健康检查线程"""
        if self.running:
            return

        self.running = True

        def health_check_loop():
            while self.running:
                try:
                    self.health_check_all()
                except Exception as e:
                    logger.error(f"健康检查异常: {e}")

                time.sleep(self.config['health_check_interval'])

        self.health_check_thread = threading.Thread(target=health_check_loop, daemon=True)
        self.health_check_thread.start()
        logger.info("代理健康检查线程已启动")

    def stop_health_check(self):
        """停止健康检查"""
        self.running = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)

    def get_stats(self) -> Dict:
        """获取代理池统计信息"""
        with self.lock:
            total = len(self.proxies)
            active = len([p for p in self.proxies if p.is_active])
            failed = len([p for p in self.proxies if p.status == 'failed'])

            return {
                'total_proxies': total,
                'active_proxies': active,
                'failed_proxies': failed,
                'success_rates': {p.url: p.success_rate for p in self.proxies},
                'avg_response_time': sum(p.response_time for p in self.proxies if p.response_time > 0) / max(1, len([p for p in self.proxies if p.response_time > 0]))
            }

    def __len__(self) -> int:
        """返回代理数量"""
        return len(self.proxies)

    def __str__(self) -> str:
        """字符串表示"""
        stats = self.get_stats()
        return f"ProxyManager(active: {stats['active_proxies']}/{stats['total_proxies']})"
