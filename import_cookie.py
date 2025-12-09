"""
手动导入 Cookie
在普通浏览器登录 Surf 后，从开发者工具复制 cookie 信息
"""
import json
from pathlib import Path

COOKIE_FILE = Path("data/surf_cookies.json")
COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)

print("=" * 50)
print("Surf Cookie 导入工具")
print("=" * 50)

print("""
请按以下步骤操作：

1. 在普通 Chrome 浏览器中访问 https://asksurf.ai 并登录

2. 登录成功后，按 F12 打开开发者工具

3. 点击 "Application"（应用程序）标签
   - 如果看不到，点击 >> 展开更多标签

4. 左侧栏找到 Storage → Cookies → https://asksurf.ai

5. 在右侧 Cookie 列表中，找到以下重要的 Cookie 名称并记录它们的值：
   - __Secure-next-auth.session-token（最重要）
   - 或者其他 session/auth 相关的 cookie

""")

print("请输入 Cookie 信息（每行一个，格式：名称=值）")
print("输入完成后，输入空行结束：")
print("-" * 50)

cookies = []
while True:
    line = input()
    if not line.strip():
        break
    
    if '=' in line:
        parts = line.split('=', 1)
        name = parts[0].strip()
        value = parts[1].strip()
        cookies.append({
            "name": name,
            "value": value,
            "domain": ".asksurf.ai",
            "path": "/"
        })
        print(f"  ✓ 已添加: {name}")

if cookies:
    with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 已保存 {len(cookies)} 个 Cookie 到: {COOKIE_FILE}")
else:
    print("\n✗ 没有输入任何 Cookie")
