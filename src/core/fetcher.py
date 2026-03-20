"""网页抓取核心逻辑

使用 curl-cffi 的浏览器指纹模拟特性抓取网页内容
"""

from typing import Optional, Dict, Tuple
from curl_cffi.requests import AsyncSession


async def fetch_url(
    url: str,
    impersonate: str = "chrome",
    headers: Optional[Dict[str, str]] = None,
    cookies: Optional[Dict[str, str]] = None,
    proxy: Optional[str] = None,  # 代理标识符或完整代理 URL
    timeout: int = 30,
    proxy_pool: Optional[Dict[str, Dict[str, str]]] = None
) -> Tuple[str, int, Dict[str, str]]:
    """
    抓取网页内容

    使用 curl-cffi 的 AsyncSession 进行异步请求，支持浏览器指纹模拟

    参数：
        url: 目标网页 URL
        impersonate: 浏览器类型（chrome/safari/edge）
        headers: 自定义请求头
        cookies: 自定义 Cookies
        proxy: 代理标识符（如 "sg", "cn"）或完整代理 URL（如 "http://proxy:8080"）
               - 如果以 http://, https://, socks5:// 开头，则直接使用该 URL
               - 否则从代理池中查找对应的代理 URL
        timeout: 超时时间（秒）
        proxy_pool: 代理池配置

    返回：
        (html_content, status_code, response_headers)

    异常：
        Exception: 网络请求失败时抛出异常
    """
    # 解析代理：支持标识符映射和直接 URL 两种模式
    proxy_url = None
    if proxy:
        # 判断是否为完整的代理 URL（以协议开头）
        if proxy.startswith(("http://", "https://", "socks5://")):
            # 直接模式：使用传入的完整代理 URL
            proxy_url = proxy
        elif proxy_pool and proxy in proxy_pool:
            # 映射模式：从代理池中查找
            proxy_url = proxy_pool[proxy].get("url")

    # 构建代理配置
    proxies = None
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

    # 使用 AsyncSession 发送请求
    async with AsyncSession(impersonate=impersonate) as session:
        response = await session.get(
            url,
            headers=headers,
            cookies=cookies,
            proxies=proxies,
            timeout=timeout
        )

        # 返回响应内容、状态码和响应头
        return (
            response.text,
            response.status_code,
            dict(response.headers)
        )
