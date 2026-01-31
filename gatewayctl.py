#!/usr/bin/env python3
"""
Sub Gateway CLI 管理工具 - gatewayctl

用法:
    python gatewayctl.py create-customer --name "客户名称"
    python gatewayctl.py list-customers
    python gatewayctl.py rotate-token --token <token>
    python gatewayctl.py set-override --token <token> --primary-share "ss://..."
    python gatewayctl.py clear-override --token <token>
    python gatewayctl.py disable-customer --token <token>
    python gatewayctl.py enable-customer --token <token>
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.storage import CustomerStorage
from app.models import Customer, Nodes, Node, ClashProxy, Override
from app.utils.token import generate_token
from app.config import settings


def create_customer(args):
    """创建新客户"""
    storage = CustomerStorage()
    
    token = generate_token(32)
    
    # 如果提供了节点信息，使用它们；否则使用占位符
    if args.primary_share or args.backup_share:
        primary_node = Node(
            share=args.primary_share or "ss://placeholder",
            clash=ClashProxy(
                type="ss",
                server="placeholder.example.com",
                port=8388,
                cipher="aes-256-gcm",
                password="placeholder"
            ) if args.primary_share else None
        )
        backup_node = Node(
            share=args.backup_share or "socks5://placeholder:1080",
            clash=ClashProxy(
                type="socks5",
                server="placeholder.example.com",
                port=1080
            ) if args.backup_share else None
        )
    else:
        # 默认占位符节点
        primary_node = Node(
            share="ss://YWVzLTI1Ni1nY206cGxhY2Vob2xkZXI=@placeholder.example.com:8388",
            clash=ClashProxy(
                type="ss",
                server="placeholder.example.com",
                port=8388,
                cipher="aes-256-gcm",
                password="placeholder"
            )
        )
        backup_node = Node(
            share="socks5://placeholder.example.com:1080",
            clash=ClashProxy(
                type="socks5",
                server="placeholder.example.com",
                port=1080
            )
        )
    
    customer = Customer(
        token=token,
        name=args.name,
        enabled=True,
        nodes=Nodes(primary=primary_node, backup=backup_node),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    storage.create_customer(customer)
    
    base_url = os.environ.get("BASE_URL", settings.base_url).rstrip('/')
    
    print(f"\n✅ 客户创建成功！")
    print(f"   名称: {args.name}")
    print(f"   Token: {token}")
    print(f"\n📋 订阅链接:")
    print(f"   v2rayN: {base_url}/s/{token}/v2rayn")
    print(f"   Clash:  {base_url}/s/{token}/clash")
    print(f"\n⚠️  请在 config/customers.yml 中更新实际节点配置")


def list_customers(args):
    """列出所有客户"""
    storage = CustomerStorage()
    customers = storage.get_all_customers()
    
    if not customers:
        print("📭 暂无客户")
        return
    
    base_url = os.environ.get("BASE_URL", settings.base_url).rstrip('/')
    
    print(f"\n📋 客户列表 (共 {len(customers)} 个):\n")
    print("-" * 80)
    
    for c in customers:
        status = "✅ 启用" if c.enabled else "❌ 禁用"
        override = "🔄 有覆盖" if c.override else ""
        
        print(f"名称: {c.name}")
        print(f"状态: {status} {override}")
        print(f"Token: {c.token}")
        print(f"v2rayN: {base_url}/s/{c.token}/v2rayn")
        print(f"Clash:  {base_url}/s/{c.token}/clash")
        print(f"创建时间: {c.created_at}")
        print("-" * 80)


def rotate_token(args):
    """轮换 Token"""
    storage = CustomerStorage()
    
    new_token = generate_token(32)
    customer = storage.rotate_token(args.token, new_token)
    
    if not customer:
        print(f"❌ 未找到 Token: {args.token}")
        sys.exit(1)
    
    base_url = os.environ.get("BASE_URL", settings.base_url).rstrip('/')
    
    print(f"\n✅ Token 轮换成功！")
    print(f"   客户: {customer.name}")
    print(f"   旧 Token: {args.token}")
    print(f"   新 Token: {new_token}")
    print(f"\n📋 新订阅链接:")
    print(f"   v2rayN: {base_url}/s/{new_token}/v2rayn")
    print(f"   Clash:  {base_url}/s/{new_token}/clash")


def set_override(args):
    """设置应急覆盖"""
    storage = CustomerStorage()
    
    # 检查客户是否存在
    customer = storage.get_customer_by_token(args.token)
    if not customer:
        print(f"❌ 未找到 Token: {args.token}")
        sys.exit(1)
    
    # 构建覆盖节点
    primary_node = None
    backup_node = None
    
    if args.primary_share:
        primary_node = Node(share=args.primary_share)
        if args.primary_clash_file:
            with open(args.primary_clash_file, 'r') as f:
                clash_data = json.load(f)
                primary_node.clash = ClashProxy(**clash_data)
    
    if args.backup_share:
        backup_node = Node(share=args.backup_share)
        if args.backup_clash_file:
            with open(args.backup_clash_file, 'r') as f:
                clash_data = json.load(f)
                backup_node.clash = ClashProxy(**clash_data)
    
    if not primary_node and not backup_node:
        print("❌ 必须提供 --primary-share 或 --backup-share")
        sys.exit(1)
    
    override = Override(
        primary=primary_node,
        backup=backup_node,
        note=args.note
    )
    
    storage.set_override(args.token, override)
    
    print(f"\n✅ 覆盖设置成功！")
    print(f"   客户: {customer.name}")
    if primary_node:
        print(f"   主节点覆盖: {primary_node.share[:50]}...")
    if backup_node:
        print(f"   备节点覆盖: {backup_node.share[:50]}...")
    if args.note:
        print(f"   备注: {args.note}")


def clear_override(args):
    """清除应急覆盖"""
    storage = CustomerStorage()
    
    customer = storage.clear_override(args.token)
    
    if not customer:
        print(f"❌ 未找到 Token: {args.token}")
        sys.exit(1)
    
    print(f"\n✅ 覆盖已清除！")
    print(f"   客户: {customer.name}")


def disable_customer(args):
    """禁用客户"""
    storage = CustomerStorage()
    
    customer = storage.update_customer(args.token, enabled=False)
    
    if not customer:
        print(f"❌ 未找到 Token: {args.token}")
        sys.exit(1)
    
    print(f"\n✅ 客户已禁用: {customer.name}")


def enable_customer(args):
    """启用客户"""
    storage = CustomerStorage()
    
    customer = storage.update_customer(args.token, enabled=True)
    
    if not customer:
        print(f"❌ 未找到 Token: {args.token}")
        sys.exit(1)
    
    print(f"\n✅ 客户已启用: {customer.name}")


def main():
    parser = argparse.ArgumentParser(
        description="Sub Gateway CLI 管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # create-customer
    create_parser = subparsers.add_parser("create-customer", help="创建新客户")
    create_parser.add_argument("--name", required=True, help="客户名称")
    create_parser.add_argument("--primary-share", help="主节点分享链接（可选）")
    create_parser.add_argument("--backup-share", help="备用节点分享链接（可选）")
    create_parser.set_defaults(func=create_customer)
    
    # list-customers
    list_parser = subparsers.add_parser("list-customers", help="列出所有客户")
    list_parser.set_defaults(func=list_customers)
    
    # rotate-token
    rotate_parser = subparsers.add_parser("rotate-token", help="轮换 Token")
    rotate_parser.add_argument("--token", required=True, help="当前 Token")
    rotate_parser.set_defaults(func=rotate_token)
    
    # set-override
    override_parser = subparsers.add_parser("set-override", help="设置应急覆盖")
    override_parser.add_argument("--token", required=True, help="客户 Token")
    override_parser.add_argument("--primary-share", help="主节点覆盖分享链接")
    override_parser.add_argument("--primary-clash-file", help="主节点 Clash 配置 JSON 文件")
    override_parser.add_argument("--backup-share", help="备用节点覆盖分享链接")
    override_parser.add_argument("--backup-clash-file", help="备用节点 Clash 配置 JSON 文件")
    override_parser.add_argument("--note", help="备注说明")
    override_parser.set_defaults(func=set_override)
    
    # clear-override
    clear_parser = subparsers.add_parser("clear-override", help="清除应急覆盖")
    clear_parser.add_argument("--token", required=True, help="客户 Token")
    clear_parser.set_defaults(func=clear_override)
    
    # disable-customer
    disable_parser = subparsers.add_parser("disable-customer", help="禁用客户")
    disable_parser.add_argument("--token", required=True, help="客户 Token")
    disable_parser.set_defaults(func=disable_customer)
    
    # enable-customer
    enable_parser = subparsers.add_parser("enable-customer", help="启用客户")
    enable_parser.add_argument("--token", required=True, help="客户 Token")
    enable_parser.set_defaults(func=enable_customer)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
