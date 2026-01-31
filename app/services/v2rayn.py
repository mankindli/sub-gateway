"""
Sub Gateway - v2rayN 格式渲染服务
"""
import base64
import urllib.parse
from typing import Optional

from app.models import Customer, Node
from app.utils.logging import logger


def add_remark_to_share_link(share: str, remark: str) -> str:
    """
    为分享链接添加或替换备注
    
    支持的格式：
    - ss://base64#remark
    - socks5://user:pass@host:port#remark
    - socks://host:port#remark
    """
    # 移除已有的备注
    if '#' in share:
        share = share.split('#')[0]
    
    # 添加新备注（URL 编码）
    encoded_remark = urllib.parse.quote(remark, safe='')
    return f"{share}#{encoded_remark}"


def render_v2rayn_subscription(customer: Customer) -> str:
    """
    渲染 v2rayN 订阅内容
    
    Args:
        customer: 客户对象
    
    Returns:
        Base64 编码的订阅内容（无换行）
    """
    lines = []
    
    # 主用节点
    primary_node = customer.get_effective_primary()
    primary_share = add_remark_to_share_link(
        primary_node.share,
        f"{customer.name}-主用-加速"
    )
    lines.append(primary_share)
    
    # 备用节点
    backup_node = customer.get_effective_backup()
    backup_share = add_remark_to_share_link(
        backup_node.share,
        f"{customer.name}-备用-直连"
    )
    lines.append(backup_share)
    
    # 合并并 Base64 编码
    content = '\n'.join(lines)
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    # 不换行
    return encoded
