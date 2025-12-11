"""
数据库迁移脚本：更新SurfAccount表结构，支持邮箱验证码登录
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from app.config import get_settings

settings = get_settings()

def migrate():
    """执行数据库迁移"""
    print("=" * 60)
    print("🚀 开始数据库迁移：更新SurfAccount表结构")
    print("=" * 60)
    
    # 创建数据库连接
    database_url = settings.database_url
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # 开始事务
            trans = conn.begin()
            
            try:
                # 1. 检查是否存在 password_encrypted 字段
                print("\n📋 检查表结构...")
                result = conn.execute(text("SHOW COLUMNS FROM surf_accounts LIKE 'password_encrypted'"))
                has_old_field = result.fetchone() is not None
                
                if has_old_field:
                    print("✓ 找到旧字段 password_encrypted，准备重命名...")
                    # 重命名字段
                    conn.execute(text("""
                        ALTER TABLE surf_accounts 
                        CHANGE COLUMN password_encrypted email_password_encrypted TEXT
                    """))
                    print("✓ 字段重命名完成")
                else:
                    print("⚠ password_encrypted 字段不存在，跳过重命名")
                
                # 2. 检查是否存在 email_password_encrypted 字段（如果不存在则添加）
                result = conn.execute(text("SHOW COLUMNS FROM surf_accounts LIKE 'email_password_encrypted'"))
                has_email_password = result.fetchone() is not None
                
                if not has_email_password:
                    print("✓ 添加 email_password_encrypted 字段...")
                    conn.execute(text("""
                        ALTER TABLE surf_accounts 
                        ADD COLUMN email_password_encrypted TEXT AFTER email
                    """))
                    print("✓ email_password_encrypted 字段添加完成")
                else:
                    print("✓ email_password_encrypted 字段已存在")
                
                # 3. 检查并添加 email_server 字段
                result = conn.execute(text("SHOW COLUMNS FROM surf_accounts LIKE 'email_server'"))
                has_email_server = result.fetchone() is not None
                
                if not has_email_server:
                    print("✓ 添加 email_server 字段...")
                    conn.execute(text("""
                        ALTER TABLE surf_accounts 
                        ADD COLUMN email_server VARCHAR(100) DEFAULT 'imap.gmail.com' AFTER email
                    """))
                    print("✓ email_server 字段添加完成")
                else:
                    print("✓ email_server 字段已存在")
                
                # 4. 检查并添加 email_port 字段
                result = conn.execute(text("SHOW COLUMNS FROM surf_accounts LIKE 'email_port'"))
                has_email_port = result.fetchone() is not None
                
                if not has_email_port:
                    print("✓ 添加 email_port 字段...")
                    conn.execute(text("""
                        ALTER TABLE surf_accounts 
                        ADD COLUMN email_port INT DEFAULT 993 AFTER email_server
                    """))
                    print("✓ email_port 字段添加完成")
                else:
                    print("✓ email_port 字段已存在")
                
                # 5. 更新现有数据的默认值（如果email_server或email_port为NULL）
                print("\n📝 更新现有数据...")
                result = conn.execute(text("""
                    UPDATE surf_accounts 
                    SET email_server = 'imap.gmail.com', email_port = 993 
                    WHERE email_server IS NULL OR email_port IS NULL
                """))
                updated_rows = result.rowcount
                print(f"✓ 更新了 {updated_rows} 条记录")
                
                # 提交事务
                trans.commit()
                print("\n✅ 数据库迁移成功完成！")
                
                # 显示更新后的表结构
                print("\n📊 更新后的表结构：")
                result = conn.execute(text("DESCRIBE surf_accounts"))
                columns = result.fetchall()
                for col in columns:
                    print(f"  - {col[0]}: {col[1]}")
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ 迁移失败: {e}")
                raise
                
    except Exception as e:
        print(f"\n❌ 数据库连接失败: {e}")
        print("请检查数据库配置和连接")
        return False
    
    return True

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)

