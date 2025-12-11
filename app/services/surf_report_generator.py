"""
Surf 投研报告生成器
使用 Playwright 自动化操作网页生成PDF报告
支持两种模式：快速问答(chat)和深度研究(research)
"""
import asyncio
import os
from datetime import datetime
from typing import Optional, Literal
from pathlib import Path
from enum import Enum
from playwright.async_api import async_playwright, Browser, Page
from sqlalchemy.orm import Session

from app.models import Project, Report, SurfAccount
from app.services.surf_account_pool import SurfAccountPool
from app.services.email_login_strategy import EmailLoginStrategy, EmailType
from app.config import get_settings

settings = get_settings()

REPORTS_DIR = Path("data/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class ReportMode(str, Enum):
    CHAT = "chat"           # 快速问答
    RESEARCH = "research"   # 深度研究


class SurfReportGenerator:
    def __init__(self, db: Session):
        self.db = db
        self.account_pool = SurfAccountPool(db)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.current_account: Optional[SurfAccount] = None
    
    async def _init_browser(self):
        """初始化浏览器"""
        self._playwright = await async_playwright().start()
        
        # 代理配置（从配置文件读取）
        proxy_server = settings.proxy_server
        
        # 改进的浏览器启动配置
        browser_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ]

        try:
            # 尝试使用系统Chrome
            self.browser = await self._playwright.chromium.launch(
                headless=True,
                channel="chrome",
                args=browser_args,
                proxy={"server": proxy_server} if proxy_server else None,
                timeout=10000,
            )
            print("✓ 使用系统Chrome浏览器")
        except Exception as e:
            print(f"⚠ 系统Chrome启动失败: {e}")
            try:
                # 回退到chromium
                self.browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=browser_args,
                    proxy={"server": proxy_server} if proxy_server else None,
                    timeout=10000,
                )
                print("✓ 使用Chromium浏览器")
            except Exception as e2:
                print(f"⚠ Chromium启动也失败: {e2}")
                raise Exception("无法启动浏览器，请检查浏览器安装")
    
    async def _close_browser(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, '_playwright') and self._playwright:
            await self._playwright.stop()
    
    async def _login(self, account: SurfAccount) -> bool:
        """登录 Surf 账号（使用自动登录工具）"""
        from pathlib import Path
        import json
        import sys
        
        # 导入自动登录工具
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from surf_auto_login import SurfAutoLogin, SurfAccount as AutoLoginAccount

        try:
            # 确保浏览器已初始化
            if not self.browser:
                print("⚠️ 浏览器未初始化，重新初始化...")
                await self._init_browser()
            
            # 创建新页面（如果还没有或已关闭）
            try:
                if not self.page:
                    self.page = await self.browser.new_page()
                    print("✓ 创建新页面")
                else:
                    # 检查页面是否已关闭
                    try:
                        if self.page.is_closed():
                            print("⚠️ 页面已关闭，重新创建...")
                            self.page = await self.browser.new_page()
                            print("✓ 重新创建页面")
                    except Exception as e:
                        # 如果检查失败，尝试重新创建页面
                        print(f"⚠️ 页面状态检查失败: {e}，尝试重新创建...")
                        self.page = await self.browser.new_page()
                        print("✓ 重新创建页面")
            except Exception as e:
                error_msg = f"无法创建浏览器页面: {e}"
                print(f"✗ {error_msg}")
                raise Exception(error_msg)
            
            # 首先检查是否已经登录
            print("🔍 检查是否已经登录...")
            
            # 导航到主页面检查登录状态
            try:
                await self.page.goto(
                    f"{settings.surf_base_url}/chat",
                    wait_until="domcontentloaded",
                    timeout=60000
                )
                await self.page.wait_for_timeout(2000)
            except:
                # 如果导航失败，尝试导航到主页
                try:
                    await self.page.goto(
                        settings.surf_base_url,
                        wait_until="domcontentloaded",
                        timeout=60000
                    )
                    await self.page.wait_for_timeout(2000)
                except:
                    pass
            
            # 检查登录状态
            is_already_logged_in = await self._is_logged_in()
            if is_already_logged_in:
                print("=" * 60)
                print("✅ 账号已经登录，跳过登录流程")
                print("=" * 60)
                self.current_account = account
                return True
            
            # 如果未登录，执行登录流程
            print("=" * 60)
            print("🔄 账号未登录，开始执行自动登录...")
            print("=" * 60)
            
            # 获取邮箱密码
            email_password = self.account_pool.get_email_password(account)
            
            # 使用邮箱登录策略自动检测IMAP服务器和配置
            email_type = EmailLoginStrategy.detect_email_type(account.email)
            login_config = EmailLoginStrategy.get_login_config(account.email)
            
            # 优先使用数据库中的配置，如果没有则使用策略检测的配置
            email_server = account.email_server or EmailLoginStrategy.get_imap_server(account.email)
            email_port = account.email_port or EmailLoginStrategy.get_imap_port(account.email)
            
            # 显示邮箱类型和配置信息
            print(f"📧 邮箱类型: {email_type.value}")
            print(f"🔍 IMAP服务器: {email_server}:{email_port}")
            if login_config.special_notes:
                print(f"ℹ️  {login_config.special_notes}")
                
            # 创建自动登录账号对象
            auto_account = AutoLoginAccount(
                email=account.email,
                email_password=email_password,
                email_server=email_server,
                email_port=email_port
            )
            
            # 使用自动登录工具，复用已有的浏览器实例和页面
            login_tool = SurfAutoLogin(auto_account)
            login_tool.browser = self.browser  # 复用浏览器
            login_tool.playwright = self._playwright  # 复用playwright
            login_tool.page = self.page  # 复用页面
            
            # 执行自动登录流程（不调用auto_login，直接调用内部方法）
            # 导航到登录页面并点击登录按钮
            await login_tool._navigate_to_login()
            
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
                    await self.page.wait_for_timeout(2000)
                    login_clicked = True
                    break
                except:
                    continue
            
            if not login_clicked:
                print("⚠️ 未找到登录按钮，可能已经打开登录表单")
            
            # 填写邮箱并发送验证码
            email_filled = await login_tool._fill_email_and_send_code(account.email)
            if not email_filled:
                print("✗ 填写邮箱或发送验证码失败")
                return False
            
            # 等待并获取验证码
            print("⏳ 等待验证码邮件...")
            verification_code = login_tool.get_verification_code()
            if not verification_code:
                print("✗ 获取验证码失败")
                return False
            
            # 填写验证码并完成登录
            login_success = await login_tool._fill_verification_code_and_login(verification_code)
            if not login_success:
                print("✗ 填写验证码或登录失败")
                return False
            
            # 等待登录完成并页面跳转
            print("⏳ 等待登录完成并页面跳转...")
            await self.page.wait_for_timeout(5000)
            
            # 检查URL是否跳转到chat页面
            current_url = self.page.url
            print(f"📍 当前URL: {current_url}")
            
            # 如果还在登录相关页面，等待跳转
            if 'login' in current_url.lower() or 'signin' in current_url.lower():
                print("⏳ 等待页面跳转到chat页面...")
                try:
                    # 等待URL变化或导航到chat
                    await self.page.wait_for_url('**/chat**', timeout=30000)
                    print("✓ 页面已跳转到chat")
                except:
                    # 如果等待超时，手动导航
                    print("⚠️ 自动跳转超时，手动导航到chat页面...")
                    await self.page.goto(
                        f"{settings.surf_base_url}/chat",
                        wait_until="domcontentloaded",
                        timeout=120000
                    )
                await self.page.wait_for_timeout(3000)
            
            # 等待登录模态框关闭
            print("⏳ 等待登录模态框关闭...")
            for i in range(10):
                try:
                    login_modal = await self.page.query_selector('[role="dialog"], .modal, .login-modal')
                    if login_modal:
                        is_visible = await login_modal.is_visible()
                        if not is_visible:
                            print("✓ 登录模态框已关闭")
                            break
                    else:
                        print("✓ 未检测到登录模态框")
                        break
                except:
                    pass
                await self.page.wait_for_timeout(1000)
            
            # 最终验证登录状态
            print("🔍 最终验证登录状态...")
            final_check = await self._is_logged_in()
            if not final_check:
                print("✗ 登录验证失败")
                # 保存调试截图
                try:
                    debug_screenshot = REPORTS_DIR / f"debug_login_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await self.page.screenshot(path=str(debug_screenshot))
                    print(f"📸 调试截图已保存: {debug_screenshot}")
                except:
                    pass
                return False
            else:
                print("✓ 登录状态验证成功")
            
            # 保存登录状态
            await login_tool.save_login_state()
            
            # 保存cookie到数据库
            try:
                cookies = await self.page.context.cookies()
                self.account_pool.update_cookie(account.id, json.dumps(cookies))
            except:
                pass
            
            self.current_account = account
            print("✓ 自动登录成功，已准备好生成报告")
            return True
            
        except Exception as e:
            print(f"Login failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    async def _perform_login_old(self, email: str, password: str) -> bool:
        """执行登录操作 - 适配新的Surf登录流程"""
        try:
            print("🔍 查找登录按钮...")
            # 新的Surf界面使用中文"登录"按钮
            login_button_selectors = [
                'button:has-text("登录")',
                'button:has-text("Sign in")',
                'button:has-text("Login")',
                'button:has-text("Log in")',
                'a:has-text("登录")',
                'a:has-text("Sign in")',
                '[data-testid*="login"]',
                '.login-button'
            ]

            login_button = None
            for selector in login_button_selectors:
                try:
                    button = await self.page.query_selector(selector)
                    if button and await button.is_visible():
                        login_button = button
                        print(f"✓ 找到登录按钮: {selector}")
                        break
                except:
                    continue

            if not login_button:
                print("✗ 未找到登录按钮")
                return False

            # 点击登录按钮，查看会跳转到什么页面
            print("🖱️ 点击登录按钮...")
            await login_button.click()
            await self.page.wait_for_timeout(3000)

            # 检查是否跳转到登录页面或弹出了登录模态框
            print(f"📍 点击后URL: {self.page.url}")

            # 等待可能的登录表单加载
            await self.page.wait_for_timeout(2000)

            # 现在尝试查找登录表单
            print("🔍 查找登录表单...")

            # 多种选择器尝试填写邮箱
            email_selectors = [
                'input[type="email"]',
                'input[name="email"]',
                'input[placeholder*="email" i]',
                'input[placeholder*="邮箱" i]',
                'input[placeholder*="mail" i]',
                '#email',
                '[data-testid*="email"]',
                'input[autocomplete="email"]'
            ]

            email_found = False
            for selector in email_selectors:
                try:
                    await self.page.fill(selector, email)
                    print(f"✓ 找到邮箱输入框: {selector}")
                    email_found = True
                    break
                except:
                    continue

            if not email_found:
                print("✗ 未找到邮箱输入框")
                return False

            # 多种选择器尝试填写密码
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[placeholder*="password" i]',
                'input[placeholder*="密码" i]',
                '#password',
                '[data-testid*="password"]',
                'input[autocomplete="current-password"]'
            ]

            password_found = False
            for selector in password_selectors:
                try:
                    await self.page.fill(selector, password)
                    print(f"✓ 找到密码输入框: {selector}")
                    password_found = True
                    break
                except:
                    continue

            if not password_found:
                print("✗ 未找到密码输入框")
                return False

            # 点击提交按钮
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("登录")',
                'button:has-text("Sign in")',
                'button:has-text("Login")',
                'button:has-text("Submit")',
                '[data-testid*="submit"]',
                'button:has-text("Continue")',
                'button:has-text("Next")'
            ]

            submit_found = False
            for selector in submit_selectors:
                try:
                    await self.page.click(selector)
                    print(f"✓ 点击提交按钮: {selector}")
                    submit_found = True
                    break
                except:
                    continue

            if not submit_found:
                # 尝试按回车键
                await self.page.keyboard.press('Enter')
                print("✓ 按回车键提交")

            # 等待登录完成
            print("⏳ 等待登录完成...")
            await self.page.wait_for_timeout(5000)

            return await self._is_logged_in()

        except Exception as e:
            print(f"Login operation failed: {e}")
            return False
    
    async def _is_logged_in(self) -> bool:
        """检查是否已登录 - 适配新的Surf界面"""
        try:
            # 检查是否还存在登录按钮（中文界面）
            login_indicators = [
                'button:has-text("登录")',
                'text=Sign in',
                'text=Sign up',
                'text=Login',
                'text=Log in',
                'button:has-text("Sign in")',
                'button:has-text("Login")',
                'button:has-text("Log in")',
                '.login-button',
                '[data-testid*="login"]'
            ]

            # 如果找到登录按钮，说明未登录
            for indicator in login_indicators:
                try:
                    login_button = await self.page.query_selector(indicator)
                    if login_button and await login_button.is_visible():
                        return False
                except Exception:
                    continue

            # 如果存在登录/验证码对话框，视为未登录
            try:
                login_dialog = await self.page.query_selector('[role="dialog"], .modal, .login-modal, [class*="login"], [class*="dialog"]')
                if login_dialog and await login_dialog.is_visible():
                    return False
            except:
                pass

            # 检查是否存在已登录的标志
            logged_in_indicators = [
                '.user-avatar',
                '.user-profile',
                '[data-testid*="user"]',
                '.logout-button',
                'text=Logout',
                'text=Sign out',
                'text=退出登录',  # 中文
                '.chat-input',  # 如果能找到聊天输入框，说明已登录
                '.message-input',
                '[data-testid*="chat"]',
                '.research-button',  # 研究按钮
                'button:has-text("Research")',
                'button:has-text("研究")'  # 中文研究按钮
            ]

            for indicator in logged_in_indicators:
                try:
                    element = await self.page.query_selector(indicator)
                    if element and await element.is_visible():
                        return True
                except:
                    continue

            # 检查URL是否包含chat或research路径（已登录的标志）
            current_url = self.page.url
            if any(path in current_url for path in ['/chat', '/research', '/dashboard']):
                # 仅当同时存在已登录特征或输入框时才判定已登录，避免误判
                try:
                    chat_input = await self.page.query_selector('textarea, [contenteditable="true"], [role="textbox"]')
                    if chat_input and await chat_input.is_visible():
                        return True
                except:
                    pass

            # 检查是否还在登录相关页面
            if any(path in current_url.lower() for path in ['login', 'signin', 'auth']):
                return False

            # 检查是否有错误信息（比如密码错误等）
            error_indicators = [
                'text=Invalid',
                'text=Error',
                'text=Failed',
                'text=错误',
                'text=失败',
                '.error-message',
                '[class*="error"]'
            ]

            for indicator in error_indicators:
                try:
                    error_element = await self.page.query_selector(indicator)
                    if error_element and await error_element.is_visible():
                        print("⚠️ 检测到错误信息，可能登录失败")
                        return False
                except:
                    continue

            # 没有任何已登录特征时，默认未登录，避免误判
            print("⚠️ 未检测到已登录特征，视为未登录")
            return False

        except Exception as e:
            print(f"Login check failed: {e}")
            return False
    
    def _build_research_query(self, project: Project) -> str:
        """
        根据数据库中的项目信息构建研究查询
        直接输入项目的详细信息，让Surf AI基于这些信息生成分析
        """
        parts = []
        
        # 添加项目基本信息
        parts.append(f"{project.name}")
        
        if project.one_liner:
            parts.append(f"{project.one_liner}")
        
        if project.description:
            parts.append(f"{project.description}")
        
        # 添加关键信息
        info_parts = []
        if project.token_symbol:
            info_parts.append(f"代币: {project.token_symbol}")
        if project.total_funding:
            info_parts.append(f"融资: ${project.total_funding:,.0f}")
        if project.tags and isinstance(project.tags, list) and len(project.tags) > 0:
            info_parts.append(f"赛道: {', '.join(project.tags)}")
        
        if info_parts:
            parts.append(", ".join(info_parts))
        
        # 添加投资者信息
        if project.investors and isinstance(project.investors, list) and len(project.investors) > 0:
            investor_names = []
            for inv in project.investors:
                if isinstance(inv, dict):
                    name = inv.get('name', '')
                    if name:
                        investor_names.append(name)
                elif isinstance(inv, str):
                    investor_names.append(inv)
            if investor_names:
                parts.append(f"投资方: {', '.join(investor_names[:10])}")
        
        # 构建最终查询文本
        query_text = "\n\n".join(parts)
        
        # 打印查询内容用于调试
        print(f"📝 构建的查询内容（长度: {len(query_text)} 字符）:")
        print("=" * 60)
        print(query_text[:800] + ("..." if len(query_text) > 800 else ""))
        print("=" * 60)
        
        return query_text

    async def _switch_surf_mode(self, mode: ReportMode) -> bool:
        """
        切换Surf页面的模式按钮
        根据系统选择的模式，点击Surf页面上对应的模式按钮
        
        Args:
            mode: 报告模式 - chat(快速问答) 或 research(深度研究)
        
        Returns:
            是否切换成功
        """
        try:
            # 根据模式选择对应的选择器（实际页面使用div而非button）
            if mode == ReportMode.RESEARCH:
                # 深度研究模式
                mode_selectors = [
                    'div[data-slot="tooltip-trigger"]:has-text("深度研究")',  # 最精确：带tooltip属性
                    'div.cursor-pointer:has-text("深度研究")',  # 带cursor-pointer类
                    'div:has-text("深度研究")',  # 直接文本匹配
                    'div:has-text("In-depth Research")',
                    'text=深度研究',
                    'text=In-depth Research'
                ]
            else:
                # 快速问答模式
                mode_selectors = [
                    'div[data-slot="tooltip-trigger"]:has-text("快速问答")',  # 最精确：带tooltip属性
                    'div.cursor-pointer:has-text("快速问答")',  # 带cursor-pointer类
                    'div:has-text("快速问答")',  # 直接文本匹配
                    'div:has-text("Quick Q&A")',
                    'text=快速问答',
                    'text=Quick Q&A'
                ]
            
            # 尝试查找并点击模式元素
            for selector in mode_selectors:
                try:
                    # 等待元素出现
                    element = await self.page.wait_for_selector(selector, timeout=10000, state='visible')
                    if element:
                        # 检查元素是否可见和可点击
                        is_visible = await element.is_visible()
                        if not is_visible:
                            continue
                        
                        # 如果找到的是外层div，尝试找到内部包含文本的可点击元素
                        text = await element.inner_text()
                        if mode == ReportMode.RESEARCH:
                            if '深度研究' not in text:
                                # 可能是外层容器，查找内部包含"深度研究"的元素
                                inner_element = await element.query_selector('div:has-text("深度研究")')
                                if inner_element and await inner_element.is_visible():
                                    element = inner_element
                        else:
                            if '快速问答' not in text:
                                # 可能是外层容器，查找内部包含"快速问答"的元素
                                inner_element = await element.query_selector('div:has-text("快速问答")')
                                if inner_element and await inner_element.is_visible():
                                    element = inner_element
                        
                        print(f"🔄 点击模式元素进行切换: {selector}")
                        
                        # 滚动到元素可见
                        await element.scroll_into_view_if_needed()
                        await self.page.wait_for_timeout(500)
                        
                        # 点击元素
                        await element.click(timeout=10000)
                        await self.page.wait_for_timeout(2000)  # 等待模式切换完成
                        
                        print(f"✓ 模式切换完成: {selector}")
                        return True
                except Exception as e:
                    continue
            
            # 如果找不到，尝试查找所有可能的模式切换元素（包括div）
            print("⚠️ 未找到模式元素，尝试查找所有可能的模式切换元素...")
            try:
                # 查找所有包含模式文本的元素（包括div和button）
                all_elements = await self.page.query_selector_all('div.cursor-pointer, button, [role="button"], [data-slot="tooltip-trigger"]')
                for element in all_elements:
                    try:
                        if not await element.is_visible():
                            continue
                        
                        text = await element.inner_text()
                        text_clean = text.strip()
                        
                        if mode == ReportMode.RESEARCH:
                            if '深度研究' in text_clean or 'In-depth Research' in text_clean:
                                print(f"✓ 通过文本匹配找到模式元素: {text_clean[:50]}")
                                await element.click(timeout=10000)
                                await self.page.wait_for_timeout(2000)
                                return True
                        else:
                            if '快速问答' in text_clean or 'Quick Q&A' in text_clean:
                                print(f"✓ 通过文本匹配找到模式元素: {text_clean[:50]}")
                                await element.click(timeout=10000)
                                await self.page.wait_for_timeout(2000)
                                return True
                    except:
                        continue
            except Exception as e:
                print(f"⚠️ 查找模式元素时出错: {e}")
            
            print("⚠️ 未找到模式切换按钮，可能页面结构已变化")
            return False
            
        except Exception as e:
            print(f"⚠️ 切换模式时出错: {e}")
            return False

    async def _generate_report_for_project(
        self, 
        project: Project, 
        mode: ReportMode = ReportMode.CHAT
    ) -> Optional[str]:
        """
        为单个项目生成投研报告
        
        Args:
            project: 项目对象
            mode: 生成模式 - chat(快速问答) 或 research(深度研究)
        
        Returns:
            PDF文件路径
        """
        try:
            # 首先确保已登录（如果未登录，先执行完整登录流程）
            print("=" * 60)
            print("🔐 步骤1: 检查并确保登录状态")
            print("=" * 60)
            
            is_logged_in = await self._is_logged_in()
            if not is_logged_in:
                print("⚠️ 检测到未登录状态，开始完整登录流程...")
                account = self.current_account
                if not account:
                    print("✗ 没有当前账号信息，无法登录")
                    return None
                
                print(f"📧 使用账号: {account.email}")
                print("🔄 执行自动登录（IMAP获取验证码）...")
                
                login_success = await self._login(account)
                if not login_success:
                    print("✗ 登录失败，无法生成报告")
                    return None
                
                # 登录成功后，等待页面稳定
                print("⏳ 等待登录完成并页面稳定...")
                await self.page.wait_for_timeout(5000)
                
                # 最终验证登录状态
                final_login_check = await self._is_logged_in()
                if not final_login_check:
                    print("✗ 登录验证失败，无法继续生成报告")
                    # 保存调试截图
                    try:
                        debug_screenshot = REPORTS_DIR / f"debug_login_final_check_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        await self.page.screenshot(path=str(debug_screenshot))
                        print(f"📸 调试截图已保存: {debug_screenshot}")
                    except:
                        pass
                    return None
                
                print("✓ 登录成功，已准备好生成报告")
            else:
                print("✓ 已登录，继续生成报告")
            
            print("=" * 60)
            print("📊 步骤2: 开始生成报告")
            print("=" * 60)
            
            # 根据模式选择不同的页面和等待时间
            if mode == ReportMode.RESEARCH:
                # 深度研究模式
                print(f"🌐 导航到研究页面: {settings.surf_base_url}/research")
                await self.page.goto(
                    f"{settings.surf_base_url}/research",
                    wait_until="domcontentloaded",
                    timeout=120000  # 2分钟超时
                )
                wait_time = 180000  # 3分钟
                max_timeout = 600000  # 最长等待10分钟
            else:
                # 快速问答模式 - 如果已经在chat页面，不需要重新导航
                current_url = self.page.url
                if '/chat' not in current_url:
                    print(f"🌐 导航到聊天页面: {settings.surf_base_url}/chat")
                    await self.page.goto(
                        f"{settings.surf_base_url}/chat",
                        wait_until="domcontentloaded",
                        timeout=120000  # 2分钟超时
                    )
                else:
                    print("✓ 已在chat页面，无需导航")
                wait_time = 30000  # 30秒
                max_timeout = 120000  # 最长等待2分钟
            
            # 等待页面稳定并确保关键元素加载
            print("⏳ 等待页面完全加载...")
            await self.page.wait_for_timeout(3000)
            
            # 再次验证登录状态（导航后）
            print("🔍 导航后验证登录状态...")
            is_logged_in_after_nav = await self._is_logged_in()
            if not is_logged_in_after_nav:
                print("✗ 导航后登录状态丢失，无法生成报告")
                # 保存调试截图
                try:
                    debug_screenshot = REPORTS_DIR / f"debug_lost_login_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await self.page.screenshot(path=str(debug_screenshot))
                    print(f"📸 调试截图已保存: {debug_screenshot}")
                except:
                    pass
                return None
            print("✓ 登录状态确认")
            
            # 等待登录模态框关闭（如果存在）
            print("⏳ 等待登录模态框关闭...")
            modal_closed = False
            for i in range(10):  # 最多等待10秒
                try:
                    # 检查是否存在登录模态框
                    login_modal = await self.page.query_selector('[role="dialog"], .modal, .login-modal, [class*="modal"]')
                    if login_modal:
                        is_visible = await login_modal.is_visible()
                        if not is_visible:
                            modal_closed = True
                            break
                    else:
                        # 没有找到模态框，可能已经关闭
                        modal_closed = True
                        break
                except:
                    pass
                await self.page.wait_for_timeout(1000)
            
            if not modal_closed:
                print("⚠️ 登录模态框可能仍然存在，继续执行...")
            
            # 尝试等待一些关键元素出现（如果存在）
            try:
                # 等待页面主体加载
                await self.page.wait_for_selector('body', timeout=10000)
                # 尝试等待可能的输入框出现
                await self.page.wait_for_timeout(2000)
            except:
                pass
            
            # 再次验证登录状态
            is_logged_in_final = await self._is_logged_in()
            if not is_logged_in_final:
                print("✗ 最终验证：未登录状态，无法生成报告")
                # 保存调试截图
                try:
                    debug_screenshot = REPORTS_DIR / f"debug_not_logged_in_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await self.page.screenshot(path=str(debug_screenshot))
                    print(f"📸 调试截图已保存: {debug_screenshot}")
                except:
                    pass
                return None
            
            print("✓ 页面加载完成，登录状态确认")
            
            # 根据模式切换Surf页面的模式按钮
            print(f"🔄 切换Surf页面模式为: {'深度研究' if mode == ReportMode.RESEARCH else '快速问答'}...")
            mode_switched = await self._switch_surf_mode(mode)
            if not mode_switched:
                print("⚠️ 模式切换失败，但继续执行...")
            else:
                print("✓ 模式切换成功")
                await self.page.wait_for_timeout(2000)  # 等待模式切换完成
            
            # 构建包含项目详细信息的研究查询
            research_query = self._build_research_query(project)

            # 记录发送前页面文本长度，用于后续判断是否真的发送了内容
            try:
                initial_text_len = await self.page.evaluate('() => (document.body.innerText || document.body.textContent || \"\").length')
            except:
                initial_text_len = 0
            
            # 找到输入框并输入查询（改进的选择器逻辑）
            print("🔍 查找输入框（最多等待60秒）...")
            input_element = await self._find_input_element(max_wait=60000)
            if not input_element:
                print("✗ 未找到输入框")
                # 保存截图用于调试
                try:
                    debug_screenshot = REPORTS_DIR / f"debug_no_input_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await self.page.screenshot(path=str(debug_screenshot))
                    print(f"📸 调试截图已保存: {debug_screenshot}")
                except:
                    pass
                return None

            print("✓ 找到输入框，准备输入内容...")
            
            # 输入前再次验证元素状态
            try:
                # 等待元素稳定
                await self.page.wait_for_timeout(1000)
                
                # 检查元素是否仍然可见和可编辑
                is_visible = await input_element.is_visible()
                if not is_visible:
                    print("⚠️ 输入框不可见，尝试重新查找...")
                    input_element = await self._find_input_element(max_wait=10000)
                    if not input_element:
                        print("✗ 重新查找输入框失败")
                        return None
                
                # 滚动到元素位置
                await input_element.scroll_into_view_if_needed()
                await self.page.wait_for_timeout(500)
                
                # 获取元素标签名（用于后续判断输入方式）
                tag_name = await input_element.evaluate('el => el.tagName.toLowerCase()')
                
                # 检查元素是否可编辑
                try:
                    is_editable = await input_element.is_editable()
                    if not is_editable:
                        # 如果是 contenteditable 元素，可能不需要 is_editable 检查
                        if tag_name not in ['div', 'span'] or not await input_element.evaluate('el => el.contentEditable === "true"'):
                            print("⚠️ 输入框不可编辑，尝试点击激活...")
                except:
                    pass
                
                # 点击聚焦（使用较短的超时时间，如果失败则继续）
                try:
                    await input_element.click(timeout=5000)
                    await self.page.wait_for_timeout(500)
                except Exception as e:
                    print(f"⚠️ 点击输入框失败，尝试继续: {e}")
                    # 尝试使用 focus() 方法
                    try:
                        await input_element.focus()
                        await self.page.wait_for_timeout(500)
                    except:
                        pass
                
                # 清空输入框（如果有内容）
                try:
                    await input_element.clear(timeout=5000)
                except:
                    # 如果 clear 失败，尝试手动清空
                    try:
                        if tag_name in ['input', 'textarea']:
                            await input_element.evaluate('el => el.value = ""')
                        else:
                            await input_element.evaluate('el => el.textContent = ""')
                    except:
                        pass
                
                # 优先使用 fill() 方法，更快更可靠
                print(f"📝 开始输入内容（长度: {len(research_query)} 字符）...")
                
                input_success = False
                try:
                    # 尝试使用 fill() 方法（适用于 input 和 textarea）
                    if tag_name in ['input', 'textarea']:
                        await input_element.fill(research_query, timeout=30000)  # 30秒超时
                        input_success = True
                        print(f"✓ 使用 fill() 方法输入完成")
                    else:
                        # contenteditable 元素，使用 type() 方法
                        raise Exception("需要使用 type() 方法")
                except Exception as e:
                    print(f"⚠️ fill() 方法失败，尝试使用 type() 方法: {e}")
                    try:
                        # 如果内容很长，分段输入
                        if len(research_query) > 200:
                            chunk_size = 100
                            chunks = [research_query[i:i+chunk_size] for i in range(0, len(research_query), chunk_size)]
                            for i, chunk in enumerate(chunks):
                                await input_element.type(chunk, delay=50, timeout=30000)  # 30秒超时
                                if i < len(chunks) - 1:
                                    await self.page.wait_for_timeout(200)
                            print(f"✓ 内容已分段输入完成")
                        else:
                            # 内容较短，直接输入
                            await input_element.type(research_query, delay=50, timeout=30000)  # 30秒超时
                            print(f"✓ 内容已输入")
                        input_success = True
                    except Exception as e2:
                        print(f"✗ type() 方法也失败: {e2}")
                        # 最后尝试使用 evaluate 直接设置值
                        try:
                            if tag_name in ['input', 'textarea']:
                                await input_element.evaluate(f'el => el.value = {repr(research_query)}')
                            else:
                                await input_element.evaluate(f'el => el.textContent = {repr(research_query)}')
                            # 触发 input 事件
                            await input_element.evaluate('el => el.dispatchEvent(new Event("input", { bubbles: true }))')
                            input_success = True
                            print(f"✓ 使用 evaluate 直接设置值完成")
                        except Exception as e3:
                            print(f"✗ 所有输入方法都失败: {e3}")
                            raise
                
                if not input_success:
                    raise Exception("无法输入内容")
                
                await self.page.wait_for_timeout(500)
                
                # 验证内容是否已输入
                try:
                    if tag_name in ['input', 'textarea']:
                        current_value = await input_element.input_value()
                    else:
                        current_value = await input_element.inner_text()
                    
                    if len(current_value) < len(research_query) * 0.8:  # 至少输入了80%的内容
                        print(f"⚠️ 输入内容可能不完整（期望: {len(research_query)}, 实际: {len(current_value)}）")
                        # 尝试重新输入（使用 evaluate 方法，更快）
                        try:
                            if tag_name in ['input', 'textarea']:
                                await input_element.evaluate(f'el => el.value = {repr(research_query)}')
                            else:
                                await input_element.evaluate(f'el => el.textContent = {repr(research_query)}')
                            await input_element.evaluate('el => el.dispatchEvent(new Event("input", { bubbles: true }))')
                        except:
                            pass
                except:
                    pass
                
                # 点击发送按钮（右下角的箭头按钮）
                print("🔍 查找并点击发送按钮...")
                send_button_clicked = False
                
                # 保存输入前的截图
                try:
                    before_send_screenshot = REPORTS_DIR / f"debug_before_send_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await self.page.screenshot(path=str(before_send_screenshot))
                    print(f"📸 输入后截图已保存: {before_send_screenshot}")
                except:
                    pass
                
                # 等待发送按钮出现（输入内容后发送按钮可能才会变为可点击状态）
                await self.page.wait_for_timeout(1000)
                
                # 触发 input 和 change 事件，确保按钮变为可点击状态
                try:
                    # 对于 input/textarea，触发 input 和 change 事件
                    if tag_name in ['input', 'textarea']:
                        await input_element.evaluate('''el => {
                            el.dispatchEvent(new Event("input", { bubbles: true }));
                            el.dispatchEvent(new Event("change", { bubbles: true }));
                        }''')
                    else:
                        # 对于 contenteditable，触发 input 事件
                        await input_element.evaluate('el => el.dispatchEvent(new Event("input", { bubbles: true }))')
                    
                    # 等待按钮状态更新
                    await self.page.wait_for_timeout(1000)
                except Exception as e:
                    print(f"⚠️ 触发事件失败: {e}")
                
                # 发送按钮的选择器（优先匹配包含 lucide-arrow-up 的按钮）
                send_button_selectors = [
                    'button:has(svg.lucide-arrow-up)',  # 最精确：包含 lucide-arrow-up SVG 的按钮
                    'button:has(svg[class*="arrow-up"])',  # 包含 arrow-up 的 SVG
                    'button.bg-brand',  # 包含 bg-brand 类的按钮（发送按钮通常是品牌色）
                    'button[class*="bg-brand"]',  # 包含 bg-brand 的按钮
                    'button[type="submit"]',
                    'button:has(svg[class*="arrow"])',  # 包含 arrow 的 SVG
                    'button:has(svg[class*="lucide"])',  # 包含 lucide 图标的按钮
                    'button[aria-label*="send" i]',
                    'button[aria-label*="发送" i]',
                    'button[aria-label*="submit" i]',
                    'button:has(svg[class*="send"])',
                    '[class*="send-button"]',
                    '[class*="submit-button"]',
                    'button:has(svg)',  # 包含SVG图标的按钮（可能是箭头）
                    '[role="button"]:has(svg)',
                ]
                
                print(f"🔍 尝试 {len(send_button_selectors)} 种发送按钮选择器...")
                # 尝试查找并点击发送按钮
                for i, selector in enumerate(send_button_selectors, 1):
                    try:
                        print(f"  尝试选择器 {i}/{len(send_button_selectors)}: {selector}")
                        send_buttons = await self.page.query_selector_all(selector)
                        print(f"    找到 {len(send_buttons)} 个匹配元素")
                        
                        for j, send_button in enumerate(send_buttons, 1):
                            try:
                                is_visible = await send_button.is_visible()
                                if not is_visible:
                                    continue
                                
                                # 检查按钮是否被禁用
                                is_disabled = await send_button.is_disabled()
                                if is_disabled:
                                    print(f"    元素 {j}: 可见但被禁用，跳过")
                                    continue
                                
                                # 检查按钮位置和尺寸（发送按钮通常是 24x24 或类似的小按钮）
                                button_box = await send_button.bounding_box()
                                if button_box:
                                    width = button_box['width']
                                    height = button_box['height']
                                    print(f"    元素 {j}: 可见，位置: x={button_box['x']:.0f}, y={button_box['y']:.0f}, w={width:.0f}, h={height:.0f}")
                                    
                                    # 获取按钮的类名和属性
                                    class_name = (await send_button.get_attribute('class') or '').lower()
                                    aria_label = (await send_button.get_attribute('aria-label') or '').lower()
                                    
                                    # 检查是否包含发送按钮的特征
                                    has_brand_bg = 'bg-brand' in class_name
                                    has_arrow_svg = False
                                    try:
                                        svg = await send_button.query_selector('svg')
                                        if svg:
                                            svg_class = (await svg.get_attribute('class') or '').lower()
                                            has_arrow_svg = 'arrow' in svg_class or 'lucide' in svg_class
                                    except:
                                        pass
                                    
                                    # 优先点击包含 bg-brand 和箭头 SVG 的按钮（典型的发送按钮）
                                    if has_brand_bg or has_arrow_svg or i <= 3:  # 前3个选择器或包含特征
                                        # 滚动到按钮位置
                                        await send_button.scroll_into_view_if_needed()
                                        await self.page.wait_for_timeout(300)
                                        
                                        # 点击按钮
                                        await send_button.click(timeout=10000)
                                        await self.page.wait_for_timeout(2000)
                                        print(f"✓ 成功点击发送按钮: {selector} (元素 {j})")
                                        send_button_clicked = True
                                        break
                            except Exception as e:
                                print(f"    元素 {j} 点击失败: {e}")
                                continue
                        
                        if send_button_clicked:
                            break
                    except Exception as e:
                        print(f"  选择器 {i} 失败: {e}")
                        continue
                
                # 如果还是找不到，列出所有包含SVG的按钮用于调试
                if not send_button_clicked:
                    print("⚠️ 未找到发送按钮，列出所有可能的按钮...")
                    try:
                        all_buttons = await self.page.query_selector_all('button, [role="button"]')
                        visible_button_count = 0
                        for button in all_buttons:
                            try:
                                is_visible = await button.is_visible()
                                if is_visible:
                                    visible_button_count += 1
                                    if visible_button_count <= 10:  # 只列出前10个
                                        class_name = await button.get_attribute('class') or ''
                                        aria_label = await button.get_attribute('aria-label') or ''
                                        button_text = (await button.inner_text() or '').replace('\n', ' ')[:50]
                                        button_box = await button.bounding_box()
                                        pos = f"x={button_box['x']:.0f}, y={button_box['y']:.0f}" if button_box else "pos=?"
                                        print(f"    按钮 {visible_button_count}: class='{class_name[:50]}', aria-label='{aria_label[:50]}', text='{button_text}', {pos}")
                            except:
                                continue
                        print(f"  共找到 {visible_button_count} 个可见按钮")
                    except:
                        pass
                    
                    # 使用回车键作为备用
                    print("⚠️ 未找到发送按钮，使用回车键发送...")
                    await self.page.keyboard.press('Enter')
                    await self.page.wait_for_timeout(2000)
                    send_button_clicked = True
                    print("✓ 已按回车键发送请求")
                else:
                    print("✓ 已通过发送按钮发送请求")
                
            except Exception as e:
                print(f"✗ 输入内容时出错: {e}")
                # 保存调试截图
                try:
                    debug_screenshot = REPORTS_DIR / f"debug_input_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await self.page.screenshot(path=str(debug_screenshot))
                    print(f"📸 调试截图已保存: {debug_screenshot}")
                except:
                    pass
                return None

            # 如果仍未成功发送，直接返回失败
            if not send_button_clicked:
                print("✗ 未能确认发送请求，终止生成")
                return None

            # 发送后校验页面文本是否有新增（粗略判断消息是否发送出去）
            try:
                await self.page.wait_for_timeout(2000)
                after_text_len = await self.page.evaluate('() => (document.body.innerText || document.body.textContent || \"\").length')
                if after_text_len <= initial_text_len:
                    print(f"⚠️ 页面文本长度未增加（前: {initial_text_len}, 后: {after_text_len}），可能未发送成功")
            except:
                pass
            
            # 等待报告生成（在等待过程中定期检查登录状态）
            print(f"⏳ 等待报告生成 ({wait_time/1000}秒)...")
            
            # 分段等待，每10秒检查一次登录状态
            wait_segments = wait_time // 10000  # 每10秒一段
            for i in range(wait_segments):
                await self.page.wait_for_timeout(10000)
                # 每10秒检查一次登录状态
                is_still_logged_in = await self._is_logged_in()
                if not is_still_logged_in:
                    print(f"⚠️ 等待过程中检测到登录状态丢失（{i*10}秒），尝试重新登录...")
                    account = self.current_account
                    if account:
                        # 快速重新登录
                        login_success = await self._login(account)
                        if not login_success:
                            print("✗ 重新登录失败")
                            return None
                        # 重新导航到目标页面
                        target_url = f"{settings.surf_base_url}/chat" if mode == ReportMode.CHAT else f"{settings.surf_base_url}/research"
                        await self.page.goto(target_url, wait_until="domcontentloaded", timeout=120000)
                        await self.page.wait_for_timeout(2000)
                    else:
                        print("✗ 无法重新登录：没有当前账号信息")
                        return None
            
            # 等待剩余时间
            remaining_time = wait_time % 10000
            if remaining_time > 0:
                await self.page.wait_for_timeout(remaining_time)
            
            # 等待生成完成的标志（改进的检测逻辑）
            print("🔍 等待内容生成完成...")
            content_found = await self._wait_for_content(max_timeout)
            if not content_found:
                print("⚠️ 未检测到内容生成，继续等待...")
                # 如果未检测到内容，再等待一段时间
                print("⏳ 额外等待30秒以确保内容生成...")
                await self.page.wait_for_timeout(30000)
                # 再次检查内容
                content_found_retry = await self._wait_for_content(60000)
                if not content_found_retry:
                    print("⚠️ 仍然未检测到内容，但继续生成PDF")
                else:
                    print("✓ 内容已生成")
            else:
                print("✓ 内容已生成")
            
            # 额外等待确保内容完全加载
            print("⏳ 等待内容完全加载（10秒）...")
            await self.page.wait_for_timeout(10000)
            
            # 检测是否还有生成进度提示（如"还剩约X分钟"、进度条等）
            print("🔍 检测是否还在生成中...")
            max_wait_for_completion = 300  # 最多等待5分钟
            wait_count = 0
            
            while wait_count < max_wait_for_completion:
                try:
                    # 检测页面上的生成进度提示
                    is_generating = await self.page.evaluate('''() => {
                        const bodyText = document.body.innerText || document.body.textContent || '';
                        
                        // 检测各种"正在生成"的提示文本
                        const generatingTexts = [
                            '还剩约',
                            '分钟',
                            'minute',
                            '正在生成',
                            'Generating',
                            'Processing',
                            'Please wait',
                            '请稍候',
                            '处理中'
                        ];
                        
                        for (const text of generatingTexts) {
                            if (bodyText.includes(text)) {
                                return true;
                            }
                        }
                        
                        // 检测进度条元素
                        const progressElements = document.querySelectorAll('[role="progressbar"], .progress, [class*="progress"], [class*="loading"]');
                        for (const el of progressElements) {
                            if (el.offsetParent !== null) {  // 元素可见
                                return true;
                            }
                        }
                        
                        return false;
                    }''')
                    
                    if is_generating:
                        if wait_count % 5 == 0:  # 每5秒输出一次
                            print(f"⏳ 检测到正在生成中，继续等待... ({wait_count}秒)")
                        await self.page.wait_for_timeout(1000)
                        wait_count += 1
                    else:
                        print(f"✓ 内容生成完成（等待了{wait_count}秒）")
                        break
                        
                except Exception as e:
                    print(f"⚠️ 检测生成状态时出错: {e}，停止检测")
                    break
            
            if wait_count >= max_wait_for_completion:
                print(f"⚠️ 等待生成完成超时（{max_wait_for_completion}秒），继续生成PDF")
            
            # 生成完成后再等待5秒，确保页面稳定
            print("⏳ 生成完成，等待页面稳定（5秒）...")
            await self.page.wait_for_timeout(5000)
            
            # 生成PDF前检查页面内容是否稳定（10秒内无变化）
            print("🔍 生成PDF前检查页面内容是否稳定...")
            try:
                # 获取初始文本长度
                page_text_initial = await self.page.evaluate('''() => {
                    const body = document.body;
                    if (!body) return '';
                    return body.innerText || body.textContent || '';
                }''')
                text_length_initial = len(page_text_initial.strip())
                print(f"📊 初始页面文本长度: {text_length_initial} 字符")
                
                if text_length_initial < 500:
                    print("⚠️ 页面内容过少（少于500字符），可能未生成报告，继续等待...")
                    await self.page.wait_for_timeout(30000)
                    # 再次检查
                    page_text_retry = await self.page.evaluate('''() => {
                        const body = document.body;
                        if (!body) return '';
                        return body.innerText || body.textContent || '';
                    }''')
                    text_length_retry = len(page_text_retry.strip())
                    print(f"📊 再次检查页面文本长度: {text_length_retry} 字符")
                    
                    if text_length_retry < 500:
                        print("⚠️ 页面内容仍然过少，保存调试截图...")
                        try:
                            debug_screenshot = REPORTS_DIR / f"debug_low_content_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                            await self.page.screenshot(path=str(debug_screenshot))
                            print(f"📸 调试截图已保存: {debug_screenshot}")
                        except:
                            pass
                    else:
                        text_length_initial = text_length_retry
                        print("✓ 内容已足够，开始检查内容是否稳定...")
                else:
                    print("✓ 内容已足够，开始检查内容是否稳定...")
                
                # 等待10秒，每2秒检查一次文本长度是否变化
                print("⏳ 等待10秒，检查页面文本长度是否稳定（无变化）...")
                stable_count = 0
                check_interval = 2  # 每2秒检查一次
                total_checks = 5  # 总共检查5次（10秒）
                last_text_length = text_length_initial
                
                for i in range(total_checks):
                    await self.page.wait_for_timeout(check_interval * 1000)
                    
                    # 获取当前文本长度
                    page_text_current = await self.page.evaluate('''() => {
                        const body = document.body;
                        if (!body) return '';
                        return body.innerText || body.textContent || '';
                    }''')
                    text_length_current = len(page_text_current.strip())
                    
                    print(f"📊 检查 {i+1}/{total_checks}: 当前文本长度: {text_length_current} 字符")
                    
                    # 如果文本长度没有变化（允许小幅波动，比如±10字符）
                    if abs(text_length_current - last_text_length) <= 10:
                        stable_count += 1
                        print(f"✓ 文本长度稳定 ({stable_count}/{total_checks})")
                    else:
                        # 文本长度有变化，重置计数
                        change = text_length_current - last_text_length
                        print(f"⚠️ 文本长度发生变化: {last_text_length} → {text_length_current} (变化: {change:+d})")
                        last_text_length = text_length_current
                        stable_count = 0
                
                # 如果10秒内文本长度稳定（至少4次检查都稳定），可以生成PDF
                if stable_count >= 4:
                    print(f"✓ 页面内容已稳定（{stable_count}/{total_checks}次检查稳定），可以生成PDF")
                else:
                    print(f"⚠️ 页面内容可能仍在变化（稳定次数: {stable_count}/{total_checks}），但继续生成PDF")
                    
            except Exception as e:
                print(f"⚠️ 检查页面内容时出错: {e}")
            
            # 生成PDF前再次验证登录状态
            print("🔍 生成PDF前验证登录状态...")
            is_logged_in_before_pdf = await self._is_logged_in()
            if not is_logged_in_before_pdf:
                print("✗ 生成PDF前检测到未登录状态，尝试最后一次重新登录...")
                account = self.current_account
                if account:
                    login_success = await self._login(account)
                    if not login_success:
                        print("✗ 重新登录失败，无法生成报告")
                        # 保存调试截图
                        try:
                            debug_screenshot = REPORTS_DIR / f"debug_not_logged_before_pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                            await self.page.screenshot(path=str(debug_screenshot))
                            print(f"📸 调试截图已保存: {debug_screenshot}")
                        except:
                            pass
                        return None
                    # 重新导航到目标页面
                    target_url = f"{settings.surf_base_url}/chat" if mode == ReportMode.CHAT else f"{settings.surf_base_url}/research"
                    await self.page.goto(target_url, wait_until="domcontentloaded", timeout=120000)
                    await self.page.wait_for_timeout(3000)
                    # 再次验证
                    is_logged_in_final = await self._is_logged_in()
                    if not is_logged_in_final:
                        print("✗ 重新登录后验证失败，无法生成报告")
                        return None
                    print("✓ 重新登录成功，继续生成PDF")
                else:
                    print("✗ 无法重新登录：没有当前账号信息")
                    return None
            
            # 检查是否还有登录模态框
            try:
                login_modal = await self.page.query_selector('[role="dialog"], .modal, .login-modal, [class*="modal"]')
                if login_modal:
                    is_visible = await login_modal.is_visible()
                    if is_visible:
                        print("⚠️ 检测到登录模态框仍然可见，等待关闭...")
                        # 尝试关闭模态框
                        try:
                            close_button = await login_modal.query_selector('button[aria-label*="close" i], button[aria-label*="关闭" i], .close-button, [class*="close"]')
                            if close_button:
                                await close_button.click()
                                await self.page.wait_for_timeout(1000)
                        except:
                            pass
                        # 等待模态框消失
                        for i in range(5):
                            await self.page.wait_for_timeout(1000)
                            try:
                                if not await login_modal.is_visible():
                                    print("✓ 登录模态框已关闭")
                                    break
                            except:
                                break
            except:
                pass
            
            print("✓ 登录状态确认，开始生成PDF...")
            
            # 生成PDF
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mode_suffix = "research" if mode == ReportMode.RESEARCH else "chat"
            # 清理文件名中的特殊字符
            safe_name = "".join(c for c in project.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            pdf_filename = f"{safe_name}_{mode_suffix}_{timestamp}.pdf"
            pdf_path = REPORTS_DIR / pdf_filename
            
            await self.page.pdf(path=str(pdf_path), format='A4')
            print(f"✓ PDF已生成: {pdf_path}")
            
            return str(pdf_path)
            
        except Exception as e:
            print(f"Report generation failed: {e}")
            # 保存错误截图
            try:
                error_screenshot = REPORTS_DIR / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await self.page.screenshot(path=str(error_screenshot))
                print(f"📸 错误截图已保存: {error_screenshot}")
            except:
                pass
            return None

    async def _find_input_element(self, max_wait: int = 60000):
        """查找输入框元素（带超时等待，更智能的查找策略）"""
        input_selectors = [
            'textarea',
            'textarea[placeholder*="输入" i]',
            'textarea[placeholder*="message" i]',
            'textarea[placeholder*="Ask" i]',
            'textarea[placeholder*="问" i]',
            'input[type="text"]',
            '[contenteditable="true"]',
            '[contenteditable="true"][role="textbox"]',
            '[role="textbox"]',
            '.input-field',
            '.chat-input',
            '.message-input',
            'input[placeholder*="输入" i]',
            'input[placeholder*="输入消息" i]',
            'input[placeholder*="message" i]',
            'div[contenteditable="true"]',
            'div[role="textbox"]',
        ]

        start_time = datetime.now()
        attempt = 0
        
        while (datetime.now() - start_time).total_seconds() * 1000 < max_wait:
            attempt += 1
            
            # 首先在主页面尝试所有选择器
            for selector in input_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        try:
                            is_visible = await element.is_visible()
                            if is_visible:
                                # 检查元素是否可编辑
                                is_editable = await element.is_editable()
                                if is_editable or selector.startswith('[contenteditable') or selector.startswith('[role="textbox"'):
                                    print(f"✓ 找到输入框(主页面): {selector} (尝试 {attempt})")
                                    return element
                        except:
                            continue
                except:
                    continue
            
            # 如果主页面没找到，检查iframe
            try:
                iframes = await self.page.query_selector_all('iframe')
                for iframe in iframes:
                    try:
                        frame = await iframe.content_frame()
                        if frame:
                            for selector in input_selectors:
                                try:
                                    elements = await frame.query_selector_all(selector)
                                    for element in elements:
                                        try:
                                            is_visible = await element.is_visible()
                                            if is_visible:
                                                is_editable = await element.is_editable()
                                                if is_editable or selector.startswith('[contenteditable') or selector.startswith('[role="textbox"'):
                                                    print(f"✓ 找到输入框(iframe): {selector} (尝试 {attempt})")
                                                    return element
                                        except:
                                            continue
                                except:
                                    continue
                    except:
                        continue
            except:
                pass
            
            # 如果没找到，等待后重试
            if attempt % 5 == 0:  # 每5次尝试输出一次进度
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"⏳ 查找输入框中... ({int(elapsed)}秒)")
            
            await self.page.wait_for_timeout(2000)  # 每2秒重试一次
        
        # 超时后，列出所有可能的输入元素用于调试
        print("⚠️ 查找输入框超时，列出页面上所有可能的输入元素...")
        try:
            all_inputs = await self.page.query_selector_all('input, textarea, [contenteditable="true"], [role="textbox"]')
            visible_inputs = []
            for inp in all_inputs:
                try:
                    if await inp.is_visible():
                        tag = await inp.evaluate('el => el.tagName')
                        placeholder = await inp.get_attribute('placeholder') or ''
                        role = await inp.get_attribute('role') or ''
                        contenteditable = await inp.get_attribute('contenteditable') or ''
                        visible_inputs.append({
                            'tag': tag,
                            'placeholder': placeholder,
                            'role': role,
                            'contenteditable': contenteditable
                        })
                except:
                    continue
            
            if visible_inputs:
                print(f"  找到 {len(visible_inputs)} 个可见的输入元素:")
                for i, inp_info in enumerate(visible_inputs[:10], 1):
                    print(f"    {i}. {inp_info['tag']} - placeholder='{inp_info['placeholder']}', role='{inp_info['role']}', contenteditable='{inp_info['contenteditable']}'")
            else:
                print("  未找到任何可见的输入元素")
        except Exception as e:
            print(f"  调试信息获取失败: {e}")
        
        return None

    async def _wait_for_content(self, max_timeout: int) -> bool:
        """等待内容生成（更严格的检测）"""
        content_selectors = [
            '.message-content',
            '.chat-content',
            '.response',
            '.research-content',
            '.report-content',
            'article',
            '.generated-content',
            '[class*="message"]',
            '[class*="content"]',
            'main',
            '[role="main"]',
            '.main-content'
        ]

        start_time = datetime.now()
        check_count = 0
        
        while (datetime.now() - start_time).total_seconds() * 1000 < max_timeout:
            check_count += 1
            
            # 方法1: 检查特定选择器的内容
            for selector in content_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        try:
                            is_visible = await element.is_visible()
                            if is_visible:
                                text_content = await element.inner_text()
                                if text_content and len(text_content.strip()) > 100:  # 至少100个字符
                                    print(f"✓ 检测到内容生成: {selector} (长度: {len(text_content.strip())} 字符)")
                                    return True
                        except:
                            continue
                except:
                    continue
            
            # 方法2: 检查整个页面的文本内容
            try:
                page_text = await self.page.evaluate('''() => {
                    const body = document.body;
                    if (!body) return '';
                    return body.innerText || body.textContent || '';
                }''')
                text_length = len(page_text.strip())
                # 排除输入框和按钮等UI元素的文本
                # 如果页面有大量文本（>500字符），说明内容已生成
                if text_length > 500:
                    print(f"✓ 检测到页面有足够内容: {text_length} 字符")
                    return True
            except:
                pass
            
            # 每5秒输出一次进度
            if check_count % 5 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"⏳ 等待内容生成中... ({int(elapsed)}秒)")

            await self.page.wait_for_timeout(1000)  # 每秒检查一次

        print("⚠️ 等待内容生成超时")
        return False
    
    async def generate_report(
        self, 
        project_id: int, 
        mode: ReportMode = ReportMode.CHAT
    ) -> Report:
        """
        为指定项目生成投研报告
        自动管理账号池和配额
        
        Args:
            project_id: 项目ID
            mode: 生成模式 - chat(快速问答) 或 research(深度研究)
        """
        print(f"🚀 开始生成报告 - 项目ID: {project_id}, 模式: {mode.value}")

        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            error_msg = f"项目 {project_id} 不存在"
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)

        print(f"📋 项目信息: {project.name} ({project.token_symbol or 'N/A'})")
        
        # 获取可用账号
        account = self.account_pool.get_available_account()
        if not account:
            error_msg = "没有可用的Surf账号，所有账号已用完每周配额"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)

        print(f"👤 使用账号: {account.email} (剩余配额: {account.weekly_quota_limit - account.weekly_quota_used})")
        
        # 创建报告记录
        report = Report(
            project_id=project_id,
            surf_account_id=account.id,
            status='generating'
        )
        self.db.add(report)
        self.db.commit()
        print(f"📝 创建报告记录 ID: {report.id}")
        
        try:
            # 初始化浏览器
            print("🌐 初始化浏览器...")
            await self._init_browser()
            
            # 创建新页面（确保页面在使用前已创建）
            try:
                if not self.page:
                    self.page = await self.browser.new_page()
                    print("✓ 创建新页面成功")
                else:
                    # 检查页面是否已关闭
                    try:
                        if self.page.is_closed():
                            print("⚠️ 页面已关闭，重新创建...")
                            self.page = await self.browser.new_page()
                            print("✓ 重新创建页面成功")
                    except Exception:
                        # 如果检查失败，重新创建页面
                        print("⚠️ 页面状态异常，重新创建...")
                        self.page = await self.browser.new_page()
                        print("✓ 重新创建页面成功")
            except Exception as e:
                error_msg = f"无法创建浏览器页面: {e}"
                print(f"✗ {error_msg}")
                raise Exception(error_msg)
            
            # 设置当前账号（用于后续登录）
            self.current_account = account
            
            # 登录（完整流程：导航到页面 → 点击登录按钮 → 输入邮箱 → IMAP获取验证码 → 填写验证码 → 登录）
            print("=" * 60)
            print("🔐 步骤1: 执行自动登录")
            print("=" * 60)
            print("📋 登录流程：")
            print("  1. 导航到Surf页面")
            print("  2. 点击登录按钮")
            print("  3. 输入邮箱并发送验证码")
            print("  4. 使用IMAP获取验证码")
            print("  5. 填写验证码并完成登录")
            print("=" * 60)
            
            if not await self._login(account):
                print("⚠️ 首次登录失败，尝试切换账号...")
                # 尝试切换账号
                account = self.account_pool.switch_to_next()
                if not account or not await self._login(account):
                    error_msg = "无法登录到Surf"
                    print(f"❌ {error_msg}")
                    raise Exception(error_msg)
                report.surf_account_id = account.id
                self.current_account = account
                print(f"🔄 已切换到账号: {account.email}")
            
            # 登录成功后，确保页面在正确位置
            current_url = self.page.url
            print(f"📍 登录后当前URL: {current_url}")
            
            # 如果不在chat或research页面，导航到chat页面
            if '/chat' not in current_url and '/research' not in current_url:
                print("🌐 登录成功，导航到chat页面...")
                await self.page.goto(
                    f"{settings.surf_base_url}/chat",
                    wait_until="domcontentloaded",
                    timeout=120000
                )
                await self.page.wait_for_timeout(3000)
            
            # 最终验证登录状态
            print("🔍 最终验证登录状态...")
            final_login_check = await self._is_logged_in()
            if not final_login_check:
                error_msg = "登录验证失败，无法生成报告"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            print("✓ 登录状态确认，可以开始生成报告")
            
            # 生成报告
            print("=" * 60)
            print(f"📊 步骤2: 开始生成{ '深度研究' if mode == ReportMode.RESEARCH else '快速问答' }报告")
            print("=" * 60)
            pdf_path = await self._generate_report_for_project(project, mode)
            
            if pdf_path:
                # 使用配额
                self.account_pool.use_quota(account.id)
                
                report.report_pdf_path = pdf_path
                report.status = 'completed'
                report.completed_at = datetime.now()
                print(f"✅ 报告生成成功: {pdf_path}")
            else:
                report.status = 'failed'
                report.error_message = "PDF生成失败"
                print("❌ PDF生成失败")
            
        except Exception as e:
            error_msg = str(e)
            report.status = 'failed'
            report.error_message = error_msg
            print(f"❌ 报告生成失败: {error_msg}")

            # 保存错误截图
            if hasattr(self, 'page') and self.page:
                try:
                    error_screenshot = REPORTS_DIR / f"error_report_{report.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await self.page.screenshot(path=str(error_screenshot))
                    print(f"📸 错误截图已保存: {error_screenshot}")
                except Exception as screenshot_error:
                    print(f"⚠️ 无法保存错误截图: {screenshot_error}")
        
        finally:
            print("🔚 清理浏览器资源...")
            await self._close_browser()
            self.db.commit()
            print(f"💾 报告状态已更新: {report.status}")
        
        return report
    
    async def batch_generate_reports(
        self, 
        project_ids: list[int],
        mode: ReportMode = ReportMode.CHAT
    ) -> list[Report]:
        """批量生成报告"""
        reports = []
        
        for project_id in project_ids:
            remaining = self.account_pool.get_total_remaining_quota()
            if remaining <= 0:
                print("No remaining quota for this week")
                break
            
            try:
                report = await self.generate_report(project_id, mode)
                reports.append(report)
            except Exception as e:
                print(f"Failed to generate report for project {project_id}: {e}")
            
            # 间隔一段时间，避免被限流
            # 深度研究模式需要更长间隔
            sleep_time = 30 if mode == ReportMode.RESEARCH else 5
            await asyncio.sleep(sleep_time)
        
        return reports
