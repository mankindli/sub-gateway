"""
Sub Gateway - 配置管理模块
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    # Admin 认证
    admin_username: str = "admin"
    admin_password: str = "changeme"
    
    # 服务配置
    base_url: str = "http://localhost:8000"
    host: str = "0.0.0.0"
    port: int = 8000
    
    # 数据存储
    config_dir: Path = Path("config")
    customers_file: str = "customers.yml"
    
    # 日志
    log_level: str = "INFO"
    log_dir: Path = Path("logs")
    
    class Config:
        env_prefix = ""
        env_file = ".env"
        extra = "ignore"
    
    @property
    def customers_path(self) -> Path:
        return self.config_dir / self.customers_file


# 全局配置实例
settings = Settings()

# 确保目录存在
settings.config_dir.mkdir(parents=True, exist_ok=True)
settings.log_dir.mkdir(parents=True, exist_ok=True)
