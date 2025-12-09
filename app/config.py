from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/crypto_research"
    
    # RootData API
    rootdata_api_key: str = ""
    rootdata_base_url: str = "https://api.rootdata.com/open"
    
    # Feishu
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_bitable_app_token: str = ""
    feishu_bitable_table_id: str = ""
    feishu_base_url: str = "https://open.feishu.cn/open-apis"
    
    # Surf
    surf_base_url: str = "https://asksurf.ai"
    surf_weekly_free_quota: int = 2
    
    # Proxy (用于访问需要VPN的网站)
    proxy_server: str = "http://127.0.0.1:7897"
    
    # App
    secret_key: str = "change_this_secret_key"
    debug: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
