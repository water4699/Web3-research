"""
Surf 登录工具 - 手动登录一次，保存状态供后续使用
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

# 保存浏览器状态的目录
STATE_DIR = Path("data/browser_state")
STATE_DIR.mkdir(parents=True, exist_ok=True)

async def login_surf():
    print("=" * 50)
    print("Surf 登录工具")
    print("=" * 50)
    
    playwright = await async_playwright().start()
    
    print("\n启动浏览器（使用代理 127.0.0.1:7897）...")
    
    # 使用独立的用户数据目录，避免与现有 Chrome 冲突
    context = await playwright.chromium.launch_persistent_context(
        str(STATE_DIR),
        headless=False,
        proxy={"server": "http://127.0.0.1:7897"},
        viewport={"width": 1280, "height": 800}
    )
    
    page = context.pages[0] if context.pages else await context.new_page()
    
    print("访问 Surf...")
    await page.goto("https://asksurf.ai")
    
    print("\n" + "=" * 50)
    print("请在浏览器中完成登录！")
    print("可以使用邮箱或其他方式（不要用 Google 登录）")
    print("登录成功后，回到这里按回车保存状态")
    print("=" * 50)
    
    input("\n按回车键保存并退出...")
    
    # 保存状态
    await context.storage_state(path=str(STATE_DIR / "state.json"))
    print(f"\n✓ 登录状态已保存到: {STATE_DIR}")
    
    await context.close()
    await playwright.stop()
    print("完成！现在可以运行 test_surf.py 测试报告生成")

if __name__ == "__main__":
    asyncio.run(login_surf())
