"""
Sub Gateway - 数据模型
"""
from datetime import datetime
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class ClashProxy(BaseModel):
    """Clash 代理节点结构"""
    type: Literal["ss", "socks5", "vmess", "vless", "trojan", "http"]
    server: str
    port: int
    name: Optional[str] = None
    
    # SS 专用字段
    cipher: Optional[str] = None
    password: Optional[str] = None
    
    # SOCKS5 专用字段
    username: Optional[str] = None
    
    # 通用可选字段
    udp: Optional[bool] = None
    
    def to_clash_dict(self, node_name: str) -> Dict[str, Any]:
        """转换为 Clash proxies 格式"""
        result: Dict[str, Any] = {
            "name": node_name,
            "type": self.type,
            "server": self.server,
            "port": self.port,
        }
        
        if self.type == "ss":
            if self.cipher:
                result["cipher"] = self.cipher
            if self.password:
                result["password"] = self.password
        elif self.type == "socks5":
            if self.username:
                result["username"] = self.username
            if self.password:
                result["password"] = self.password
        
        if self.udp is not None:
            result["udp"] = self.udp
        
        return result


class Node(BaseModel):
    """节点配置"""
    share: str  # 分享链接（用于 v2rayN）
    clash: Optional[ClashProxy] = None  # Clash 结构化配置


class Override(BaseModel):
    """应急覆盖配置"""
    primary: Optional[Node] = None
    backup: Optional[Node] = None
    note: Optional[str] = None


class Nodes(BaseModel):
    """节点组"""
    primary: Node
    backup: Node


class Customer(BaseModel):
    """客户配置"""
    token: str = Field(..., min_length=32)
    name: str
    enabled: bool = True
    nodes: Nodes
    override: Optional[Override] = None
    ip_source: Optional[str] = None  # IP来源（如：狗云、搬瓦工、自建等）
    expires_at: Optional[datetime] = None  # 到期时间
    remark: Optional[str] = None  # 备注
    primary_name: Optional[str] = None  # 主用节点名称（默认使用客户名称）
    backup_name: Optional[str] = None  # 备用节点名称（默认使用客户名称）
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def get_effective_primary(self) -> Node:
        """获取生效的主节点（考虑覆盖）"""
        if self.override and self.override.primary:
            return self.override.primary
        return self.nodes.primary
    
    def get_effective_backup(self) -> Node:
        """获取生效的备用节点（考虑覆盖）"""
        if self.override and self.override.backup:
            return self.override.backup
        return self.nodes.backup
    
    def get_primary_display_name(self) -> str:
        """获取主用节点显示名称"""
        return self.primary_name or self.name
    
    def get_backup_display_name(self) -> str:
        """获取备用节点显示名称"""
        return self.backup_name or self.name


class CustomersConfig(BaseModel):
    """客户配置文件结构"""
    customers: list[Customer] = []


# API 请求/响应模型
class CreateCustomerRequest(BaseModel):
    """创建客户请求"""
    name: str
    nodes: Nodes
    enabled: bool = True
    ip_source: Optional[str] = None
    expires_at: Optional[datetime] = None
    remark: Optional[str] = None
    primary_name: Optional[str] = None
    backup_name: Optional[str] = None


class CreateCustomerResponse(BaseModel):
    """创建客户响应"""
    token: str
    name: str
    subscribe_urls: Dict[str, str]


class UpdateCustomerRequest(BaseModel):
    """更新客户请求"""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    nodes: Optional[Nodes] = None
    ip_source: Optional[str] = None
    expires_at: Optional[datetime] = None
    remark: Optional[str] = None
    primary_name: Optional[str] = None
    backup_name: Optional[str] = None


class RotateTokenResponse(BaseModel):
    """Token 轮换响应"""
    old_token: str
    new_token: str
    subscribe_urls: Dict[str, str]


class SetOverrideRequest(BaseModel):
    """设置覆盖请求"""
    primary: Optional[Node] = None
    backup: Optional[Node] = None
    note: Optional[str] = None


class CustomerListItem(BaseModel):
    """客户列表项"""
    token: str
    name: str
    enabled: bool
    has_override: bool
    ip_source: Optional[str] = None
    expires_at: Optional[datetime] = None
    remark: Optional[str] = None
    primary_name: Optional[str] = None
    backup_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    subscribe_urls: Dict[str, str]

