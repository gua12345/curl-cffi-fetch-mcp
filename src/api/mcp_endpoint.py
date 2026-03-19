"""MCP Streamable HTTP 端点

使用 MCP Python SDK 提供符合 Model Context Protocol 的工具接口
"""

from typing import Dict, Any
from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.core.fetcher import fetch_url
from src.core.converter import html_to_markdown


# 创建 MCP 服务器实例
# streamable_http_path="/" 让端点直接在挂载点响应，避免路径重定向问题
mcp = FastMCP("curl-cffi-fetch", json_response=True, streamable_http_path="/")


@mcp.tool()
async def list_proxies() -> str:
    """
    查询可用的代理列表

    返回所有配置的代理标识符和描述
    """
    proxy_pool = settings.PROXY_POOL

    if not proxy_pool:
        print(proxy_pool)
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
        proxy: 代理标识符（如 sg/cn/us），使用 list_proxies 工具查询可用代理
        headers: 自定义请求头（可选）
        cookies: 自定义 Cookies（可选）
        timeout: 超时时间（秒），默认 30

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

        return markdown

    except Exception as e:
        return f"Error: {str(e)}"
