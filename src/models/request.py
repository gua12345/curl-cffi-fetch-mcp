"""请求数据模型"""

from typing import Optional, Dict
from pydantic import BaseModel, Field


class FetchRequest(BaseModel):
    """网页抓取请求模型"""

    url: str = Field(..., description="目标网页 URL")
    impersonate: Optional[str] = Field(
        default="chrome",
        description="浏览器类型（chrome/safari/edge）"
    )
    proxy: Optional[str] = Field(
        default=None,
        description="代理配置，支持两种模式：1) 代理标识符（如 hk/sg/us）从代理池查找；2) 完整代理 URL（如 http://proxy:8080, socks5://user:pass@proxy:1080）直接使用"
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="自定义请求头"
    )
    cookies: Optional[Dict[str, str]] = Field(
        default=None,
        description="自定义 Cookies"
    )
    timeout: Optional[int] = Field(
        default=30,
        description="超时时间（秒）"
    )
