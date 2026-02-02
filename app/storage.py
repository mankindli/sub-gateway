"""
Sub Gateway - YAML 存储层
使用文件锁实现并发保护，原子写入保证数据安全
"""
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
from filelock import FileLock

import yaml

from app.config import settings
from app.models import Customer, CustomersConfig, Nodes, Override
from app.utils.logging import logger


class CustomerStorage:
    """客户数据存储管理"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or settings.customers_path
        self.lock_path = self.config_path.with_suffix('.lock')
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """确保配置文件存在"""
        if not self.config_path.exists():
            self._save_config(CustomersConfig())
    
    def _load_config(self) -> CustomersConfig:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            return CustomersConfig(**data)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return CustomersConfig()
    
    def _save_config(self, config: CustomersConfig):
        """原子写入配置文件"""
        # 先写入临时文件
        fd, temp_path = tempfile.mkstemp(
            suffix='.yml',
            dir=self.config_path.parent
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                yaml.dump(
                    config.model_dump(mode='json'),
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False
                )
            # 原子替换
            shutil.move(temp_path, self.config_path)
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
    
    def get_all_customers(self) -> list[Customer]:
        """获取所有客户"""
        with FileLock(self.lock_path):
            config = self._load_config()
            return config.customers
    
    def get_customer_by_token(self, token: str) -> Optional[Customer]:
        """通过 token 获取客户"""
        with FileLock(self.lock_path):
            config = self._load_config()
            for customer in config.customers:
                if customer.token == token:
                    return customer
            return None
    
    def create_customer(self, customer: Customer) -> Customer:
        """创建新客户"""
        with FileLock(self.lock_path):
            config = self._load_config()
            
            # 检查 token 是否已存在
            for existing in config.customers:
                if existing.token == customer.token:
                    raise ValueError(f"Token already exists: {customer.token}")
            
            config.customers.append(customer)
            self._save_config(config)
            logger.info(f"Created customer: {customer.name} ({customer.token[:8]}...)")
            return customer
    
    def update_customer(
        self,
        token: str,
        name: Optional[str] = None,
        enabled: Optional[bool] = None,
        nodes: Optional[Nodes] = None,
        ip_source: Optional[str] = None,
        expires_at = None,
        remark: Optional[str] = None,
        primary_name: Optional[str] = None,
        backup_name: Optional[str] = None
    ) -> Optional[Customer]:
        """更新客户信息"""
        with FileLock(self.lock_path):
            config = self._load_config()
            
            for i, customer in enumerate(config.customers):
                if customer.token == token:
                    if name is not None:
                        customer.name = name
                    if enabled is not None:
                        customer.enabled = enabled
                    if nodes is not None:
                        customer.nodes = nodes
                    if ip_source is not None:
                        customer.ip_source = ip_source
                    if expires_at is not None:
                        customer.expires_at = expires_at
                    if remark is not None:
                        customer.remark = remark
                    if primary_name is not None:
                        customer.primary_name = primary_name
                    if backup_name is not None:
                        customer.backup_name = backup_name
                    customer.updated_at = datetime.utcnow()
                    config.customers[i] = customer
                    self._save_config(config)
                    logger.info(f"Updated customer: {customer.name}")
                    return customer
            
            return None
    
    def rotate_token(self, old_token: str, new_token: str) -> Optional[Customer]:
        """轮换客户 token"""
        with FileLock(self.lock_path):
            config = self._load_config()
            
            # 检查新 token 是否已存在
            for customer in config.customers:
                if customer.token == new_token:
                    raise ValueError("New token already exists")
            
            for i, customer in enumerate(config.customers):
                if customer.token == old_token:
                    customer.token = new_token
                    customer.updated_at = datetime.utcnow()
                    config.customers[i] = customer
                    self._save_config(config)
                    logger.info(
                        f"Rotated token for customer: {customer.name} "
                        f"({old_token[:8]}... -> {new_token[:8]}...)"
                    )
                    return customer
            
            return None
    
    def set_override(
        self,
        token: str,
        override: Override
    ) -> Optional[Customer]:
        """设置应急覆盖"""
        with FileLock(self.lock_path):
            config = self._load_config()
            
            for i, customer in enumerate(config.customers):
                if customer.token == token:
                    customer.override = override
                    customer.updated_at = datetime.utcnow()
                    config.customers[i] = customer
                    self._save_config(config)
                    logger.info(f"Set override for customer: {customer.name}")
                    return customer
            
            return None
    
    def clear_override(self, token: str) -> Optional[Customer]:
        """清除应急覆盖"""
        with FileLock(self.lock_path):
            config = self._load_config()
            
            for i, customer in enumerate(config.customers):
                if customer.token == token:
                    customer.override = None
                    customer.updated_at = datetime.utcnow()
                    config.customers[i] = customer
                    self._save_config(config)
                    logger.info(f"Cleared override for customer: {customer.name}")
                    return customer
            
            return None
    
    def delete_customer(self, token: str) -> bool:
        """删除客户"""
        with FileLock(self.lock_path):
            config = self._load_config()
            
            for i, customer in enumerate(config.customers):
                if customer.token == token:
                    del config.customers[i]
                    self._save_config(config)
                    logger.info(f"Deleted customer: {customer.name}")
                    return True
            
            return False


# 全局存储实例
storage = CustomerStorage()
