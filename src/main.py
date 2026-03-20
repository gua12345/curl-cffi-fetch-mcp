"""FastAPI 主应用

整合 MCP 和 OneAPI 端点，提供统一的服务入口
"""

import asyncio
import contextlib
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Mount
from starlette.middleware.base import BaseHTTPMiddleware
from src.config import settings
from src.auth import verify_api_key
from src.api.oneapi_endpoint import router as oneapi_router
from src.api.mcp_endpoint import mcp, cache_manager


class MCPAuthMiddleware(BaseHTTPMiddleware):
    """MCP 端点鉴权中间件

    拦截所有 /mcp 路径的请求，复用 verify_api_key 进行鉴权
    """

    async def dispatch(self, request: Request, call_next):
        # 只对 /mcp 路径进行鉴权
        if request.url.path.startswith("/mcp"):
            try:
                await verify_api_key(request)
            except HTTPException as e:
                # 鉴权失败，返回 401
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=e.status_code,
                    content={"error": e.detail},
                    headers=e.headers
                )

        # 鉴权通过或非 MCP 路径，继续处理请求
        response = await call_next(request)
        return response


# 创建 lifespan 管理器来初始化 MCP 任务组
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """管理 MCP session manager 的生命周期和后台清理任务"""
    # 启动后台清理任务（缓存强制启用）
    cleanup_task = asyncio.create_task(cache_cleanup_task())

    async with mcp.session_manager.run():
        yield

    # 关闭后台清理任务
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


async def cache_cleanup_task():
    """后台定期清理缓存任务"""
    while True:
        try:
            await asyncio.sleep(settings.CACHE_CLEANUP_INTERVAL)

            # 清理完全读取的缓存
            fully_read_count = await cache_manager.cleanup_fully_read()

            # 清理过期未读缓存
            expired_count = await cache_manager.cleanup_expired()

            # 可选：记录清理日志
            if fully_read_count > 0 or expired_count > 0:
                print(f"缓存清理: 完全读取 {fully_read_count} 个, 过期 {expired_count} 个")

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"缓存清理任务出错: {e}")
            # 继续运行，不中断清理任务


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

# 添加 MCP 鉴权中间件（复用 verify_api_key）
app.add_middleware(MCPAuthMiddleware)

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
