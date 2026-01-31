"""
Sub Gateway - 订阅输出路由
"""
from fastapi import APIRouter, Request, HTTPException, Response

from app.storage import storage
from app.services.v2rayn import render_v2rayn_subscription
from app.services.clash import render_clash_subscription
from app.utils.logging import log_subscribe_access, logger

router = APIRouter(prefix="/s", tags=["subscribe"])


def get_client_ip(request: Request) -> str:
    """获取客户端真实 IP"""
    # 优先使用反向代理头
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


@router.get("/{token}/v2rayn")
async def get_v2rayn_subscription(token: str, request: Request):
    """
    获取 v2rayN 格式订阅
    
    返回 Base64 编码的分享链接列表
    """
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "unknown")
    
    # 查找客户
    customer = storage.get_customer_by_token(token)
    
    if not customer:
        log_subscribe_access(
            token=token,
            client_ip=client_ip,
            user_agent=user_agent,
            format_type="v2rayn",
            status_code=403
        )
        raise HTTPException(status_code=403, detail="Invalid token")
    
    if not customer.enabled:
        log_subscribe_access(
            token=token,
            client_ip=client_ip,
            user_agent=user_agent,
            format_type="v2rayn",
            status_code=403,
            customer_name=customer.name
        )
        raise HTTPException(status_code=403, detail="Subscription disabled")
    
    try:
        content = render_v2rayn_subscription(customer)
        
        log_subscribe_access(
            token=token,
            client_ip=client_ip,
            user_agent=user_agent,
            format_type="v2rayn",
            status_code=200,
            customer_name=customer.name
        )
        
        return Response(
            content=content,
            media_type="text/plain; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"Error rendering v2rayn subscription: {e}")
        log_subscribe_access(
            token=token,
            client_ip=client_ip,
            user_agent=user_agent,
            format_type="v2rayn",
            status_code=500,
            customer_name=customer.name
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{token}/clash")
async def get_clash_subscription(token: str, request: Request):
    """
    获取 Clash 格式订阅
    
    返回 Clash YAML 配置
    """
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "unknown")
    
    # 查找客户
    customer = storage.get_customer_by_token(token)
    
    if not customer:
        log_subscribe_access(
            token=token,
            client_ip=client_ip,
            user_agent=user_agent,
            format_type="clash",
            status_code=403
        )
        raise HTTPException(status_code=403, detail="Invalid token")
    
    if not customer.enabled:
        log_subscribe_access(
            token=token,
            client_ip=client_ip,
            user_agent=user_agent,
            format_type="clash",
            status_code=403,
            customer_name=customer.name
        )
        raise HTTPException(status_code=403, detail="Subscription disabled")
    
    try:
        content = render_clash_subscription(customer)
        
        log_subscribe_access(
            token=token,
            client_ip=client_ip,
            user_agent=user_agent,
            format_type="clash",
            status_code=200,
            customer_name=customer.name
        )
        
        return Response(
            content=content,
            media_type="text/yaml; charset=utf-8"
        )
    except ValueError as e:
        logger.error(f"Error rendering clash subscription: {e}")
        log_subscribe_access(
            token=token,
            client_ip=client_ip,
            user_agent=user_agent,
            format_type="clash",
            status_code=400,
            customer_name=customer.name
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error rendering clash subscription: {e}")
        log_subscribe_access(
            token=token,
            client_ip=client_ip,
            user_agent=user_agent,
            format_type="clash",
            status_code=500,
            customer_name=customer.name
        )
        raise HTTPException(status_code=500, detail="Internal server error")
