"""MCP Streamable HTTP 端点

使用 MCP Python SDK 提供符合 Model Context Protocol 的工具接口
"""

import json
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.core.fetcher import fetch_url
from src.core.converter import html_to_markdown
from src.core.cache import ContentCacheManager, count_tokens
import tiktoken


# 创建 MCP 服务器实例
# streamable_http_path="/" 让端点直接在挂载点响应，避免路径重定向问题
mcp = FastMCP("curl-cffi-fetch", json_response=True, streamable_http_path="/")

# 创建全局缓存管理器实例（强制启用）
cache_manager = ContentCacheManager(
    redis_url=settings.CACHE_REDIS_URL,
    ttl_seconds=settings.CACHE_TTL_SECONDS,
    delete_delay_seconds=settings.CACHE_DELETE_DELAY_SECONDS
)


@mcp.tool()
async def list_proxies() -> str:
    """
    查询可用的代理列表

    返回所有配置的代理标识符和描述
    """
    proxy_pool = settings.PROXY_POOL

    if not proxy_pool:
        return "当前没有配置可用代理"

    # 格式化代理列表
    proxy_list = []
    for proxy_id, proxy_info in proxy_pool.items():
        description = proxy_info.get("description", "无描述")
        proxy_list.append(f"- {proxy_id}: {description}")

    return "可用代理列表：\n" + "\n".join(proxy_list)


@mcp.tool()
async def fetch_url_tool(
    url: str,
    impersonate: str = "chrome",
    proxy: str = None,
    headers: Dict[str, str] = None,
    cookies: Dict[str, str] = None,
    timeout: int = 30
) -> str:
    """
    模拟浏览器指纹抓取网页内容并转换为 Markdown
    参数：
        url: 目标网页 URL
        impersonate: 浏览器类型（chrome/safari/edge），默认 chrome
        proxy: 代理配置，支持两种模式：
               1. 代理标识符（如 "hk", "sg"）- 从代理池中查找，使用 list_proxies 工具查询可用代理
               2. 完整代理 URL（如 "http://proxy.example.com:8080", "socks5://user:pass@proxy:1080"）- 直接使用该代理
        headers: 自定义请求头（可选）（JSON 对象）
        cookies: 自定义 Cookies（可选）（JSON 对象，格式：`{"name": "value"}`）
        timeout: 默认 30 秒
    返回：
        Markdown 格式的网页内容
    """
    try:
        # 合并配置：使用请求参数覆盖默认配置
        final_impersonate = impersonate or settings.DEFAULT_IMPERSONATE
        final_timeout = timeout or settings.DEFAULT_TIMEOUT
        final_proxy = proxy or settings.DEFAULT_PROXY

        # 调用核心抓取逻辑
        html_content, status_code, response_headers = await fetch_url(
            url=url,
            impersonate=final_impersonate,
            headers=headers,
            cookies=cookies,
            proxy=final_proxy,
            timeout=final_timeout,
            proxy_pool=settings.PROXY_POOL
        )

        # 检查 HTTP 状态码
        if status_code >= 400:
            return f"Error: HTTP {status_code} - 请求失败"

        # 转换为 Markdown
        markdown = html_to_markdown(
            html_content,
            body_width=settings.HTML2TEXT_BODY_WIDTH,
            ignore_links=settings.HTML2TEXT_IGNORE_LINKS,
            ignore_images=settings.HTML2TEXT_IGNORE_IMAGES
        )

        # 检查内容大小，超过阈值则缓存
        encoding = tiktoken.get_encoding("cl100k_base")
        token_count = count_tokens(markdown, encoding)

        # 如果超过阈值，缓存内容并返回元信息
        if token_count >= settings.CACHE_TOKEN_THRESHOLD:
            cached = await cache_manager.store(url, markdown)
            return json.dumps({
                "type": "cached",
                "uuid": cached.uuid,
                "url": url,
                "total_tokens": token_count,
                "message": "内容token超过设定阈值，内容已缓存，请使用 get_cached_content 工具分块读取"
            }, ensure_ascii=False)

        # 小内容直接返回
        return markdown

    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def get_cached_content(
    uuid: str,
    start_token: int = 0,
    end_token: Optional[int] = None,
    chunk_size: int = None
) -> str:
    """
    分块读取缓存的网页内容，你可以根据实际情况选择块大小以及是否读取完
    参数：
        uuid: 缓存内容的唯一标识符（从 fetch_url_tool 返回）
        start_token: 起始 token 位置（从 0 开始），默认 0
        end_token: 结束 token 位置（不包含），None 表示读取到末尾
        chunk_size: 默认分块大小（tokens），当 end_token 为 None 时使用
    返回：
        JSON 格式的分块内容
        uuid: ...,
        chunk: 实际的 Markdown 内容
        start_token: 0
        end_token: 2000
        total_tokens: 5000
        is_fully_read: false
        progress: 40% (2000/5000 tokens)
    """
    try:
        # 处理 chunk_size
        if end_token is None:
            if chunk_size is None:
                chunk_size = settings.CACHE_DEFAULT_CHUNK_SIZE
            end_token = start_token + chunk_size

        # 获取分块内容
        chunk, is_fully_read, actual_end_token = await cache_manager.get_chunk(
            uuid, start_token, end_token
        )

        if chunk is None:
            return json.dumps({
                "error": "缓存不存在或已过期"
            }, ensure_ascii=False)

        # 获取总 token 数（从缓存中读取）
        content = await cache_manager._backend.get(uuid)
        total_tokens = content.total_tokens if content else 0

        # 计算进度
        progress_percent = int((actual_end_token / total_tokens * 100)) if total_tokens > 0 else 0
        progress_str = f"{progress_percent}% ({actual_end_token}/{total_tokens} tokens)"

        return json.dumps({
            "uuid": uuid,
            "chunk": chunk,
            "start_token": start_token,
            "end_token": actual_end_token,
            "total_tokens": total_tokens,
            "is_fully_read": is_fully_read,
            "progress": progress_str
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "error": f"读取缓存失败: {str(e)}"
        }, ensure_ascii=False)
