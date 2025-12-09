"""
手动登录 Surf 并保存 Cookie
运行后会打开浏览器，请手动完成登录，登录成功后按回车保存 cookie
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

SURF_BASE_URL = "https://asksurf.ai"
COOKIE_FILE = Path("data/surf_cookies.json")
COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)

async def save_cookies():
    print("=" * 50)
    print("Surf Cookie 保存工具")
    print("=" * 50)
    
    playwright = await async_playwright().start()
    
    # 使用系统安装的 Chrome 浏览器（而不是 Playwright 自带的 Chromium）
    print("\n启动 Chrome 浏览器...")
    browser = await playwright.chromium.launch(
        headless=False,
        channel="chrome",  # 使用系统 Chrome
        proxy={"server": "http://127.0.0.1:7897"}
    )
    context = await browser.new_context()
    page = await context.new_page()
    
    # 增加超时时间
    page.set_default_timeout(120000)
    
    try:
        print(f"\n1. 正在打开 {SURF_BASE_URL}（最长等待2分钟）...")
        await page.goto(SURF_BASE_URL, timeout=120000)
        await page.wait_for_timeout(2000)
        
        print("\n" + "=" * 50)
        print("请在浏览器中手动完成登录！")
        print("登录成功后，回到这里按回车键保存 Cookie")
        print("=" * 50)
        
        input("\n按回车键继续...")
        
        # 保存 cookies
        cookies = await context.cookies()
        
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Cookie 已保存到: {COOKIE_FILE}")
        print(f"  共保存 {len(cookies)} 个 cookie")
        
        # 验证登录状态
        print("\n验证登录状态...")
        await page.goto(SURF_BASE_URL)
        await page.wait_for_timeout(3000)
        
        # 检查是否有用户头像或其他登录标志
        print(f"当前 URL: {page.url}")
        print("\n请确认浏览器中显示已登录状态")
        
    except Exception as e:
        print(f"错误: {e}")
    
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(save_cookies())
