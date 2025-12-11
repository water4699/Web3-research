"""
更新Surf账号的邮箱密码（应用密码）
用于Outlook等需要应用密码的邮箱
"""
import sys
from app.database import SessionLocal
from app.services.surf_account_pool import SurfAccountPool
from app.models import SurfAccount

def update_password(account_id: int, new_password: str):
    """更新指定账号的邮箱密码"""
    db = SessionLocal()
    try:
        pool = SurfAccountPool(db)
        account = db.query(SurfAccount).filter(SurfAccount.id == account_id).first()
        
        if not account:
            print(f"❌ 账号ID {account_id} 不存在")
            return False
        
        # 加密新密码
        encrypted_password = pool.cipher.encrypt(new_password.encode()).decode()
        account.email_password_encrypted = encrypted_password
        db.commit()
        
        print(f"✅ 账号 {account.email} 的密码已更新")
        return True
    finally:
        db.close()

def list_accounts():
    """列出所有账号"""
    db = SessionLocal()
    try:
        accounts = db.query(SurfAccount).all()
        print("\n📋 所有Surf账号:")
        print("-" * 60)
        for acc in accounts:
            print(f"  ID: {acc.id} | 邮箱: {acc.email} | 状态: {acc.status}")
        print("-" * 60)
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  列出账号: python update_email_password.py list")
        print("  更新密码: python update_email_password.py <账号ID> <新密码>")
        print("\n示例:")
        print("  python update_email_password.py list")
        print("  python update_email_password.py 6 your_app_password_here")
        sys.exit(1)
    
    if sys.argv[1] == "list":
        list_accounts()
    elif len(sys.argv) >= 3:
        account_id = int(sys.argv[1])
        new_password = sys.argv[2]
        update_password(account_id, new_password)
    else:
        print("❌ 参数不足，请提供账号ID和新密码")
