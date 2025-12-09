"""
Surf 账号池管理
每个账号每周免费2次
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
from app.models import SurfAccount
from app.config import get_settings

settings = get_settings()


class SurfAccountPool:
    def __init__(self, db: Session):
        self.db = db
        self._cipher = None
    
    @property
    def cipher(self) -> Fernet:
        """获取加密器"""
        if not self._cipher:
            key = settings.secret_key.encode()[:32].ljust(32, b'0')
            import base64
            self._cipher = Fernet(base64.urlsafe_b64encode(key))
        return self._cipher
    
    def _get_week_start(self) -> datetime:
        """获取本周一的日期"""
        today = datetime.now()
        return today - timedelta(days=today.weekday())
    
    def _reset_weekly_quota_if_needed(self, account: SurfAccount) -> None:
        """如果是新的一周，重置配额"""
        week_start = self._get_week_start()
        
        if account.week_start_date is None or account.week_start_date < week_start:
            account.weekly_quota_used = 0
            account.week_start_date = week_start
            if account.status == 'exhausted':
                account.status = 'active'
            self.db.commit()
    
    def get_available_account(self) -> Optional[SurfAccount]:
        """
        获取可用账号（本周额度未用完）
        优先选择使用次数少的账号
        """
        accounts = self.db.query(SurfAccount).filter(
            SurfAccount.status.in_(['active', 'exhausted'])
        ).all()
        
        for account in accounts:
            self._reset_weekly_quota_if_needed(account)
        
        # 获取可用账号，优先选择使用次数少的账号
        available_accounts = self.db.query(SurfAccount).filter(
            SurfAccount.status == 'active',
            SurfAccount.weekly_quota_used < SurfAccount.weekly_quota_limit
        ).order_by(
            SurfAccount.weekly_quota_used.asc(),
            SurfAccount.id.asc()  # 简单按ID排序，避免NULL值问题
        ).all()

        # 从可用账号中选择last_used_at最早的（包括NULL值）
        if available_accounts:
            # 如果有从未使用过的账号（last_used_at为NULL），优先选择
            never_used = [acc for acc in available_accounts if acc.last_used_at is None]
            if never_used:
                return never_used[0]

            # 否则选择使用时间最早的
            return min(available_accounts, key=lambda acc: acc.last_used_at)

        return None
        
        return available
    
    def use_quota(self, account_id: int) -> bool:
        """
        使用一次配额
        返回是否成功
        """
        account = self.db.query(SurfAccount).filter(
            SurfAccount.id == account_id
        ).first()
        
        if not account:
            return False
        
        self._reset_weekly_quota_if_needed(account)
        
        if account.weekly_quota_used >= account.weekly_quota_limit:
            return False
        
        account.weekly_quota_used += 1
        account.last_used_at = datetime.now()
        
        if account.weekly_quota_used >= account.weekly_quota_limit:
            account.status = 'exhausted'
        
        self.db.commit()
        return True
    
    def switch_to_next(self) -> Optional[SurfAccount]:
        """切换到下一个可用账号"""
        return self.get_available_account()
    
    def add_account(self, email: str, password: str) -> SurfAccount:
        """添加新账号"""
        encrypted_password = self.cipher.encrypt(password.encode()).decode()
        
        account = SurfAccount(
            email=email,
            password_encrypted=encrypted_password,
            weekly_quota_limit=settings.surf_weekly_free_quota,
            week_start_date=self._get_week_start()
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account
    
    def get_password(self, account: SurfAccount) -> str:
        """解密获取密码"""
        return self.cipher.decrypt(account.password_encrypted.encode()).decode()
    
    def update_cookie(self, account_id: int, cookie_data: str) -> None:
        """更新账号的cookie"""
        account = self.db.query(SurfAccount).filter(
            SurfAccount.id == account_id
        ).first()
        if account:
            account.cookie_data = cookie_data
            self.db.commit()
    
    def disable_account(self, account_id: int) -> None:
        """禁用账号"""
        account = self.db.query(SurfAccount).filter(
            SurfAccount.id == account_id
        ).first()
        if account:
            account.status = 'disabled'
            self.db.commit()
    
    def get_all_accounts_status(self) -> list:
        """获取所有账号状态"""
        accounts = self.db.query(SurfAccount).all()
        result = []
        
        for account in accounts:
            self._reset_weekly_quota_if_needed(account)
            result.append({
                "id": account.id,
                "email": account.email,
                "status": account.status,
                "weekly_quota_used": account.weekly_quota_used,
                "weekly_quota_limit": account.weekly_quota_limit,
                "remaining": account.weekly_quota_limit - account.weekly_quota_used,
                "last_used_at": account.last_used_at.isoformat() if account.last_used_at else None
            })
        
        return result
    
    def get_total_remaining_quota(self) -> int:
        """获取所有账号剩余总配额"""
        accounts = self.db.query(SurfAccount).filter(
            SurfAccount.status != 'disabled'
        ).all()
        
        total = 0
        for account in accounts:
            self._reset_weekly_quota_if_needed(account)
            total += account.weekly_quota_limit - account.weekly_quota_used
        
        return total
