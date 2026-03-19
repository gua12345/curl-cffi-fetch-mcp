"""响应数据模型"""

from typing import Optional, Any, List, Dict
from pydantic import BaseModel, Field


class OneAPIResponse(BaseModel):
    """OneAPI 统一响应格式"""

    success: bool = Field(..., description="请求是否成功")
    data: Optional[Any] = Field(default=None, description="响应数据")
    error: Optional[Dict[str, str]] = Field(default=None, description="错误信息")


class FetchResult(BaseModel):
    """抓取结果数据"""

    url: str = Field(..., description="目标 URL")
    status_code: int = Field(..., description="HTTP 状态码")
    content_type: Optional[str] = Field(default=None, description="内容类型")
    markdown: str = Field(..., description="Markdown 格式的内容")
    length: int = Field(..., description="内容长度")


class ProxyInfo(BaseModel):
    """代理信息"""

    id: str = Field(..., description="代理标识符")
    description: str = Field(..., description="代理描述")
