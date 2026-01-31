"""
Sub Gateway - v2rayN 格式渲染服务
支持 ss://, socks5://, vmess://, vless://, trojan:// 等格式
"""
import base64
import json
import urllib.parse
from typing import Optional

from app.models import Customer, Node
from app.utils.logging import logger


def add_remark_to_share_link(share: str, remark: str) -> str:
    """
    为分享链接添加或替换备注
    
    支持的格式：
    - vmess://base64json (备注在 JSON 的 ps 字段)
    - ss://base64#remark
    - socks5://user:pass@host:port#remark
    - vless://uuid@host:port?params#remark
    - trojan://password@host:port?params#remark
    """
    share = share.strip()
    
    # 处理 vmess:// 链接（备注在 base64 编码的 JSON 里）
    if share.lower().startswith('vmess://'):
        try:
            # 提取 base64 部分
            b64_part = share[8:]  # 去掉 'vmess://'
            
            # 解码 JSON
            json_str = base64.b64decode(b64_part).decode('utf-8')
            config = json.loads(json_str)
            
            # 更新备注字段
            config['ps'] = remark
            
            # 重新编码
            new_json = json.dumps(config, ensure_ascii=False)
            new_b64 = base64.b64encode(new_json.encode('utf-8')).decode('utf-8')
            
            return f"vmess://{new_b64}"
        except Exception as e:
            logger.warning(f"Failed to parse vmess link, using original: {e}")
            # 解析失败，尝试用 # 方式添加备注
            if '#' in share:
                share = share.split('#')[0]
            return f"{share}#{urllib.parse.quote(remark, safe='')}"
    
    # 处理其他格式（ss, socks5, vless, trojan 等都用 # 追加备注）
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

