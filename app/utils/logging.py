"""
Sub Gateway - 日志配置
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

from app.config import settings


def setup_logging() -> logging.Logger:
    """配置日志系统"""
    logger = logging.getLogger("sub_gateway")
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（订阅访问日志）
    log_file = settings.log_dir / "subscribe.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# 全局日志实例
logger = setup_logging()


def log_subscribe_access(
    token: str,
    client_ip: str,
    user_agent: str,
    format_type: str,
    status_code: int,
    customer_name: str = None
):
    """
    记录订阅访问日志
    
    Args:
        token: 客户 token（部分隐藏）
        client_ip: 客户端 IP
        user_agent: 用户代理
        format_type: 订阅格式（v2rayn/clash）
        status_code: 响应状态码
        customer_name: 客户名称（可选）
    """
    masked_token = f"{token[:8]}...{token[-4:]}" if len(token) >= 12 else "***"
    logger.info(
        f"SUBSCRIBE | token={masked_token} | name={customer_name or 'N/A'} | "
        f"ip={client_ip} | format={format_type} | status={status_code} | "
        f"ua={user_agent[:100]}"
    )
