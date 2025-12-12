"""
Surf AI 自动登录工具 - 使用IMAP获取验证码并自动登录
支持邮箱+验证码登录流程
支持rambler.ru邮箱的特殊激活流程（邮箱激活+重新登录）
"""
import asyncio
import imaplib
import email
import re
import time
import ssl
import socket
from datetime import datetime
from email.mime.text import MIMEText
from email.header import decode_header
from playwright.async_api import async_playwright
from pathlib import Path
import json
from typing import Optional, Tuple
from dataclasses import dataclass
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

# 导入Selenium相关模块（用于rambler.ru邮箱激活）
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import urllib.parse

# 导入代理管理器
from proxy_manager import ProxyManager

@dataclass
class EmailConfig:
    """邮箱配置"""
    server: str
    port: int
    username: str
    password: str

@dataclass
class SurfAccount:
    """Surf账号信息"""
    email: str
    email_password: str  # 邮箱密码，不是Surf密码
    email_server: str = "imap.gmail.com"
    email_port: int = 993

class SurfAutoLogin:
    """Surf自动登录工具"""

    def __init__(self, account: SurfAccount):
        self.account = account
        self.imap = None
        self.playwright = None
        self.browser = None
        self.page = None

        # 检测是否为rambler.ru邮箱（需要特殊激活流程）
        self.is_rambler_email = 'rambler.ru' in self.account.email.lower()

        # 初始化代理管理器
        self.proxy_manager = ProxyManager()

        # 保存浏览器状态的目录
        self.state_dir = Path("data/browser_state")
        self.state_dir.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self):
        await self._init_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._cleanup()

    async def _init_browser(self):
        """初始化浏览器"""
        print("🚀 初始化浏览器...")
        self.playwright = await async_playwright().start()

        # 尝试使用系统Chrome
        try:
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # 显示浏览器便于观察
                channel="chrome",
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            print("✓ 使用系统Chrome浏览器")
        except Exception as e:
            print(f"⚠ Chrome启动失败，尝试使用Chromium: {e}")
            self.browser = await self.playwright.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            print("✓ 使用Chromium浏览器")

    async def _cleanup(self):
        """清理资源"""
        if self.imap:
            try:
                self.imap.logout()
            except:
                pass

        if self.browser:
            await self.browser.close()

        if self.playwright:
            await self.playwright.stop()

    def _connect_imap(self) -> bool:
        """连接到IMAP服务器"""
        try:
            # 检查是否为rambler.ru邮箱，使用特殊连接逻辑
            email_domain = self.account.email.split('@')[1].lower() if '@' in self.account.email else ''
            if 'rambler.ru' in email_domain:
                print(f"📧 检测到rambler.ru邮箱，使用专用连接逻辑")
                return self._connect_rambler_imap()

            print(f"📧 连接到 {self.account.email_server}:{self.account.email_port}")

            # 设置socket超时，避免无限等待
            socket.setdefaulttimeout(30)
            
            # 尝试多种连接方式
            connection_success = False
            last_error = None
            
            # 根据邮箱类型确定提示信息
            email_domain = self.account.email.split('@')[1].lower() if '@' in self.account.email else ''
            is_russian_email = email_domain.endswith('.ru') or 'mail.ru' in email_domain or 'yandex' in email_domain
            email_type_hint = "俄罗斯邮箱" if is_russian_email else ("Outlook账户" if 'outlook' in email_domain or 'hotmail' in email_domain else "邮箱账户")
            
            # 方式1: 使用PROTOCOL_TLS（兼容性更好）
            try:
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
                ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                ssl_context.maximum_version = ssl.TLSVersion.MAXIMUM_SUPPORTED
                ssl_context.check_hostname = True
                ssl_context.verify_mode = ssl.CERT_REQUIRED
                ssl_context.load_default_certs()
                
                self.imap = imaplib.IMAP4_SSL(
                    self.account.email_server, 
                    self.account.email_port,
                    ssl_context=ssl_context,
                    timeout=30
                )
                connection_success = True
                print("✓ 使用PROTOCOL_TLS连接成功")
            except Exception as e1:
                last_error = e1
                print(f"⚠ PROTOCOL_TLS连接失败: {e1}")
                
                # 方式2: 使用PROTOCOL_TLS_CLIENT（Python 3.10+）
                try:
                    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                    ssl_context.check_hostname = True
                    ssl_context.verify_mode = ssl.CERT_REQUIRED
                    ssl_context.load_default_certs()
                    
                    self.imap = imaplib.IMAP4_SSL(
                        self.account.email_server, 
                        self.account.email_port,
                        ssl_context=ssl_context,
                        timeout=30
                    )
                    connection_success = True
                    print("✓ 使用PROTOCOL_TLS_CLIENT连接成功")
                except Exception as e2:
                    last_error = e2
                    print(f"⚠ PROTOCOL_TLS_CLIENT连接失败: {e2}")
                    
                    # 方式3: 使用默认SSL上下文
                    try:
                        ssl_context = ssl.create_default_context()
                        self.imap = imaplib.IMAP4_SSL(
                            self.account.email_server, 
                            self.account.email_port,
                            ssl_context=ssl_context,
                            timeout=30
                        )
                        connection_success = True
                        print("✓ 使用默认SSL上下文连接成功")
                    except Exception as e3:
                        last_error = e3
                        print(f"⚠ 默认SSL上下文连接失败: {e3}")
                        
                        # 方式4: 不验证证书（用于测试）
                        try:
                            ssl_context_loose = ssl.create_default_context()
                            ssl_context_loose.check_hostname = False
                            ssl_context_loose.verify_mode = ssl.CERT_NONE
                            
                            self.imap = imaplib.IMAP4_SSL(
                                self.account.email_server, 
                                self.account.email_port,
                                ssl_context=ssl_context_loose,
                                timeout=30
                            )
                            connection_success = True
                            print("✓ 使用宽松SSL设置连接成功（不验证证书）")
                        except Exception as e4:
                            last_error = e4
                            print(f"⚠ 宽松SSL设置连接失败: {e4}")
                            
                            # 方式5: 使用PROTOCOL_TLSv1_2（明确指定TLS 1.2，如果可用）
                            try:
                                # PROTOCOL_TLSv1_2 在Python 3.6+中可用
                                if hasattr(ssl, 'PROTOCOL_TLSv1_2'):
                                    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                                    ssl_context.check_hostname = True
                                    ssl_context.verify_mode = ssl.CERT_REQUIRED
                                    ssl_context.load_default_certs()
                                    
                                    self.imap = imaplib.IMAP4_SSL(
                                        self.account.email_server, 
                                        self.account.email_port,
                                        ssl_context=ssl_context,
                                        timeout=30
                                    )
                                    connection_success = True
                                    print("✓ 使用PROTOCOL_TLSv1_2连接成功")
                                else:
                                    raise Exception("PROTOCOL_TLSv1_2 not available")
                            except Exception as e5:
                                last_error = e5
                                if "not available" not in str(e5):
                                    print(f"⚠ PROTOCOL_TLSv1_2连接失败: {e5}")
                                
                                # 方式6: 手动创建socket然后包装SSL（最底层方式）
                                try:
                                    sock = socket.create_connection(
                                        (self.account.email_server, self.account.email_port),
                                        timeout=30
                                    )
                                    ssl_context = ssl.create_default_context()
                                    ssl_sock = ssl_context.wrap_socket(sock, server_hostname=self.account.email_server)
                                    self.imap = imaplib.IMAP4()
                                    self.imap.sock = ssl_sock
                                    self.imap.file = ssl_sock.makefile('rb')
                                    connection_success = True
                                    print("✓ 使用手动socket+SSL包装连接成功")
                                except Exception as e6:
                                    last_error = e6
                                    print(f"⚠ 手动socket+SSL包装连接失败: {e6}")
                                    
                                    # 方式7: 完全默认（不指定任何SSL参数）
                                    try:
                                        self.imap = imaplib.IMAP4_SSL(
                                            self.account.email_server, 
                                            self.account.email_port,
                                            timeout=30
                                        )
                                        connection_success = True
                                        print("✓ 使用完全默认连接成功")
                                    except Exception as e7:
                                        last_error = e7
                                        print(f"⚠ 完全默认连接失败: {e7}")
            
            if not connection_success:
                print(f"✗ 所有IMAP连接方式都失败")
                print(f"  最后错误: {last_error}")
                print(f"  提示: 请检查以下几点:")
                print(f"    1. 确保{email_type_hint}已启用IMAP访问")
                if is_russian_email:
                    print(f"    2. 俄罗斯邮箱通常不需要应用密码，直接使用登录密码")
                else:
                    print(f"    2. 如果启用了两步验证，需要使用应用密码")
                print(f"    3. 检查网络代理设置是否影响IMAP连接")
                print(f"    4. 尝试关闭VPN/代理后重试")
                print(f"    5. 确认IMAP服务器地址正确: {self.account.email_server}:{self.account.email_port}")
                return False
            
            # 登录
            print(f"🔐 尝试登录邮箱: {self.account.email}")
            self.imap.login(self.account.email, self.account.email_password)
            self.imap.select('inbox')
            print("✓ IMAP登录成功")
            return True
        except imaplib.IMAP4.error as e:
            print(f"✗ IMAP认证失败: {e}")
            print(f"  提示: 请检查邮箱密码是否正确，或是否需要使用应用密码")
            return False
        except Exception as e:
            print(f"✗ IMAP连接或登录失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # 恢复默认socket超时
            socket.setdefaulttimeout(None)

    def _extract_verification_code(self, email_content: str) -> Optional[str]:
        """从邮件内容中提取验证码（6位数字）"""
        # 优先匹配纯数字的6位验证码
        patterns = [
            # 纯数字6位验证码（最优先）
            r'\b(\d{6})\b',  # 独立的6位数字
            r'verification code[:\s]*is[:\s]*(\d{6})',  # verification code is: 123456
            r'verification code[:\s]*(\d{6})',           # verification code: 123456
            r'code[:\s]*is[:\s]*(\d{6})',                # code is: 123456
            r'code[:\s]*(\d{6})',                        # code: 123456
            r'verify[:\s]*(\d{6})',                      # verify: 123456
            r'验证码[:\s]*(\d{6})',                      # 中文：验证码: 123456
            r'验证码[:\s]*是[:\s]*(\d{6})',              # 验证码是: 123456
            r'Your code is[:\s]*(\d{6})',                # Your code is: 123456
            r'Your verification code[:\s]*(\d{6})',      # Your verification code: 123456
            # 如果上面都没匹配到，尝试匹配字母数字组合（但优先数字）
            r'verification code[:\s]*is[:\s]*([0-9]{6})',  # 确保是数字
            r'code[:\s]*([0-9]{6})',                       # 确保是数字
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, email_content, re.IGNORECASE)
            for match in matches:
                code = match.group(1)
                # 确保是6位数字
                if code.isdigit() and len(code) == 6:
                    print(f"✓ 提取到验证码: {code}")
                    return code

        # 如果都没匹配到，尝试查找所有6位数字
        all_digits = re.findall(r'\b\d{6}\b', email_content)
        if all_digits:
            # 选择第一个6位数字作为验证码
            code = all_digits[0]
            print(f"✓ 提取到验证码（备用方法）: {code}")
            return code

        print("✗ 未能提取到6位数字验证码")
        print(f"📄 邮件内容预览: {email_content[:500]}")
        return None

    def _get_latest_surf_email(self, within_minutes: int = 5, start_time: Optional[datetime] = None) -> Optional[Tuple[str, str]]:
        """获取最新的Surf验证码邮件（只获取start_time之后或最近within_minutes分钟内的邮件）"""
        try:
            from datetime import datetime, timedelta, timezone
            
            # 确保IMAP连接已选择邮箱（必须在SELECTED状态才能搜索）
            if not self.imap:
                print("✗ IMAP连接未建立")
                return None
            
            # 确保进入 INBOX（状态从 AUTH -> SELECTED）
            try:
                status, data = self.imap.select('INBOX')
                if status != 'OK':
                    print(f"⚠️ 选择INBOX失败: {status}，尝试重新连接...")
                    if not self._connect_imap():
                        print("✗ 重新连接IMAP失败")
                        return None
                    # 重新连接后再次选择
                    status, data = self.imap.select('INBOX')
                    if status != 'OK':
                        raise Exception(f"无法选择INBOX: {status}")
            except Exception as e:
                print(f"✗ 选择邮箱失败: {e}")
                # 尝试重新连接
                if not self._connect_imap():
                    print("✗ 重新连接IMAP失败")
                    return None
                # 重新连接后再次尝试选择
                try:
                    status, data = self.imap.select('INBOX')
                    if status != 'OK':
                        raise Exception(f"重新连接后仍无法选择INBOX: {status}")
                except Exception as e2:
                    print(f"✗ 重新连接后选择邮箱仍失败: {e2}")
                    return None
            
            # 计算时间范围
            if start_time:
                # 使用指定的开始时间（只获取这个时间之后的邮件）
                # 确保start_time是naive datetime，如果没有时区信息则添加本地时区
                if start_time.tzinfo is None:
                    # naive datetime，保持原样
                    cutoff_time = start_time
                else:
                    # aware datetime，转换为naive（使用本地时间）
                    cutoff_time = start_time.replace(tzinfo=None)
            else:
                # 使用相对时间（只获取最近within_minutes分钟的邮件）
                now = datetime.now()
                cutoff_time = now - timedelta(minutes=within_minutes)
            
            # IMAP日期格式：DD-MMM-YYYY
            cutoff_date_str = cutoff_time.strftime("%d-%b-%Y")
            
            # 首先搜索来自Surf的未读邮件（最近within_minutes分钟内）
            search_criteria = f'(FROM "noreply@asksurf.ai" UNSEEN SINCE "{cutoff_date_str}")'
            status, messages = self.imap.search(None, search_criteria)
            
            if status != 'OK' or not messages[0]:
                # 如果没找到，搜索包含Surf关键词的未读邮件
                search_criteria = f'(UNSEEN SINCE "{cutoff_date_str}" (OR SUBJECT "Surf" SUBJECT "surf" FROM "noreply@asksurf.ai"))'
                status, messages = self.imap.search(None, search_criteria)
            
            if status != 'OK' or not messages[0]:
                # 最后尝试搜索验证码相关的未读邮件
                search_criteria = f'(UNSEEN SINCE "{cutoff_date_str}" (OR SUBJECT "verification" SUBJECT "code" SUBJECT "验证码" SUBJECT "verify"))'
                status, messages = self.imap.search(None, search_criteria)

            if status != 'OK' or not messages[0]:
                print(f"⚠ 未找到最近{within_minutes}分钟内的新验证码邮件")
                return None

            # 获取所有邮件ID，直接取最新的（邮件ID通常是递增的，最新的在最后）
            email_ids = messages[0].split()
            if not email_ids:
                print("⚠ 未找到新的验证码邮件")
                return None

            # 优化：直接取最新的邮件ID（通常是最后一个），只检查时间是否符合要求
            # 这样可以避免遍历所有邮件，大大提高速度
            latest_email_id = email_ids[-1]  # 最新的邮件ID
            
            # 快速检查最新邮件的时间
            status, msg_data = self.imap.fetch(latest_email_id, '(RFC822)')
            if status != 'OK':
                print("✗ 获取最新邮件失败")
                return None
            
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            date_str = email_message.get("Date")
            
            if date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    email_time = parsedate_to_datetime(date_str)
                    
                    # 统一时区处理：将aware datetime转换为naive datetime（本地时间）
                    if email_time.tzinfo is not None:
                        # aware datetime，转换为本地时间的naive datetime
                        email_time = email_time.astimezone().replace(tzinfo=None)
                    
                    # 检查邮件时间是否在要求范围内（允许10秒误差）
                    time_diff = (cutoff_time - email_time).total_seconds()
                    if time_diff > 10:  # 邮件时间早于开始时间超过10秒
                        print(f"⚠ 最新邮件时间: {email_time.strftime('%Y-%m-%d %H:%M:%S')}，早于开始时间 {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}，跳过")
                        # 如果最新邮件太旧，尝试从后往前找符合时间要求的
                        found_valid = False
                        for email_id in reversed(email_ids[-10:]):  # 只检查最近10封邮件
                            status, msg_data = self.imap.fetch(email_id, '(RFC822)')
                            if status != 'OK':
                                continue
                            email_body = msg_data[0][1]
                            email_message = email.message_from_bytes(email_body)
                            date_str = email_message.get("Date")
                            if date_str:
                                try:
                                    email_time_check = parsedate_to_datetime(date_str)
                                    # 统一时区处理
                                    if email_time_check.tzinfo is not None:
                                        email_time_check = email_time_check.astimezone().replace(tzinfo=None)
                                    
                                    # 允许10秒误差：邮件时间在开始时间之前10秒内也算有效
                                    time_diff_check = (cutoff_time - email_time_check).total_seconds()
                                    if time_diff_check <= 10:  # 邮件时间在开始时间之前10秒内或之后
                                        latest_email_id = email_id
                                        found_valid = True
                                        print(f"✓ 找到符合时间要求的邮件: {email_time_check.strftime('%Y-%m-%d %H:%M:%S')}")
                                        break
                                except Exception as e:
                                    continue
                        
                        if not found_valid:
                            print(f"⚠ 未找到开始时间 {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')} 之后的邮件")
                            return None
                    else:
                        print(f"✓ 邮件时间: {email_time.strftime('%Y-%m-%d %H:%M:%S')}，符合要求（>= {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}）")
                except Exception as e:
                    # 如果时间解析失败，跳过这封邮件，不返回
                    print(f"⚠ 解析邮件时间失败: {e}，跳过此邮件")
                    return None

            # 获取邮件内容
            status, msg_data = self.imap.fetch(latest_email_id, '(RFC822)')
            if status != 'OK':
                print("✗ 获取邮件内容失败")
                return None

            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)

            # 解码主题
            subject = decode_header(email_message["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()

            # 获取邮件时间并显示，并再次验证时间
            date_str = email_message.get("Date")
            email_time_str = ""
            email_time_final = None
            if date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    email_time_final = parsedate_to_datetime(date_str)
                    # 统一时区处理
                    if email_time_final.tzinfo is not None:
                        email_time_final = email_time_final.astimezone().replace(tzinfo=None)
                    email_time_str = f" ({email_time_final.strftime('%Y-%m-%d %H:%M:%S')})"
                    
                    # 最终验证：确保邮件时间符合要求（允许10秒误差）
                    if start_time:
                        time_diff_final = (cutoff_time - email_time_final).total_seconds()
                        if time_diff_final > 10:  # 邮件时间早于开始时间超过10秒
                            print(f"⚠ 最终验证失败: 邮件时间 {email_time_final.strftime('%Y-%m-%d %H:%M:%S')} 早于开始时间 {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            return None
                except:
                    pass

            # 获取邮件正文
            content = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        content += part.get_payload(decode=True).decode()
            else:
                content = email_message.get_payload(decode=True).decode()

            print(f"📧 获取到邮件: {subject}{email_time_str}")
            return subject, content

        except Exception as e:
            print(f"✗ 获取邮件失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_verification_code(self, max_attempts: int = 20, wait_seconds: int = 2) -> Optional[str]:
        """获取验证码，带重试机制（只获取开始等待之后的邮件，快速轮询）"""
        if not self._connect_imap():
            return None

        print("⏳ 等待验证码邮件...")
        
        # 记录开始时间，只获取这个时间之后的邮件
        from datetime import datetime
        start_time = datetime.now()
        print(f"📅 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}，只获取此时间之后的邮件")

        for attempt in range(max_attempts):
            print(f"🔄 第 {attempt + 1}/{max_attempts} 次尝试获取验证码...")

            # 只获取start_time之后的邮件
            email_data = self._get_latest_surf_email(within_minutes=10, start_time=start_time)
            if email_data:
                subject, content = email_data
                code = self._extract_verification_code(content)
                if code:
                    # 验证验证码格式：必须是6位数字
                    if code.isdigit() and len(code) == 6:
                        return code
                    else:
                        print(f"⚠️ 提取的验证码格式不正确: {code}，继续尝试...")

            if attempt < max_attempts - 1:
                # 快速轮询，减少等待时间
                time.sleep(wait_seconds)

        print("✗ 获取验证码超时")
        return None

    async def _navigate_to_login(self):
        """导航到登录页面"""
        print("🌐 访问Surf主页面...")
        # 更长超时+重试，并在页面关闭时重建
        nav_url = "https://asksurf.ai/chat"
        nav_success = False
        for attempt in range(3):
            try:
                # 如果页面被关闭，则重建
                try:
                    if not self.page or self.page.is_closed():
                        self.page = await self.browser.new_page()
                except Exception as e:
                    print(f"⚠️ 页面状态检查失败，重建页面: {e}")
                    self.page = await self.browser.new_page()

                await self.page.goto(nav_url, wait_until="domcontentloaded", timeout=1800000)
                nav_success = True
                break
            except (PlaywrightTimeoutError,) as e:
                print(f"⚠️ 导航超时({attempt+1}/3): {e}")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"⚠️ 导航异常({attempt+1}/3): {e}")
                await asyncio.sleep(1)

        if not nav_success:
            print("✗ 无法导航到登录页，终止自动登录")
            raise PlaywrightTimeoutError("Navigation to Surf chat failed after retries")

        # 智能等待页面关键元素加载完成
        print("⏳ 智能等待页面加载...")
        max_wait_time = 120000  # 最多等待2分钟
        check_interval = 2000   # 每2秒检查一次
        elapsed = 0

        while elapsed < max_wait_time:
            try:
                # 检查页面是否包含关键的登录相关元素
                login_indicators = [
                    'button:has-text("登录")',
                    'button:has-text("Login")',
                    'button:has-text("Sign in")',
                    'a:has-text("登录")',
                    'a:has-text("Login")',
                    'nav',  # 导航栏
                    'header',  # 页头
                    '.navbar',  # 导航栏类
                    '[role="navigation"]'  # 导航角色
                ]

                page_ready = False
                for indicator in login_indicators:
                    try:
                        element = await self.page.query_selector(indicator)
                        if element and await element.is_visible():
                            print(f"✅ 检测到页面元素: {indicator}")
                            page_ready = True
                            break
                    except:
                        continue

                if page_ready:
                    print("✅ 页面已完全加载")
                    break

            except Exception as e:
                print(f"⚠️ 检查页面状态时出错: {e}")

            await self.page.wait_for_timeout(check_interval)
            elapsed += check_interval

        if elapsed >= max_wait_time:
            print("⚠️ 页面加载超时，继续执行...")

        # 最后等待一小段时间确保稳定性
        await self.page.wait_for_timeout(1000)

    async def _fill_email_and_send_code(self, email: str) -> bool:
        """填写邮箱并发送验证码"""
        try:
            print("📝 填写邮箱并发送验证码...")

            # 等待登录表单出现
            form_max_wait = 30000  # 最多等待30秒
            form_check_interval = 1000  # 每1秒检查一次
            form_elapsed = 0

            print("⏳ 等待登录表单完全加载 (最多30秒)...")

            while form_elapsed < form_max_wait:
                # 检查登录表单的关键元素
                form_indicators = [
                    'input[type="email"]',
                    'input[name="email"]',
                    'input[placeholder*="email" i]',
                    'input[placeholder*="邮箱" i]',
                    'input[type="text"]',
                    '.login-form',
                    '[role="dialog"]',
                    'form'
                ]

                form_ready = False
                for form_indicator in form_indicators:
                    try:
                        # 检查主页面
                        form_element = await self.page.query_selector(form_indicator)
                        if form_element and await form_element.is_visible():
                            print(f"✅ 检测到登录表单元素(主页面): {form_indicator}")
                            form_ready = True
                            break

                        # 检查iframe
                        iframes = await self.page.query_selector_all('iframe')
                        for iframe in iframes:
                            try:
                                frame = await iframe.content_frame()
                                if frame:
                                    form_element = await frame.query_selector(form_indicator)
                                    if form_element and await form_element.is_visible():
                                        print(f"✅ 检测到登录表单元素(iframe): {form_indicator}")
                                        form_ready = True
                                        break
                            except:
                                continue

                        if form_ready:
                            break

                    except:
                        continue

                if form_ready:
                    print("✅ 登录表单已准备就绪")
                    await self.page.wait_for_timeout(1000)  # 额外等待1秒确保稳定
                    break

                await self.page.wait_for_timeout(form_check_interval)
                form_elapsed += form_check_interval

            if not form_ready:
                print("⚠️ 登录表单可能未完全加载，继续尝试填写...")

            # 填写邮箱 - 查找包含"请输入邮箱地址"的输入框
            email_selectors = [
                'input[placeholder*="请输入邮箱地址" i]',
                'input[placeholder*="邮箱地址" i]',
                'input[placeholder*="邮箱" i]',
                'input[type="email"]',
                'input[name="email"]',
                'input[placeholder*="email" i]',
                '#email',
                '.email-input'
            ]

            email_input = None

            # 首先在主页面查找
            for selector in email_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        if await element.is_visible():
                            # 检查placeholder是否包含邮箱相关文字
                            placeholder = await element.get_attribute('placeholder') or ''
                            if '邮箱' in placeholder or 'email' in placeholder.lower() or selector.startswith('input[placeholder'):
                                email_input = element
                                print(f"✓ 找到邮箱输入框(主页面): {selector}, placeholder='{placeholder}'")
                                break
                    if email_input:
                        break
                except:
                    continue

            # 如果主页面没找到，检查iframe
            if not email_input:
                iframes = await self.page.query_selector_all('iframe')
                for iframe in iframes:
                    try:
                        frame = await iframe.content_frame()
                        if frame:
                            for selector in email_selectors:
                                try:
                                    elements = await frame.query_selector_all(selector)
                                    for element in elements:
                                        if await element.is_visible():
                                            placeholder = await element.get_attribute('placeholder') or ''
                                            if '邮箱' in placeholder or 'email' in placeholder.lower() or selector.startswith('input[placeholder'):
                                                email_input = element
                                                print(f"✓ 找到邮箱输入框(iframe): {selector}, placeholder='{placeholder}'")
                                                break
                                    if email_input:
                                        break
                                except:
                                    continue
                            if email_input:
                                break
                    except:
                        continue

            if not email_input:
                print("✗ 未找到邮箱输入框")
                # 尝试关闭可能存在的模态框或对话框
                try:
                    close_buttons = await self.page.query_selector_all('button[aria-label*="close" i], button[aria-label*="关闭" i], button:has(svg[class*="close"]), button:has(svg[class*="x"])')
                    for close_btn in close_buttons:
                        try:
                            if await close_btn.is_visible():
                                await close_btn.click()
                                await self.page.wait_for_timeout(1000)
                                print("✓ 已关闭模态框，重新查找邮箱输入框...")
                                break
                        except:
                            continue
                    
                    # 重新查找邮箱输入框
                    for selector in email_selectors:
                        try:
                            elements = await self.page.query_selector_all(selector)
                            for element in elements:
                                if await element.is_visible():
                                    placeholder = await element.get_attribute('placeholder') or ''
                                    if '邮箱' in placeholder or 'email' in placeholder.lower() or selector.startswith('input[placeholder'):
                                        email_input = element
                                        print(f"✓ 重新找到邮箱输入框: {selector}, placeholder='{placeholder}'")
                                        break
                            if email_input:
                                break
                        except:
                            continue
                except:
                    pass
                
                if not email_input:
                    print("✗ 未找到邮箱输入框")
                    return False

            await email_input.fill(email)
            print(f"✓ 填写邮箱: {email}")
            await self.page.wait_for_timeout(500)  # 等待输入完成

            # 点击"继续"按钮发送验证码
            continue_selectors = [
                'button:has-text("继续")',
                'button:has-text("Continue")',
                'button:has-text("下一步")',
                'button:has-text("Next")',
                'button[type="submit"]',
            ]

            continue_button = None

            # 首先在主页面查找
            for selector in continue_selectors:
                try:
                    buttons = await self.page.query_selector_all(selector)
                    for button in buttons:
                        if await button.is_visible():
                            button_text = await button.inner_text() or ''
                            if '继续' in button_text or 'Continue' in button_text or '下一步' in button_text or 'Next' in button_text or selector == 'button[type="submit"]':
                                continue_button = button
                                print(f"✓ 找到继续按钮(主页面): {selector}, text='{button_text}'")
                                break
                    if continue_button:
                        break
                except:
                    continue

            # 如果主页面没找到，检查iframe
            if not continue_button:
                iframes = await self.page.query_selector_all('iframe')
                for iframe in iframes:
                    try:
                        frame = await iframe.content_frame()
                        if frame:
                            for selector in continue_selectors:
                                try:
                                    buttons = await frame.query_selector_all(selector)
                                    for button in buttons:
                                        if await button.is_visible():
                                            button_text = await button.inner_text() or ''
                                            if '继续' in button_text or 'Continue' in button_text or '下一步' in button_text or 'Next' in button_text or selector == 'button[type="submit"]':
                                                continue_button = button
                                                print(f"✓ 找到继续按钮(iframe): {selector}, text='{button_text}'")
                                                break
                                    if continue_button:
                                        break
                                except:
                                    continue
                            if continue_button:
                                break
                    except:
                        continue

            if continue_button:
                await continue_button.click()
                print("✓ 点击继续按钮，验证码已发送")
                await self.page.wait_for_timeout(2000)  # 等待验证码发送
                return True
            else:
                print("✗ 未找到继续按钮")
                return False

        except Exception as e:
            print(f"✗ 填写邮箱或发送验证码失败: {e}")
            return False

    async def _fill_verification_code_and_login(self, verification_code: str) -> bool:
        """填写验证码并完成登录"""
        try:
            print("📝 填写验证码并完成登录...")

            # 检查页面是否关闭，如果关闭了则重新导航
            try:
                if self.page.is_closed():
                    print("⚠️ 页面已关闭，重新导航到登录页面...")
                    await self._navigate_to_login()
                    # 重新点击登录按钮并填写邮箱
                    await self._fill_email_and_send_code(self.account.email)
            except Exception as e:
                print(f"⚠️ 检查页面状态时出错: {e}，尝试重新导航...")
                try:
                    await self._navigate_to_login()
                    await self._fill_email_and_send_code(self.account.email)
                except Exception as e2:
                    print(f"✗ 重新导航失败: {e2}")
                    return False

            # 等待验证码界面出现
            print("⏳ 等待验证码界面出现...")
            code_interface_max_wait = 30000  # 最多等待30秒
            code_interface_check_interval = 1000  # 每1秒检查一次
            code_interface_elapsed = 0
            code_inputs = []

            while code_interface_elapsed < code_interface_max_wait:
                # 检查页面是否关闭
                try:
                    if self.page.is_closed():
                        print("⚠️ 页面已关闭，无法继续填写验证码")
                        return False
                except:
                    pass

                # 查找验证码输入框（支持两种模式：多个单字符输入框 或 单个完整输入框）
                code_selectors = [
                    'input[type="text"][maxlength="1"]',  # 单个字符输入框（最优先）
                    'input[inputmode="numeric"]',  # 数字输入模式
                    'input[type="text"]',  # 通用文本输入框
                    'input[pattern*="[0-9]"]',  # 数字模式
                ]

                # 在主页面查找
                for selector in code_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        visible_inputs = []
                        single_code_input = None  # 单个完整验证码输入框
                        
                        for element in elements:
                            try:
                                if await element.is_visible():
                                    # 检查是否是验证码输入框
                                    placeholder = await element.get_attribute('placeholder') or ''
                                    class_name = await element.get_attribute('class') or ''
                                    maxlength = await element.get_attribute('maxlength') or ''
                                    inputmode = await element.get_attribute('inputmode') or ''
                                    input_type = await element.get_attribute('type') or ''
                                    
                                    # 模式1：多个单字符输入框（maxlength=1）
                                    if maxlength == '1' or (inputmode == 'numeric' and maxlength == '1'):
                                        visible_inputs.append(element)
                                    # 模式2：单个完整验证码输入框（maxlength=6 或 inputmode=numeric 且 maxlength>=6）
                                    elif (maxlength == '6' or (inputmode == 'numeric' and (maxlength == '' or int(maxlength) >= 6)) or 
                                          'code' in class_name.lower() or 'verification' in class_name.lower() or 'otp' in class_name.lower()):
                                        if single_code_input is None:
                                            single_code_input = element
                            except:
                                continue
                        
                        # 优先使用多个单字符输入框
                        if len(visible_inputs) >= 4:
                            code_inputs = visible_inputs[:6]  # 最多取6个
                            print(f"✓ 找到 {len(code_inputs)} 个验证码输入框(主页面，多输入框模式)")
                            break
                        # 如果找到单个完整输入框，也使用
                        elif single_code_input:
                            code_inputs = [single_code_input]
                            print(f"✓ 找到验证码输入框(主页面，单输入框模式，maxlength={await single_code_input.get_attribute('maxlength')})")
                            break
                    except:
                        continue

                # 如果主页面没找到，检查iframe
                if not code_inputs:
                    iframes = await self.page.query_selector_all('iframe')
                    for iframe in iframes:
                        try:
                            frame = await iframe.content_frame()
                            if frame:
                                for selector in code_selectors:
                                    try:
                                        elements = await frame.query_selector_all(selector)
                                        visible_inputs = []
                                        single_code_input = None
                                        
                                        for element in elements:
                                            try:
                                                if await element.is_visible():
                                                    maxlength = await element.get_attribute('maxlength') or ''
                                                    class_name = await element.get_attribute('class') or ''
                                                    inputmode = await element.get_attribute('inputmode') or ''
                                                    
                                                    # 模式1：多个单字符输入框
                                                    if maxlength == '1' or (inputmode == 'numeric' and maxlength == '1'):
                                                        visible_inputs.append(element)
                                                    # 模式2：单个完整验证码输入框
                                                    elif (maxlength == '6' or (inputmode == 'numeric' and (maxlength == '' or int(maxlength) >= 6)) or 
                                                          'code' in class_name.lower() or 'verification' in class_name.lower() or 'otp' in class_name.lower()):
                                                        if single_code_input is None:
                                                            single_code_input = element
                                            except:
                                                continue
                                        
                                        # 优先使用多个单字符输入框
                                        if len(visible_inputs) >= 4:
                                            code_inputs = visible_inputs[:6]
                                            print(f"✓ 找到 {len(code_inputs)} 个验证码输入框(iframe，多输入框模式)")
                                            break
                                        # 如果找到单个完整输入框，也使用
                                        elif single_code_input:
                                            code_inputs = [single_code_input]
                                            print(f"✓ 找到验证码输入框(iframe，单输入框模式，maxlength={await single_code_input.get_attribute('maxlength')})")
                                            break
                                    except:
                                        continue
                                if code_inputs:
                                    break
                        except:
                            continue

                # 一旦找到验证码输入框，立即继续（不等待）
                if code_inputs:
                    print("✅ 验证码界面已出现")
                    await self.page.wait_for_timeout(300)  # 短暂等待确保稳定
                    break

                # 如果还没找到，等待后继续检查
                await self.page.wait_for_timeout(code_interface_check_interval)
                code_interface_elapsed += code_interface_check_interval

            if not code_inputs:
                print("✗ 未找到验证码输入框")
                # 调试：显示所有可见的input元素
                try:
                    all_inputs = await self.page.query_selector_all('input')
                    visible_count = 0
                    for inp in all_inputs:
                        if await inp.is_visible():
                            visible_count += 1
                            maxlength = await inp.get_attribute('maxlength') or ''
                            inputmode = await inp.get_attribute('inputmode') or ''
                            print(f"  input: maxlength={maxlength}, inputmode={inputmode}")
                    print(f"🔍 主页面共有 {visible_count} 个可见input元素")
                except:
                    pass
                return False

            # 验证验证码格式
            if not verification_code.isdigit():
                print(f"✗ 验证码格式错误: {verification_code}，应为6位数字")
                return False

            if len(verification_code) != 6:
                print(f"✗ 验证码长度错误: {len(verification_code)}，应为6位")
                return False

            # 填写验证码到各个输入框
            print(f"📝 填写验证码: {verification_code}")
            code_length = len(verification_code)
            input_count = len(code_inputs)

            # 判断是单个输入框还是多个输入框
            is_single_input = input_count == 1
            if is_single_input:
                # 单个输入框模式：直接填写整个验证码
                single_input = code_inputs[0]
                try:
                    # 检查页面是否关闭
                    if self.page.is_closed():
                        print("✗ 页面已关闭，无法填写验证码")
                        return False
                    
                    # 点击输入框聚焦
                    await single_input.click()
                    await self.page.wait_for_timeout(200)
                    
                    # 清空输入框
                    await single_input.fill('')
                    await self.page.wait_for_timeout(100)
                    
                    # 填写整个验证码
                    await single_input.type(verification_code, delay=50)
                    await self.page.wait_for_timeout(200)
                    
                    # 验证填写是否成功
                    value = await single_input.input_value()
                    if value == verification_code:
                        print(f"✅ 验证码填写完成: {verification_code}")
                    else:
                        print(f"⚠️ 填写后值为: {value}，期望: {verification_code}")
                        # 尝试备用方法：直接fill
                        try:
                            await single_input.fill(verification_code)
                            await self.page.wait_for_timeout(200)
                            value = await single_input.input_value()
                            if value == verification_code:
                                print(f"✅ 使用备用方法填写完成: {verification_code}")
                            else:
                                print(f"⚠️ 备用方法填写后值为: {value}")
                        except Exception as e2:
                            print(f"✗ 备用方法也失败: {e2}")
                except Exception as e:
                    error_msg = str(e)
                    if "closed" in error_msg.lower() or "target" in error_msg.lower():
                        print(f"✗ 页面或浏览器已关闭: {e}")
                        return False
                    print(f"✗ 填写验证码失败: {e}")
                    # 尝试备用方法
                    try:
                        if not self.page.is_closed():
                            await single_input.fill(verification_code)
                            await self.page.wait_for_timeout(200)
                            print(f"✅ 使用备用方法填写完成: {verification_code}")
                        else:
                            print("✗ 页面已关闭，无法使用备用方法")
                            return False
                    except Exception as e2:
                        if "closed" in str(e2).lower() or "target" in str(e2).lower():
                            print(f"✗ 页面或浏览器已关闭: {e2}")
                        else:
                            print(f"✗ 备用方法也失败: {e2}")
                        return False
            else:
                # 多个输入框模式：逐个填写
                # 确保验证码长度不超过输入框数量
                if code_length > input_count:
                    print(f"⚠️ 验证码长度({code_length})超过输入框数量({input_count})，截取前{input_count}位")
                    verification_code = verification_code[:input_count]
                elif code_length < input_count:
                    print(f"⚠️ 验证码长度({code_length})少于输入框数量({input_count})，只填写前{code_length}位")

                # 逐个填写验证码
                for i, code_char in enumerate(verification_code):
                    if i < len(code_inputs):
                        try:
                            # 检查页面是否关闭
                            if self.page.is_closed():
                                print(f"✗ 页面已关闭，无法继续填写验证码（已填写 {i}/{code_length} 位）")
                                return False
                            
                            # 点击输入框聚焦
                            await code_inputs[i].click()
                            await self.page.wait_for_timeout(150)
                            
                            # 清空输入框（如果有内容）
                            await code_inputs[i].fill('')
                            await self.page.wait_for_timeout(50)
                            
                            # 填写单个字符
                            await code_inputs[i].type(code_char, delay=50)
                            await self.page.wait_for_timeout(100)
                            
                            # 验证填写是否成功
                            value = await code_inputs[i].input_value()
                            if value == code_char:
                                print(f"  ✓ 填写第 {i+1} 位: {code_char}")
                            else:
                                print(f"  ⚠️ 第 {i+1} 位填写后值为: {value}，期望: {code_char}")
                        except Exception as e:
                            error_msg = str(e)
                            if "closed" in error_msg.lower() or "target" in error_msg.lower():
                                print(f"✗ 页面或浏览器已关闭: {e}")
                                return False
                            print(f"  ✗ 填写第 {i+1} 位失败: {e}")
                            # 尝试备用方法
                            try:
                                if not self.page.is_closed():
                                    await code_inputs[i].fill(code_char)
                                    await self.page.wait_for_timeout(100)
                                    print(f"  ✓ 使用备用方法填写第 {i+1} 位: {code_char}")
                                else:
                                    print(f"  ✗ 页面已关闭，无法使用备用方法")
                                    return False
                            except Exception as e2:
                                if "closed" in str(e2).lower() or "target" in str(e2).lower():
                                    print(f"  ✗ 页面或浏览器已关闭: {e2}")
                                    return False
                                print(f"  ✗ 备用方法也失败: {e2}")

                print(f"✅ 验证码填写完成")
            await self.page.wait_for_timeout(1000)  # 等待验证码填写完成，给按钮出现时间

            # 点击"继续"按钮完成登录
            print("🔍 查找完成登录按钮...")
            
            # 扩展的选择器列表
            final_continue_selectors = [
                'button:has-text("继续")',
                'button:has-text("Continue")',
                'button:has-text("完成")',
                'button:has-text("完成登录")',
                'button:has-text("登录")',
                'button:has-text("Sign in")',
                'button:has-text("Verify")',
                'button:has-text("确认")',
                'button:has-text("Confirm")',
                'button[type="submit"]',
                'button[type="button"]',  # 也可能是普通按钮
            ]

            final_continue_button = None
            max_wait_attempts = 10  # 最多等待10次，每次1秒
            wait_interval = 1000  # 每次等待1秒

            # 智能等待按钮出现
            for attempt in range(max_wait_attempts):
                # 首先在主页面查找
                for selector in final_continue_selectors:
                    try:
                        buttons = await self.page.query_selector_all(selector)
                        for button in buttons:
                            try:
                                if await button.is_visible():
                                    button_text = await button.inner_text() or ''
                                    button_text_lower = button_text.lower().strip()
                                    
                                    # 更严格的匹配条件，避免匹配到错误的按钮（如用户信息按钮）
                                    if (any(keyword in button_text_lower for keyword in ['继续', 'continue', '完成', '完成登录', '登录', 'sign in', 'verify', '确认', 'confirm', 'submit']) or 
                                        selector == 'button[type="submit"]'):
                                        # 排除明显不是登录按钮的文本（如包含邮箱、upgrade等）
                                        if not any(exclude in button_text_lower for exclude in ['upgrade', '邮箱', 'email', '@', 'profile', 'profile', '用户', 'user']):
                                            final_continue_button = button
                                            print(f"✓ 找到完成登录按钮(主页面): {selector}, text='{button_text}'")
                                            break
                            except:
                                continue
                        if final_continue_button:
                            break
                    except:
                        continue

                # 如果主页面没找到，检查iframe
                if not final_continue_button:
                    iframes = await self.page.query_selector_all('iframe')
                    for iframe in iframes:
                        try:
                            frame = await iframe.content_frame()
                            if frame:
                                for selector in final_continue_selectors:
                                    try:
                                        buttons = await frame.query_selector_all(selector)
                                        for button in buttons:
                                            try:
                                                if await button.is_visible():
                                                    button_text = await button.inner_text() or ''
                                                    button_text_lower = button_text.lower().strip()
                                                    
                                                    if (any(keyword in button_text_lower for keyword in ['继续', 'continue', '完成', '登录', 'sign in', 'verify', '确认', 'confirm']) or 
                                                        selector == 'button[type="submit"]' or
                                                        (selector == 'button[type="button"]' and len(button_text.strip()) > 0)):
                                                        final_continue_button = button
                                                        print(f"✓ 找到完成登录按钮(iframe): {selector}, text='{button_text}'")
                                                        break
                                            except:
                                                continue
                                        if final_continue_button:
                                            break
                                    except:
                                        continue
                                if final_continue_button:
                                    break
                        except:
                            continue

                # 如果找到了按钮，退出循环
                if final_continue_button:
                    break

                # 如果还没找到，等待后重试
                if attempt < max_wait_attempts - 1:
                    print(f"⏳ 等待按钮出现... ({attempt + 1}/{max_wait_attempts})")
                    await self.page.wait_for_timeout(wait_interval)

            # 如果还是没找到，列出所有可见的按钮用于调试
            if not final_continue_button:
                print("✗ 未找到完成登录按钮")
                print("🔍 调试：列出所有可见的按钮...")
                try:
                    all_buttons = await self.page.query_selector_all('button')
                    visible_buttons = []
                    for btn in all_buttons:
                        try:
                            if await btn.is_visible():
                                text = await btn.inner_text() or ''
                                btn_type = await btn.get_attribute('type') or ''
                                visible_buttons.append(f"text='{text}', type='{btn_type}'")
                        except:
                            continue
                    
                    if visible_buttons:
                        print(f"  找到 {len(visible_buttons)} 个可见按钮:")
                        for i, btn_info in enumerate(visible_buttons[:10], 1):  # 只显示前10个
                            print(f"    {i}. {btn_info}")
                    else:
                        print("  未找到任何可见按钮")
                    
                    # 也检查iframe中的按钮
                    iframes = await self.page.query_selector_all('iframe')
                    for iframe in iframes:
                        try:
                            frame = await iframe.content_frame()
                            if frame:
                                iframe_buttons = await frame.query_selector_all('button')
                                for btn in iframe_buttons:
                                    try:
                                        if await btn.is_visible():
                                            text = await btn.inner_text() or ''
                                            btn_type = await btn.get_attribute('type') or ''
                                            print(f"    [iframe] text='{text}', type='{btn_type}'")
                                    except:
                                        continue
                        except:
                            continue
                except Exception as e:
                    print(f"  调试信息获取失败: {e}")

                # 如果没找到按钮，尝试检测是否已登录成功（验证码提交后可能已自动登录）
                try:
                    login_status = await self._check_login_success()
                    if login_status:
                        print("✓ 未找到完成按钮，但检测到已登录成功，继续流程")
                        return True
                except Exception as e:
                    print(f"⚠️ 登录状态检测失败: {e}")

                # 最后尝试回车键提交
                try:
                    print("⚠️ 尝试按回车键提交...")
                    await self.page.keyboard.press('Enter')
                    await self.page.wait_for_timeout(2000)
                    login_status = await self._check_login_success()
                    if login_status:
                        print("✓ 回车提交后已登录成功")
                        return True
                except:
                    pass
                
                return False

            # 在点击前重新查找按钮，避免元素已从DOM中移除
            print("🔍 重新查找并点击完成登录按钮...")
            button_clicked = False
            for retry in range(3):  # 最多重试3次
                try:
                    # 重新查找按钮
                    for selector in final_continue_selectors:
                        try:
                            buttons = await self.page.query_selector_all(selector)
                            for button in buttons:
                                try:
                                    if await button.is_visible():
                                        button_text = (await button.inner_text() or '').strip()
                                        button_text_lower = button_text.lower()
                                        
                                        # 检查是否包含登录相关的关键词
                                        has_login_keyword = any(text in button_text_lower for text in ['继续', 'continue', '登录', 'login', '完成', 'submit', 'verify', '确认', 'confirm'])
                                        
                                        # 排除明显不是登录按钮的文本
                                        is_excluded = any(exclude in button_text_lower for exclude in ['upgrade', '邮箱', 'email', '@', 'profile', '用户', 'user', '1043223937'])
                                        
                                        if has_login_keyword and not is_excluded:
                                            # 检查按钮是否可用
                                            is_disabled = await button.is_disabled()
                                            if not is_disabled:
                                                await button.scroll_into_view_if_needed()
                                                await self.page.wait_for_timeout(300)
                                                await button.click(timeout=10000)
                                                print(f"✓ 点击完成登录按钮: {button_text}")
                                                button_clicked = True
                                                break
                                except Exception as e:
                                    if "not attached" not in str(e).lower():
                                        continue
                            if button_clicked:
                                break
                        except:
                            continue
                    if button_clicked:
                        break
                    
                    # 如果没找到，等待后重试
                    if retry < 2:
                        print(f"⚠️ 未找到按钮，等待后重试 ({retry + 1}/3)...")
                        await self.page.wait_for_timeout(1000)
                except Exception as e:
                    if retry < 2:
                        print(f"⚠️ 查找按钮失败，重试 ({retry + 1}/3): {e}")
                        await self.page.wait_for_timeout(1000)
                    else:
                        raise
            
            if not button_clicked:
                print("✗ 无法找到或点击完成登录按钮")
                return False

            # 等待登录完成
            await self.page.wait_for_timeout(3000)

            # 检查是否登录成功
            return await self._check_login_success()

        except Exception as e:
            print(f"✗ 填写表单失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _check_login_success(self) -> bool:
        """检查登录是否成功"""
        try:
            # 检查URL是否跳转（已登录的页面通常不包含login）
            current_url = self.page.url.lower()
            if "login" not in current_url and ("chat" in current_url or "research" in current_url or "dashboard" in current_url):
                print("✓ 登录成功 (URL跳转)")
                return True

            # 检查是否存在登录按钮（如果存在，说明未登录）
            login_indicators = [
                'button:has-text("登录")',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                'button:has-text("Log in")',
            ]
            
            has_login_button = False
            for selector in login_indicators:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        has_login_button = True
                        break
                except:
                    continue
            
            # 如果存在登录按钮，说明未登录
            if has_login_button:
                print("⚠️ 检测到登录按钮，可能未登录")
                return False

            # 检查是否存在已登录的特征元素
            success_indicators = [
                'button:has-text("登出")',
                'button:has-text("Logout")',
                'button:has-text("Sign out")',
                'a:has-text("Profile")',
                '.user-avatar',
                '.user-info',
                '[data-testid*="user"]',
                'textarea[placeholder*="输入" i]',  # 聊天输入框
                'textarea[placeholder*="message" i]',  # 消息输入框
                'textarea[placeholder*="Ask" i]',  # 提问输入框
                'button:has-text("深度研究")',  # 深度研究按钮
                'button:has-text("快速问答")',  # 快速问答按钮
                'button:has-text("Research")',  # 研究按钮
                'button:has-text("Chat")',  # 聊天按钮
            ]

            for selector in success_indicators:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        print(f"✓ 登录成功 (找到已登录特征: {selector})")
                        return True
                except:
                    continue

            # 如果URL不包含login，且没有登录按钮，假设已登录
            if "login" not in current_url:
                print("✓ 登录成功 (URL不包含login且无登录按钮)")
                return True

            print("⚠️ 登录状态不确定")
            return False

        except Exception as e:
            print(f"✗ 检查登录状态失败: {e}")
            return False

    async def save_login_state(self):
        """保存登录状态"""
        try:
            # 创建上下文并保存状态
            context = await self.browser.new_context()
            await context.add_cookies(await self.page.context.cookies())

            state_path = self.state_dir / "auto_login_state.json"
            await context.storage_state(path=str(state_path))

            await context.close()
            print(f"✓ 登录状态已保存到: {state_path}")
            return True
        except Exception as e:
            print(f"✗ 保存登录状态失败: {e}")
            return False

    async def auto_login(self) -> bool:
        """执行自动登录流程"""
        try:
            print("=" * 60)
            print("🚀 开始 Surf AI 自动登录")
            print("=" * 60)

            # 创建新页面
            if not self.page or self.page.is_closed():
                self.page = await self.browser.new_page()
            else:
                print("ℹ️ 使用现有页面")

            # 导航到登录页面
            await self._navigate_to_login()
            
            # 等待页面加载
            await self.page.wait_for_timeout(2000)
            
            # 首先检查是否已经登录
            print("🔍 检查是否已经登录...")
            is_already_logged_in = await self._check_login_success()
            if is_already_logged_in:
                print("=" * 60)
                print("✅ 账号已经登录，跳过登录流程")
                print("=" * 60)
                return True

            # 如果未登录，继续登录流程
            print("ℹ️ 账号未登录，开始登录流程...")

            # 检查是否为rambler.ru邮箱，需要特殊激活流程
            if self.is_rambler_email:
                print("🇷🇺 检测到rambler.ru邮箱，使用邮箱激活流程")
                return await self._handle_rambler_email_activation()

            # 点击登录按钮打开登录表单
            login_button_selectors = [
                'button:has-text("登录")',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                'a:has-text("登录")',
                'a:has-text("Login")',
            ]

            login_clicked = False
            for selector in login_button_selectors:
                try:
                    button = await self.page.query_selector(selector)
                    if button and await button.is_visible():
                        print(f"🖱️ 点击登录按钮: {selector}")
                        await button.click()
                        await self.page.wait_for_timeout(2000)  # 等待登录表单出现
                        login_clicked = True
                        break
                except:
                    continue

            if not login_clicked:
                print("⚠️ 未找到登录按钮，可能已经打开登录表单")

            # 填写邮箱并发送验证码
            email_filled = await self._fill_email_and_send_code(self.account.email)
            if not email_filled:
                print("✗ 填写邮箱或发送验证码失败")
                return False

            # 等待并获取验证码
            print("⏳ 等待验证码邮件...")
            verification_code = self.get_verification_code()
            if not verification_code:
                print("✗ 获取验证码失败")
                return False

            # 填写验证码并完成登录
            login_success = await self._fill_verification_code_and_login(verification_code)
            if not login_success:
                print("✗ 填写验证码或登录失败")
                return False

            # 保存登录状态
            await self.save_login_state()

            print("=" * 60)
            print("🎉 自动登录成功！")
            print("=" * 60)
            return True

        except Exception as e:
            print(f"✗ 自动登录过程出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _handle_rambler_email_activation(self) -> bool:
        """处理rambler.ru邮箱的激活流程"""
        try:
            print("=" * 60)
            print("🇷🇺 rambler.ru 邮箱激活流程")
            print("=" * 60)

            # 注意：rambler.ru邮箱的完整激活流程需要API调用
            # 这里提供基本框架，实际需要根据space3.py的逻辑完善

            print("⚠️ rambler.ru邮箱激活流程开发中...")
            print("📧 需要实现:")
            print("  1. 账户注册 (调用API获取auth_code)")
            print("  2. 邮箱激活 (IMAP获取邮件 + Selenium点击)")
            print("  3. 重新登录 (获取新的access_token)")

            # 暂时返回失败，需要完整实现
            print("❌ rambler.ru邮箱激活暂未完全实现")
            return False

        except Exception as e:
            print(f"✗ rambler.ru邮箱激活过程出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ==================== rambler.ru 邮箱激活相关方法 ====================

    def _connect_rambler_imap(self) -> bool:
        """专门连接rambler.ru邮箱的IMAP服务器（支持代理池轮询重试）"""
        print(f"📧 连接到rambler.ru IMAP服务器...")

        # 获取代理轮询列表
        proxy_rotation = self.proxy_manager.get_proxy_rotation()
        print(f"🔄 共有 {len(proxy_rotation)} 个代理可用于轮询")

        # 如果没有代理，尝试直连
        if not proxy_rotation:
            print("⚠️ 没有可用代理，尝试直连...")
            return self._connect_rambler_direct()

        # 轮询尝试每个代理
        last_error = None
        for i, proxy_info in enumerate(proxy_rotation):
            try:
                print(f"🔄 尝试代理 {i+1}/{len(proxy_rotation)}: {proxy_info.url}")

                # 使用代理连接IMAP
                success = self._connect_imap_through_proxy(proxy_info)
                if success:
                    # 连接成功后进行登录
                    print(f"🔐 尝试登录rambler邮箱: {self.account.email}")
                    self.imap.login(self.account.email, self.account.email_password)
                    self.imap.select('inbox')
                    print("✓ Rambler邮箱登录成功")

                    # 标记代理成功
                    self.proxy_manager.mark_proxy_success(proxy_info)
                    return True
                else:
                    # 连接失败，标记代理失败
                    self.proxy_manager.mark_proxy_failed(proxy_info)
                    print(f"❌ 代理 {proxy_info.url} 连接失败")

            except imaplib.IMAP4.error as e:
                last_error = e
                self.proxy_manager.mark_proxy_failed(proxy_info)
                print(f"❌ 代理 {proxy_info.url} 认证失败: {e}")
            except Exception as e:
                last_error = e
                self.proxy_manager.mark_proxy_failed(proxy_info)
                print(f"❌ 代理 {proxy_info.url} 连接异常: {e}")

        # 所有代理都失败，尝试直连作为最后手段
        print("⚠️ 所有代理都失败，尝试直连...")
        if self._connect_rambler_direct():
            print(f"🔐 尝试登录rambler邮箱: {self.account.email}")
            self.imap.login(self.account.email, self.account.email_password)
            self.imap.select('inbox')
            print("✓ Rambler邮箱直连登录成功")
            return True

        # 完全失败
        print("✗ 所有代理和直连方式都失败")
        print(f"  最后错误: {last_error}")
        print("  建议解决方案:")
        print("    1. 检查代理列表是否正确配置")
        print("    2. 确认代理IP可用性")
        print("    3. 尝试使用VPN连接")
        print("    4. 检查防火墙和网络设置")
        return False

    def _connect_imap_through_proxy(self, proxy_info) -> bool:
        """通过代理连接IMAP服务器"""
        try:
            socket.setdefaulttimeout(60)

            # 解析代理信息
            if proxy_info.protocol in ['http', 'https']:
                # HTTP代理需要特殊处理IMAP over HTTP
                # 这里使用socksipy或类似库来处理
                try:
                    import socks
                    import socket as sock_socket

                    # 解析代理URL
                    proxy_url = proxy_info.url.replace('http://', '').replace('https://', '')
                    if ':' in proxy_url:
                        proxy_host, proxy_port = proxy_url.split(':')
                        proxy_port = int(proxy_port)
                    else:
                        proxy_host = proxy_url
                        proxy_port = 80 if proxy_info.protocol == 'http' else 443

                    # 创建代理socket
                    sock = socks.socksocket()
                    if proxy_info.username and proxy_info.password:
                        # 使用认证信息
                        sock.set_proxy(socks.HTTP, proxy_host, proxy_port,
                                     username=proxy_info.username,
                                     password=proxy_info.password)
                    else:
                        sock.set_proxy(socks.HTTP, proxy_host, proxy_port)
                    sock.connect(('imap.rambler.ru', 993))

                    # 包装SSL
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE

                    ssl_sock = ssl_context.wrap_socket(sock, server_hostname='imap.rambler.ru')
                    self.imap = imaplib.IMAP4()
                    self.imap.sock = ssl_sock
                    self.imap.file = ssl_sock.makefile('rb')

                    return True

                except ImportError:
                    print("⚠️ 需要安装 PySocks 库: pip install PySocks")
                    return False
                except Exception as e:
                    print(f"⚠️ HTTP代理连接失败: {e}")
                    return False

            elif proxy_info.protocol in ['socks4', 'socks5']:
                # SOCKS代理
                try:
                    import socks
                    import socket as sock_socket

                    # 解析代理URL
                    proxy_url = proxy_info.url.replace('socks4://', '').replace('socks5://', '')
                    proxy_host, proxy_port = proxy_url.split(':')
                    proxy_port = int(proxy_port)

                    # 创建SOCKS代理socket
                    sock = socks.socksocket()
                    if proxy_info.username and proxy_info.password:
                        # 使用认证信息
                        if proxy_info.protocol == 'socks4':
                            sock.set_proxy(socks.SOCKS4, proxy_host, proxy_port,
                                         username=proxy_info.username,
                                         password=proxy_info.password)
                        else:
                            sock.set_proxy(socks.SOCKS5, proxy_host, proxy_port,
                                         username=proxy_info.username,
                                         password=proxy_info.password)
                    else:
                        if proxy_info.protocol == 'socks4':
                            sock.set_proxy(socks.SOCKS4, proxy_host, proxy_port)
                        else:
                            sock.set_proxy(socks.SOCKS5, proxy_host, proxy_port)

                    sock.connect(('imap.rambler.ru', 993))

                    # 包装SSL
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE

                    ssl_sock = ssl_context.wrap_socket(sock, server_hostname='imap.rambler.ru')
                    self.imap = imaplib.IMAP4()
                    self.imap.sock = ssl_sock
                    self.imap.file = ssl_sock.makefile('rb')

                    return True

                except ImportError:
                    print("⚠️ 需要安装 PySocks 库: pip install PySocks")
                    return False
                except Exception as e:
                    print(f"⚠️ SOCKS代理连接失败: {e}")
                    return False

            else:
                print(f"⚠️ 不支持的代理协议: {proxy_info.protocol}")
                return False

        except Exception as e:
            print(f"⚠️ 代理连接异常: {e}")
            return False
        finally:
            socket.setdefaulttimeout(None)

    def _connect_rambler_direct(self) -> bool:
        """直接连接rambler.ru邮箱（不使用代理）"""
        try:
            socket.setdefaulttimeout(60)

            # 方式1: 使用宽松SSL设置
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                ssl_context.minimum_version = ssl.TLSVersion.TLSv1
                ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3

                self.imap = imaplib.IMAP4_SSL(
                    'imap.rambler.ru',
                    port=993,
                    ssl_context=ssl_context,
                    timeout=60
                )
                print("✓ 直连SSL连接成功")
                return True
            except Exception as e1:
                print(f"⚠️ 直连SSL失败: {e1}")

            # 方式2: 手动socket连接
            try:
                sock = socket.create_connection(('imap.rambler.ru', 993), timeout=60)
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                ssl_sock = ssl_context.wrap_socket(sock, server_hostname='imap.rambler.ru')
                self.imap = imaplib.IMAP4()
                self.imap.sock = ssl_sock
                self.imap.file = ssl_sock.makefile('rb')
                print("✓ 直连socket+SSL成功")
                return True
            except Exception as e2:
                print(f"⚠️ 直连socket失败: {e2}")

            return False

        except Exception as e:
            print(f"⚠️ 直连异常: {e}")
            return False
        finally:
            socket.setdefaulttimeout(None)

    def _get_rambler_verification_email(self, mail, retries=5):
        """获取rambler.ru的验证邮件"""
        try:
            # 定义需要检查的文件夹
            folders_to_check = ['inbox', 'spam', 'trash', 'Spam', 'Trash']

            for folder in folders_to_check:
                print(f"🔍 检查文件夹: {folder}")
                # 选择邮件箱
                status, response = mail.select(folder)

                if status != 'OK':
                    print(f"⚠️ 无法选择文件夹 {folder}")
                    continue

                # 使用收件地址进行筛选
                status, messages = mail.search(None, f'(TO "{self.account.email}")')

                if status != 'OK' or not messages[0]:
                    print(f"⚠️ {folder}文件夹中未找到邮件")
                    continue

                # 获取邮件ID
                email_ids = messages[0].split()

                for email_id in email_ids:
                    # 获取邮件数据
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue

                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])

                            # 解码邮件主题
                            subject, encoding = decode_header(msg['Subject'])[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding or 'utf-8')

                            print(f"📧 检查邮件主题: {subject}")

                            # 检查是否为验证邮件
                            if 'Please Verify Your Email' in subject:
                                print(f"✅ 找到验证邮件: {subject}")
                                return msg

            print("⚠️ 未找到验证邮件")
            return None

        except Exception as e:
            print(f"✗ 获取验证邮件失败: {e}")
            if retries > 0:
                print(f"🔄 重试中... ({6-retries}/5)")
                time.sleep(2)
                return self._get_rambler_verification_email(mail, retries-1)
            return None

    def _extract_activation_link(self, msg):
        """从邮件中提取激活链接"""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    # 查找邮件中的激活链接
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        body = part.get_payload(decode=True).decode()
                        # 提取激活链接
                        activation_link = body.split("http")[1].strip().split()[0]
                        return "http" + activation_link
            else:
                # 处理非multipart邮件
                body = msg.get_payload(decode=True).decode()
                # 提取激活链接
                activation_link = body.split("http")[1].strip().split()[0]
                return "http" + activation_link

            return None
        except Exception as e:
            print(f"✗ 提取激活链接失败: {e}")
            return None

    def _clean_activation_link(self, link):
        """清理激活链接中的特殊字符"""
        try:
            # URL解码
            cleaned_link = urllib.parse.unquote(link)
            # 去掉链接末尾的多余字符
            if cleaned_link.endswith('"'):
                cleaned_link = cleaned_link[:-1]
            return cleaned_link
        except Exception as e:
            print(f"✗ 清理链接失败: {e}")
            return link

    def _activate_rambler_account_with_selenium(self, activation_link):
        """使用Selenium激活rambler.ru账户"""
        driver = None
        try:
            print("🚀 启动Chrome浏览器进行激活...")

            # 创建Chrome配置
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--headless")  # 无头模式
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

            # 启动浏览器
            driver = webdriver.Chrome(options=chrome_options)
            print("✅ 浏览器启动成功")

            # 访问激活链接
            print(f"🔗 访问激活链接: {activation_link}")
            driver.get(activation_link)

            # 等待页面加载
            time.sleep(5)

            # 检查是否重定向到激活成功页面
            current_url = driver.current_url
            print(f"📍 当前URL: {current_url}")

            if "verify-email" in current_url or "success" in current_url.lower():
                print("✅ 邮箱激活成功")
                return True
            else:
                print("⚠️ 激活状态不确定，但继续流程")
                return True

        except Exception as e:
            print(f"✗ Selenium激活失败: {e}")
            return False
        finally:
            if driver:
                driver.quit()
                print("🔒 浏览器已关闭")

    def _register_rambler_account(self):
        """注册rambler.ru账户（模拟space3.py的注册逻辑）"""
        try:
            print("📝 注册rambler.ru账户...")

            # 这里需要模拟space3.py中的注册逻辑
            # 由于需要访问API，这里暂时返回模拟的auth_code
            # 实际实现时需要调用相应的API

            print("⚠️ rambler.ru账户注册功能待实现")
            return None

        except Exception as e:
            print(f"✗ 注册失败: {e}")
            return None


async def main():
    """主函数 - 使用surf_config.py中的配置"""
    try:
        import surf_config
        account = surf_config.get_default_account()
        print("✅ 使用 surf_config.py 中的配置")
        print(f"📧 邮箱: {account.email}")
        print(f"🏠 服务器: {account.email_server}:{account.email_port}")
    except ImportError:
        print("❌ 未找到 surf_config.py，请创建配置文件")
        print("参考: copy surf_config_example.py surf_config.py")
        return
    except Exception as e:
        print(f"❌ 加载配置失败: {e}")
        return

    async with SurfAutoLogin(account) as login_tool:
        success = await login_tool.auto_login()
        if success:
            print("\n🎯 自动登录完成！现在可以使用保存的状态进行后续操作")
        else:
            print("\n❌ 自动登录失败，请检查配置和网络连接")


if __name__ == "__main__":
    asyncio.run(main())
