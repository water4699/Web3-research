"""
Surf AI 自动登录配置文件
"""

from surf_auto_login import SurfAccount

# 实际账号配置
SURF_ACCOUNTS = [
    # 俄罗斯邮箱 Mail.ru（不需要授权码，直接使用登录密码）
    SurfAccount(
        email="your-email@mail.ru",  # 请替换为你的俄罗斯邮箱地址
        email_password="your-login-password",  # 请替换为你的登录密码（不需要授权码）
        email_server="imap.mail.ru",
        email_port=993
    ),
    
    # QQ邮箱账号（备用）
    SurfAccount(
        email="1043223937@qq.com",
        email_password="juqmlhoqlrpsbdgd",  # QQ邮箱授权码
        email_server="imap.qq.com",
        email_port=993
    ),
]

# 选择要使用的账号索引（0, 1, 2...）
DEFAULT_ACCOUNT_INDEX = 0

# 调试模式（显示更多日志）
DEBUG_MODE = True

# 验证码等待配置
VERIFICATION_CODE_MAX_ATTEMPTS = 10  # 最大尝试次数
VERIFICATION_CODE_WAIT_SECONDS = 5   # 每次等待秒数

# 浏览器配置
HEADLESS_MODE = False  # 是否无头模式（False=显示浏览器窗口）
BROWSER_TIMEOUT = 30000  # 浏览器操作超时时间（毫秒）

def get_default_account() -> SurfAccount:
    """获取默认账号"""
    if 0 <= DEFAULT_ACCOUNT_INDEX < len(SURF_ACCOUNTS):
        return SURF_ACCOUNTS[DEFAULT_ACCOUNT_INDEX]
    else:
        raise ValueError(f"无效的账号索引: {DEFAULT_ACCOUNT_INDEX}")

# 使用示例：
"""
from surf_config import get_default_account
from surf_auto_login import SurfAutoLogin

async def test_login():
    account = get_default_account()
    async with SurfAutoLogin(account) as login_tool:
        success = await login_tool.auto_login()
        print(f"登录结果: {'成功' if success else '失败'}")
"""
