"""
Sub Gateway - 轻量订阅网关
FastAPI 应用入口
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.config import settings
from app.routers import subscribe, admin
from app.utils.logging import logger

app = FastAPI(
    title="Sub Gateway",
    description="轻量订阅网关系统 - 为客户分发代理节点",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 中间件（可选，用于开发）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件（管理界面）
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# 注册路由
app.include_router(subscribe.router)
app.include_router(admin.router)


@app.get("/manage")
async def admin_page():
    """管理界面入口"""
    return RedirectResponse(url="/static/admin.html")


@app.get("/")
async def root():
    """健康检查"""
    return {
        "service": "Sub Gateway",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("Sub Gateway starting...")
    logger.info(f"Base URL: {settings.base_url}")
    logger.info(f"Config dir: {settings.config_dir}")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    logger.info("Sub Gateway shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
