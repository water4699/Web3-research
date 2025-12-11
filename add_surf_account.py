"""
添加Surf账号到数据库
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.services.surf_account_pool import SurfAccountPool
from app.services.email_login_strategy import EmailLoginStrategy

def add_account(email: str, password: str, email_server: str = None, email_port: int = 993):
    """添加账号到数据库"""
    db = SessionLocal()
    try:
        pool = SurfAccountPool(db)
        
        # 如果没有指定IMAP服务器，使用邮箱登录策略自动检测
        if not email_server:
            email_server = EmailLoginStrategy.get_imap_server(email)
            email_port = EmailLoginStrategy.get_imap_port(email)
        
        # 获取邮箱类型和配置信息
        email_type = EmailLoginStrategy.detect_email_type(email)
        login_config = EmailLoginStrategy.get_login_config(email)
        
        print("=" * 60)
        print("📧 添加Surf账号到数据库")
        print("=" * 60)
        print(f"邮箱: {email}")
        print(f"邮箱类型: {email_type.value}")
        print(f"IMAP服务器: {email_server}:{email_port}")
        if login_config.special_notes:
            print(f"提示: {login_config.special_notes}")
        print()
        
        # 添加账号
        account = pool.add_account(
            email=email,
            email_password=password,
            email_server=email_server,
            email_port=email_port
        )
        
        print(f"✅ 账号添加成功！")
        print(f"   ID: {account.id}")
        print(f"   邮箱: {account.email}")
        print(f"   IMAP服务器: {account.email_server}:{account.email_port}")
        print(f"   状态: {account.status}")
        print(f"   每周配额: {account.weekly_quota_limit}")
        
        return account
        
    except Exception as e:
        print(f"❌ 添加账号失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    # 添加俄罗斯邮箱账号
    email = "plrkrggu@autorambler.ru"
    password = "cV5YRA2tWF"
    
    account = add_account(email, password)
    
    if account:
        print("\n🎉 账号添加完成！")
        sys.exit(0)
    else:
        print("\n❌ 账号添加失败！")
        sys.exit(1)

