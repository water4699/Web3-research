"""
邮箱登录策略 - 根据不同邮箱类型使用不同的登录方式
"""
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass


class EmailType(str, Enum):
    """邮箱类型枚举"""
    GMAIL = "gmail"
    QQ = "qq"
    OUTLOOK = "outlook"
    NETEASE_163 = "netease_163"
    RAMBLER = "rambler"
    MAIL_RU = "mail_ru"
    YANDEX = "yandex"
    OTHER = "other"


@dataclass
class EmailLoginConfig:
    """邮箱登录配置"""
    email_type: EmailType
    imap_server: str
    imap_port: int
    use_app_password: bool  # 是否需要应用密码
    ssl_verify: bool  # 是否验证SSL证书
    connection_timeout: int  # 连接超时（秒）
    special_notes: str  # 特殊说明


class EmailLoginStrategy:
    """邮箱登录策略管理器"""
    
    # 邮箱类型配置映射
    EMAIL_CONFIGS: Dict[EmailType, EmailLoginConfig] = {
        EmailType.GMAIL: EmailLoginConfig(
            email_type=EmailType.GMAIL,
            imap_server="imap.gmail.com",
            imap_port=993,
            use_app_password=True,  # Gmail需要应用密码（如果开启了两步验证）
            ssl_verify=True,
            connection_timeout=30,
            special_notes="如果开启了两步验证，需要使用应用密码"
        ),
        EmailType.QQ: EmailLoginConfig(
            email_type=EmailType.QQ,
            imap_server="imap.qq.com",
            imap_port=993,
            use_app_password=True,  # QQ邮箱需要授权码
            ssl_verify=True,
            connection_timeout=30,
            special_notes="需要使用授权码，不是登录密码"
        ),
        EmailType.OUTLOOK: EmailLoginConfig(
            email_type=EmailType.OUTLOOK,
            imap_server="outlook.office365.com",
            imap_port=993,
            use_app_password=True,  # Outlook需要应用密码
            ssl_verify=True,
            connection_timeout=30,
            special_notes="如果开启了两步验证，需要使用应用密码"
        ),
        EmailType.NETEASE_163: EmailLoginConfig(
            email_type=EmailType.NETEASE_163,
            imap_server="imap.163.com",
            imap_port=993,
            use_app_password=True,  # 网易邮箱需要授权码
            ssl_verify=True,
            connection_timeout=30,
            special_notes="需要使用授权码，需要在邮箱设置中开启IMAP并生成授权码"
        ),
        EmailType.RAMBLER: EmailLoginConfig(
            email_type=EmailType.RAMBLER,
            imap_server="imap.rambler.ru",
            imap_port=993,
            use_app_password=False,  # 俄罗斯邮箱通常不需要应用密码
            ssl_verify=True,
            connection_timeout=30,
            special_notes="俄罗斯邮箱，通常直接使用登录密码"
        ),
        EmailType.MAIL_RU: EmailLoginConfig(
            email_type=EmailType.MAIL_RU,
            imap_server="imap.mail.ru",
            imap_port=993,
            use_app_password=False,
            ssl_verify=True,
            connection_timeout=30,
            special_notes="俄罗斯邮箱，通常直接使用登录密码"
        ),
        EmailType.YANDEX: EmailLoginConfig(
            email_type=EmailType.YANDEX,
            imap_server="imap.yandex.ru",
            imap_port=993,
            use_app_password=False,
            ssl_verify=True,
            connection_timeout=30,
            special_notes="俄罗斯邮箱，通常直接使用登录密码"
        ),
    }
    
    @staticmethod
    def detect_email_type(email: str) -> EmailType:
        """根据邮箱地址检测邮箱类型"""
        if not email or '@' not in email:
            return EmailType.OTHER
        
        email_domain = email.split('@')[1].lower()
        
        # Gmail
        if 'gmail.com' in email_domain:
            return EmailType.GMAIL
        
        # QQ邮箱
        if 'qq.com' in email_domain:
            return EmailType.QQ
        
        # Outlook/Hotmail
        if 'outlook.com' in email_domain or 'hotmail.com' in email_domain or 'live.com' in email_domain:
            return EmailType.OUTLOOK
        
        # 网易邮箱
        if '163.com' in email_domain or '126.com' in email_domain or 'yeah.net' in email_domain:
            return EmailType.NETEASE_163
        
        # Rambler
        if 'rambler.ru' in email_domain or 'autorambler.ru' in email_domain:
            return EmailType.RAMBLER
        
        # Mail.ru
        if 'mail.ru' in email_domain or 'inbox.ru' in email_domain or 'list.ru' in email_domain:
            return EmailType.MAIL_RU
        
        # Yandex
        if 'yandex.ru' in email_domain or 'yandex.com' in email_domain:
            return EmailType.YANDEX
        
        return EmailType.OTHER
    
    @staticmethod
    def get_login_config(email: str) -> EmailLoginConfig:
        """获取邮箱的登录配置"""
        email_type = EmailLoginStrategy.detect_email_type(email)
        
        if email_type in EmailLoginStrategy.EMAIL_CONFIGS:
            return EmailLoginStrategy.EMAIL_CONFIGS[email_type]
        
        # 默认配置（其他邮箱）
        return EmailLoginConfig(
            email_type=EmailType.OTHER,
            imap_server="imap.gmail.com",  # 默认值，实际应该从数据库读取
            imap_port=993,
            use_app_password=False,
            ssl_verify=True,
            connection_timeout=30,
            special_notes="未知邮箱类型，使用默认配置"
        )
    
    @staticmethod
    def get_imap_server(email: str, default_server: Optional[str] = None) -> str:
        """获取IMAP服务器地址"""
        config = EmailLoginStrategy.get_login_config(email)
        
        # 如果配置中有服务器地址，使用配置的
        if config.email_type != EmailType.OTHER:
            return config.imap_server
        
        # 否则使用传入的默认值
        return default_server or "imap.gmail.com"
    
    @staticmethod
    def get_imap_port(email: str, default_port: Optional[int] = None) -> int:
        """获取IMAP端口"""
        config = EmailLoginStrategy.get_login_config(email)
        return config.imap_port or default_port or 993
    
    @staticmethod
    def needs_app_password(email: str) -> bool:
        """判断是否需要应用密码"""
        config = EmailLoginStrategy.get_login_config(email)
        return config.use_app_password
    
    @staticmethod
    def get_connection_timeout(email: str) -> int:
        """获取连接超时时间"""
        config = EmailLoginStrategy.get_login_config(email)
        return config.connection_timeout
    
    @staticmethod
    def get_special_notes(email: str) -> str:
        """获取特殊说明"""
        config = EmailLoginStrategy.get_login_config(email)
        return config.special_notes

