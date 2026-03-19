"""FastAPI 主应用

整合 MCP 和 OneAPI 端点，提供统一的服务入口
"""

import contextlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Mount
from src.config import settings
from src.api.oneapi_endpoint import router as oneapi_router
from src.api.mcp_endpoint import mcp


# 创建 lifespan 管理器来初始化 MCP 任务组
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """管理 MCP session manager 的生命周期"""
    async with mcp.session_manager.run():
        yield


# 创建 FastAPI 应用
app = FastAPI(
    title="curl-cffi Fetch Service",
    description="使用 curl-cffi 抓取网页内容并转换为 Markdown，支持 MCP 和 OneAPI 接口",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 使用 Starlette Mount 挂载 MCP 应用
# 注意：必须在添加中间件之后挂载
app.router.routes.append(Mount("/mcp", app=mcp.streamable_http_app()))

# 注册 OneAPI 路由
app.include_router(oneapi_router)

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "curl-cffi-fetch-mcp",
        "version": "1.0.0"
    }


# 根路径
@app.get("/")
async def root():
    """根路径，返回服务信息"""
    return {
        "service": "curl-cffi Fetch Service",
        "version": "1.0.0",
        "endpoints": {
            "mcp": "/mcp (MCP Streamable HTTP)",
            "oneapi_proxies": "GET /v1/proxies",
            "oneapi_fetch": "POST /v1/fetch",
            "health": "GET /health",
            "docs": "GET /docs"
        },
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
