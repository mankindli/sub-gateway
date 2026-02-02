"""
Sub Gateway - 管理接口路由
"""
import secrets
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings
from app.storage import storage
from app.models import (
    Customer,
    Nodes,
    Override,
    CreateCustomerRequest,
    CreateCustomerResponse,
    UpdateCustomerRequest,
    RotateTokenResponse,
    SetOverrideRequest,
    CustomerListItem,
)
from app.utils.token import generate_token
from app.utils.logging import logger

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """验证 Basic Auth 凭据"""
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        settings.admin_username.encode("utf8")
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        settings.admin_password.encode("utf8")
    )
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def get_subscribe_urls(token: str) -> dict:
    """生成订阅 URL"""
    base = settings.base_url.rstrip('/')
    return {
        "v2rayn": f"{base}/s/{token}/v2rayn",
        "clash": f"{base}/s/{token}/clash"
    }


@router.post("/customers", response_model=CreateCustomerResponse)
async def create_customer(
    request: CreateCustomerRequest,
    username: str = Depends(verify_credentials)
):
    """创建新客户"""
    token = generate_token(32)
    
    customer = Customer(
        token=token,
        name=request.name,
        enabled=request.enabled,
        nodes=request.nodes,
        ip_source=request.ip_source,
        expires_at=request.expires_at,
        remark=request.remark,
        primary_name=request.primary_name,
        backup_name=request.backup_name,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    try:
        storage.create_customer(customer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    logger.info(f"Admin {username} created customer: {request.name}")
    
    return CreateCustomerResponse(
        token=token,
        name=request.name,
        subscribe_urls=get_subscribe_urls(token)
    )


@router.get("/customers", response_model=List[CustomerListItem])
async def list_customers(username: str = Depends(verify_credentials)):
    """列出所有客户"""
    customers = storage.get_all_customers()
    
    return [
        CustomerListItem(
            token=c.token,
            name=c.name,
            enabled=c.enabled,
            has_override=c.override is not None,
            ip_source=c.ip_source,
            expires_at=c.expires_at,
            remark=c.remark,
            primary_name=c.primary_name,
            backup_name=c.backup_name,
            created_at=c.created_at,
            updated_at=c.updated_at,
            subscribe_urls=get_subscribe_urls(c.token)
        )
        for c in customers
    ]


@router.get("/customers/{token}")
async def get_customer(token: str, username: str = Depends(verify_credentials)):
    """获取客户详情"""
    customer = storage.get_customer_by_token(token)
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return {
        **customer.model_dump(mode='json'),
        "subscribe_urls": get_subscribe_urls(token)
    }


@router.patch("/customers/{token}")
async def update_customer(
    token: str,
    request: UpdateCustomerRequest,
    username: str = Depends(verify_credentials)
):
    """更新客户信息"""
    customer = storage.update_customer(
        token=token,
        name=request.name,
        enabled=request.enabled,
        nodes=request.nodes,
        ip_source=request.ip_source,
        expires_at=request.expires_at,
        remark=request.remark,
        primary_name=request.primary_name,
        backup_name=request.backup_name
    )
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    logger.info(f"Admin {username} updated customer: {customer.name}")
    
    return {
        **customer.model_dump(mode='json'),
        "subscribe_urls": get_subscribe_urls(token)
    }


@router.post("/customers/{token}/rotate", response_model=RotateTokenResponse)
async def rotate_token(token: str, username: str = Depends(verify_credentials)):
    """轮换客户 Token"""
    new_token = generate_token(32)
    
    try:
        customer = storage.rotate_token(token, new_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    logger.info(f"Admin {username} rotated token for customer: {customer.name}")
    
    return RotateTokenResponse(
        old_token=token,
        new_token=new_token,
        subscribe_urls=get_subscribe_urls(new_token)
    )


@router.post("/customers/{token}/override")
async def set_override(
    token: str,
    request: SetOverrideRequest,
    username: str = Depends(verify_credentials)
):
    """设置应急覆盖"""
    if not request.primary and not request.backup:
        raise HTTPException(
            status_code=400,
            detail="At least one of primary or backup must be provided"
        )
    
    override = Override(
        primary=request.primary,
        backup=request.backup,
        note=request.note
    )
    
    customer = storage.set_override(token, override)
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    logger.info(f"Admin {username} set override for customer: {customer.name}")
    
    return {
        "message": "Override set successfully",
        "customer": customer.name,
        "override": override.model_dump(mode='json')
    }


@router.delete("/customers/{token}/override")
async def clear_override(token: str, username: str = Depends(verify_credentials)):
    """清除应急覆盖"""
    customer = storage.clear_override(token)
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    logger.info(f"Admin {username} cleared override for customer: {customer.name}")
    
    return {
        "message": "Override cleared successfully",
        "customer": customer.name
    }


@router.delete("/customers/{token}")
async def delete_customer(token: str, username: str = Depends(verify_credentials)):
    """删除客户"""
    customer = storage.get_customer_by_token(token)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    storage.delete_customer(token)
    logger.info(f"Admin {username} deleted customer: {customer.name}")
    
    return {"message": "Customer deleted successfully", "name": customer.name}
