"""
Sub Gateway - Clash 格式渲染服务
"""
from typing import Dict, Any, List, Optional

import yaml

from app.models import Customer, Node
from app.utils.logging import logger


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
    primary_name = f"{customer.name}-主用-加速"
    primary_node = customer.get_effective_primary()
    
    if primary_node.clash:
        proxies.append(primary_node.clash.to_clash_dict(primary_name))
        proxy_names.append(primary_name)
    else:
        warning = f"主节点缺少 clash 配置，已跳过: {customer.name}"
        warnings.append(warning)
        logger.warning(warning)
    
    # 备用节点
    backup_name = f"{customer.name}-备用-直连"
    backup_node = customer.get_effective_backup()
    
    if backup_node.clash:
        proxies.append(backup_node.clash.to_clash_dict(backup_name))
        proxy_names.append(backup_name)
    else:
        warning = f"备用节点缺少 clash 配置，已跳过: {customer.name}"
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
