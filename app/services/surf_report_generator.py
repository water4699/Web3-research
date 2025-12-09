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
                timeout=10000
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
                    timeout=10000
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
        """登录 Surf 账号"""
        from pathlib import Path
        import json

        try:
            # 首先尝试使用持久化状态（如果存在）
            state_dir = Path("data/browser_state")
            state_file = state_dir / "state.json"

            if state_file.exists():
                try:
                    # 使用持久化上下文
                    context = await self.browser.new_persistent_context(
                        str(state_dir),
                        proxy={"server": settings.proxy_server} if settings.proxy_server else None
                    )
                    self.page = context.pages[0] if context.pages else await context.new_page()
                    self.current_account = account
                    print("✓ 使用持久化浏览器状态")
                    return True
                except Exception as e:
                    print(f"⚠ 持久化状态加载失败: {e}")

            # 如果持久化状态不可用，使用传统登录
            context = await self.browser.new_context()
            self.page = await context.new_page()

            # 如果有保存的cookie，尝试使用
            if account.cookie_data:
                try:
                    cookies = json.loads(account.cookie_data)
                    await context.add_cookies(cookies)

                    # 验证登录状态
                    await self.page.goto(f"{settings.surf_base_url}/chat")
                    await self.page.wait_for_timeout(2000)

                    # 检查是否已登录
                    if await self._is_logged_in():
                        self.current_account = account
                        print("✓ Cookie登录成功")
                        return True
                except Exception as e:
                    print(f"⚠ Cookie登录失败: {e}")

            # Cookie失效，需要重新登录
            print("🔄 执行重新登录...")
            await self.page.goto(f"{settings.surf_base_url}/login")
            await self.page.wait_for_timeout(2000)

            password = self.account_pool.get_password(account)

            # 改进的登录表单填写逻辑
            login_success = await self._perform_login(account.email, password)

            if login_success:
                # 保存cookie
                cookies = await context.cookies()
                self.account_pool.update_cookie(account.id, json.dumps(cookies))
                self.current_account = account
                print("✓ 重新登录成功")
                return True

            print("✗ 登录失败")
            return False

        except Exception as e:
            print(f"Login failed: {e}")
            return False

    async def _perform_login(self, email: str, password: str) -> bool:
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
                except:
                    continue

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
                return True

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

            # 默认认为已登录（如果没有明确的登录按钮且URL正常）
            print("✓ 未检测到登录按钮，假设已登录")
            return True

        except Exception as e:
            print(f"Login check failed: {e}")
            return False
    
    def _build_research_query(self, project: Project) -> str:
        """
        根据数据库中的项目信息构建研究查询
        将项目的详细信息作为上下文传给 Surf
        """
        parts = [f"请为加密项目 **{project.name}** 生成一份详细的投研报告。"]
        parts.append("\n\n### 以下是该项目的已知信息：\n")
        
        if project.one_liner:
            parts.append(f"- **简介**: {project.one_liner}")
        if project.description:
            parts.append(f"- **描述**: {project.description[:500]}")
        if project.token_symbol:
            parts.append(f"- **代币**: {project.token_symbol}")
        if project.establishment_date:
            parts.append(f"- **成立时间**: {project.establishment_date}")
        if project.total_funding:
            parts.append(f"- **融资总额**: ${project.total_funding:,.0f}")
        if project.tags and isinstance(project.tags, list):
            parts.append(f"- **赛道**: {', '.join(project.tags)}")
        if project.investors and isinstance(project.investors, list):
            names = [inv.get('name', '') for inv in project.investors[:10] if inv.get('name')]
            if names:
                parts.append(f"- **投资方**: {', '.join(names)}")
        if project.ecosystem and isinstance(project.ecosystem, list):
            parts.append(f"- **生态**: {', '.join(project.ecosystem)}")
        if project.market_cap:
            parts.append(f"- **流通市值**: {project.market_cap}")
        if project.price:
            parts.append(f"- **价格**: {project.price}")
        if project.heat_rank:
            parts.append(f"- **X热度排名**: #{project.heat_rank}")
        
        parts.append("\n\n### 请分析以下内容：")
        parts.append("1. 项目概述与核心价值")
        parts.append("2. 技术架构与创新点")
        parts.append("3. 团队与融资背景")
        parts.append("4. 代币经济模型")
        parts.append("5. 竞争格局分析")
        parts.append("6. 风险评估")
        parts.append("7. 投资建议与评级")
        
        return "\n".join(parts)

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
            # 根据模式选择不同的页面和等待时间
            if mode == ReportMode.RESEARCH:
                # 深度研究模式
                await self.page.goto(f"{settings.surf_base_url}/research")
                wait_time = 180000  # 3分钟
                max_timeout = 600000  # 最长等待10分钟
            else:
                # 快速问答模式
                await self.page.goto(f"{settings.surf_base_url}/chat")
                wait_time = 30000  # 30秒
                max_timeout = 120000  # 最长等待2分钟

            await self.page.wait_for_timeout(2000)

            # 构建包含项目详细信息的研究查询
            research_query = self._build_research_query(project)

            # 找到输入框并输入查询（改进的选择器逻辑）
            input_element = await self._find_input_element()
            if not input_element:
                print("✗ 未找到输入框")
                return None

            await input_element.click()
            await self.page.wait_for_timeout(500)
            await input_element.fill(research_query)
            print("✓ 内容已输入")

            # 点击发送或按回车
            await self.page.keyboard.press('Enter')
            print("✓ 已发送请求")

            # 等待报告生成
            print(f"⏳ 等待报告生成 ({wait_time/1000}秒)...")
            await self.page.wait_for_timeout(wait_time)

            # 等待生成完成的标志（改进的检测逻辑）
            content_found = await self._wait_for_content(max_timeout)
            if not content_found:
                print("⚠ 未检测到内容生成，尝试继续生成PDF")

            # 额外等待确保内容完全加载
            await self.page.wait_for_timeout(5000)

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

    async def _find_input_element(self):
        """查找输入框元素"""
        input_selectors = [
            'textarea',
            'input[type="text"]',
            '[contenteditable="true"]',
            '[role="textbox"]',
            '.input-field',
            '.chat-input',
            '.message-input'
        ]

        for selector in input_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    # 检查元素是否可见和可编辑
                    is_visible = await element.is_visible()
                    if is_visible:
                        print(f"✓ 找到输入框: {selector}")
                        return element
            except:
                continue

        return None

    async def _wait_for_content(self, max_timeout: int) -> bool:
        """等待内容生成"""
        content_selectors = [
            '.message-content',
            '.chat-content',
            '.response',
            '.research-content',
            '.report-content',
            'article',
            '.generated-content',
            '[class*="message"]',
            '[class*="content"]'
        ]

        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() * 1000 < max_timeout:
            for selector in content_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        if is_visible:
                            text_content = await element.inner_text()
                            if text_content and len(text_content.strip()) > 10:  # 至少10个字符
                                print(f"✓ 检测到内容生成: {selector}")
                                return True
                except:
                    continue

            await self.page.wait_for_timeout(1000)  # 每秒检查一次

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

            # 登录
            print("🔐 执行登录...")
            if not await self._login(account):
                print("⚠️ 首次登录失败，尝试切换账号...")
                # 尝试切换账号
                account = self.account_pool.switch_to_next()
                if not account or not await self._login(account):
                    error_msg = "无法登录到Surf"
                    print(f"❌ {error_msg}")
                    raise Exception(error_msg)
                report.surf_account_id = account.id
                print(f"🔄 已切换到账号: {account.email}")

            # 生成报告
            print(f"📊 开始生成{ '深度研究' if mode == ReportMode.RESEARCH else '快速问答' }报告...")
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
