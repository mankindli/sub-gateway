"""
Sub Gateway - Clash 格式渲染服务
支持自动解析 vmess://, vless://, trojan://, ss://, socks5:// 链接
"""
import base64
import json
import urllib.parse
from typing import Dict, Any, List, Optional

import yaml

from app.models import Customer, Node
from app.utils.logging import logger


def parse_vmess_to_clash(share: str) -> Optional[Dict[str, Any]]:
    """解析 vmess:// 链接为 Clash 代理配置"""
    try:
        b64_part = share[8:]  # 去掉 'vmess://'
        json_str = base64.b64decode(b64_part).decode('utf-8')
        config = json.loads(json_str)
        
        # name 会在 get_clash_proxy 中设置，这里用占位符
        proxy: Dict[str, Any] = {
            "name": "",  # 占位符，稍后填充
            "type": "vmess",
            "server": config.get("add", ""),
            "port": int(config.get("port", 443)),
            "uuid": config.get("id", ""),
            "alterId": int(config.get("aid", 0)),
            "cipher": config.get("scy", "auto"),
            "udp": True,
        }
        
        # 网络类型
        net = config.get("net", "tcp")
        if net == "ws":
            proxy["network"] = "ws"
            ws_opts: Dict[str, Any] = {}
            if config.get("path"):
                ws_opts["path"] = config["path"]
            if config.get("host"):
                ws_opts["headers"] = {"Host": config["host"]}
            if ws_opts:
                proxy["ws-opts"] = ws_opts
        elif net == "grpc":
            proxy["network"] = "grpc"
            if config.get("path"):
                proxy["grpc-opts"] = {"grpc-service-name": config["path"]}
        elif net != "tcp":
            proxy["network"] = net
        
        # TLS
        if config.get("tls") == "tls":
            proxy["tls"] = True
            if config.get("sni"):
                proxy["servername"] = config["sni"]
            if config.get("alpn"):
                proxy["alpn"] = config["alpn"].split(",")
        
        return proxy
    except Exception as e:
        logger.warning(f"Failed to parse vmess link: {e}")
        return None


def parse_ss_to_clash(share: str) -> Optional[Dict[str, Any]]:
    """解析 ss:// 链接为 Clash 代理配置"""
    try:
        # 去掉 'ss://' 和备注
        content = share[5:]
        if '#' in content:
            content = content.split('#')[0]
        
        # 格式: base64(method:password)@server:port
        if '@' in content:
            b64_part, server_part = content.rsplit('@', 1)
            decoded = base64.b64decode(b64_part + '==').decode('utf-8')
            method, password = decoded.split(':', 1)
            server, port = server_part.rsplit(':', 1)
        else:
            # 整个都是 base64
            decoded = base64.b64decode(content + '==').decode('utf-8')
            # method:password@server:port
            method_pass, server_port = decoded.rsplit('@', 1)
            method, password = method_pass.split(':', 1)
            server, port = server_port.rsplit(':', 1)
        
        return {
            "type": "ss",
            "server": server,
            "port": int(port),
            "cipher": method,
            "password": password,
        }
    except Exception as e:
        logger.warning(f"Failed to parse ss link: {e}")
        return None


def parse_socks5_to_clash(share: str) -> Optional[Dict[str, Any]]:
    """解析 socks5:// 链接为 Clash 代理配置"""
    try:
        # socks5://user:pass@server:port 或 socks5://server:port
        content = share.replace("socks5://", "").replace("socks://", "")
        if '#' in content:
            content = content.split('#')[0]
        
        proxy: Dict[str, Any] = {"type": "socks5"}
        
        if '@' in content:
            auth, server_part = content.rsplit('@', 1)
            if ':' in auth:
                proxy["username"], proxy["password"] = auth.split(':', 1)
            server, port = server_part.rsplit(':', 1)
        else:
            server, port = content.rsplit(':', 1)
        
        proxy["server"] = server
        proxy["port"] = int(port)
        return proxy
    except Exception as e:
        logger.warning(f"Failed to parse socks5 link: {e}")
        return None


def parse_share_to_clash(share: str) -> Optional[Dict[str, Any]]:
    """根据链接类型自动解析为 Clash 配置"""
    share = share.strip()
    share_lower = share.lower()
    
    if share_lower.startswith('vmess://'):
        return parse_vmess_to_clash(share)
    elif share_lower.startswith('ss://'):
        return parse_ss_to_clash(share)
    elif share_lower.startswith('socks5://') or share_lower.startswith('socks://'):
        return parse_socks5_to_clash(share)
    # vless 和 trojan 暂不支持自动解析，需要手动填 clash 配置
    return None


def get_clash_proxy(node: Node, node_name: str) -> Optional[Dict[str, Any]]:
    """获取节点的 Clash 代理配置"""
    # 优先使用手动配置的 clash 字段
    if node.clash:
        return node.clash.to_clash_dict(node_name)
    
    # 尝试从 share 链接自动解析
    proxy = parse_share_to_clash(node.share)
    if proxy:
        proxy["name"] = node_name
        return proxy
    
    return None


def render_clash_subscription(customer: Customer) -> str:
    """
    渲染 Clash 订阅配置
    
    Args:
        customer: 客户对象
    
    Returns:
        Clash YAML 配置内容
    """
    proxies: List[Dict[str, Any]] = []
    proxy_names: List[str] = []
    warnings: List[str] = []
    
    # 主用节点
    primary_name = customer.get_primary_display_name()
    primary_node = customer.get_effective_primary()
    primary_proxy = get_clash_proxy(primary_node, primary_name)
    
    if primary_proxy:
        proxies.append(primary_proxy)
        proxy_names.append(primary_name)
    else:
        warning = f"主节点无法解析为 Clash 配置，已跳过: {customer.name}"
        warnings.append(warning)
        logger.warning(warning)
    
    # 备用节点
    backup_name = customer.get_backup_display_name()
    backup_node = customer.get_effective_backup()
    backup_proxy = get_clash_proxy(backup_node, backup_name)
    
    if backup_proxy:
        proxies.append(backup_proxy)
        proxy_names.append(backup_name)
    else:
        warning = f"备用节点无法解析为 Clash 配置，已跳过: {customer.name}"
        warnings.append(warning)
        logger.warning(warning)
    
    # 如果没有有效节点，报错
    if not proxies:
        error_msg = f"客户 {customer.name} 没有可用的 Clash 节点配置"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # 构建 Clash 配置
    config: Dict[str, Any] = {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "info",
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "Proxy",
                "type": "select",
                "proxies": proxy_names
            }
        ],
        "rules": [
            "MATCH,Proxy"
        ]
    }
    
    # 添加警告注释（如果有）
    yaml_content = yaml.dump(
        config,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False
    )
    
    if warnings:
        warning_comments = "\n".join([f"# WARNING: {w}" for w in warnings])
        yaml_content = warning_comments + "\n" + yaml_content
    
    return yaml_content

