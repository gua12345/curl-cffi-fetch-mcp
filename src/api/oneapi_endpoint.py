"""OneAPI REST API 端点

提供符合 OneAPI 规范的 REST API 接口
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from src.auth import verify_api_key
from src.config import settings
from src.core.fetcher import fetch_url
from src.core.converter import html_to_markdown
from src.core.headers_generator import get_supported_impersonates
from src.models.request import FetchRequest
from src.models.response import OneAPIResponse, FetchResult, ProxyInfo


# 创建路由器
router = APIRouter(prefix="/v1", tags=["OneAPI"])


@router.get("/impersonates", response_model=OneAPIResponse)
async def get_impersonates(request: Request):
    """
    查询支持的浏览器指纹列表

    返回所有 curl-cffi 支持的 impersonate 参数及其描述
    """
    # 验证 API Key
    await verify_api_key(request)

    try:
        impersonates = get_supported_impersonates()

        return OneAPIResponse(
            success=True,
            data=impersonates,
            error=None
        )

    except Exception as e:
        return OneAPIResponse(
            success=False,
            data=None,
            error={
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        )


@router.get("/proxies", response_model=OneAPIResponse)
async def get_proxies(request: Request):
    """
    查询可用的代理列表

    返回所有配置的代理标识符和描述
    """
    # 验证 API Key
    await verify_api_key(request)

    try:
        proxy_pool = settings.PROXY_POOL

        if not proxy_pool:
            return OneAPIResponse(
                success=True,
                data=[],
                error=None
            )

        # 构建代理列表
        proxies: List[ProxyInfo] = []
        for proxy_id, proxy_info in proxy_pool.items():
            proxies.append(ProxyInfo(
                id=proxy_id,
                description=proxy_info.get("description", "无描述")
            ))

        return OneAPIResponse(
            success=True,
            data=proxies,
            error=None
        )

    except Exception as e:
        return OneAPIResponse(
            success=False,
            data=None,
            error={
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        )


@router.post("/fetch", response_model=OneAPIResponse)
async def fetch_webpage(fetch_request: FetchRequest, request: Request):
    """
    抓取网页内容并转换为 Markdown

    参数：
        fetch_request: 抓取请求参数
            - url: 目标网页 URL（必填）
            - impersonate: 浏览器类型（chrome/safari/edge），默认 chrome
            - proxy: 代理配置，支持两种模式：
                1) 代理标识符（如 "hk", "sg"）- 从代理池中查找
                2) 完整代理 URL（如 "http://proxy:8080", "socks5://user:pass@proxy:1080"）- 直接使用
            - headers: 自定义请求头（可选）
            - cookies: 自定义 Cookies（可选）
            - timeout: 超时时间（秒），默认 30

    返回：
        包含 Markdown 内容的响应
    """
    # 验证 API Key
    await verify_api_key(request)

    try:
        # 合并配置：使用请求参数覆盖默认配置
        final_impersonate = fetch_request.impersonate or settings.DEFAULT_IMPERSONATE
        final_timeout = fetch_request.timeout or settings.DEFAULT_TIMEOUT
        final_proxy = fetch_request.proxy or settings.DEFAULT_PROXY

        # 调用核心抓取逻辑
        html_content, status_code, response_headers = await fetch_url(
            url=fetch_request.url,
            impersonate=final_impersonate,
            headers=fetch_request.headers,
            cookies=fetch_request.cookies,
            proxy=final_proxy,
            timeout=final_timeout,
            proxy_pool=settings.PROXY_POOL
        )

        # 检查 HTTP 状态码
        if status_code >= 400:
            return OneAPIResponse(
                success=False,
                data=None,
                error={
                    "code": "HTTP_ERROR",
                    "message": f"HTTP {status_code} - 请求失败"
                }
            )

        # 转换为 Markdown
        markdown = html_to_markdown(
            html_content,
            body_width=settings.HTML2TEXT_BODY_WIDTH,
            ignore_links=settings.HTML2TEXT_IGNORE_LINKS,
            ignore_images=settings.HTML2TEXT_IGNORE_IMAGES
        )

        # 构建响应数据
        result = FetchResult(
            url=fetch_request.url,
            status_code=status_code,
            content_type=response_headers.get("content-type"),
            markdown=markdown,
            length=len(markdown)
        )

        return OneAPIResponse(
            success=True,
            data=result,
            error=None
        )

    except Exception as e:
        return OneAPIResponse(
            success=False,
            data=None,
            error={
                "code": "FETCH_ERROR",
                "message": f"Failed to fetch URL: {str(e)}"
            }
        )
