"""鉴权中间件

验证请求中的 API Key，支持 Header 和 Query 参数两种方式
"""

from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.config import settings


# HTTP Bearer 认证方案
security = HTTPBearer(auto_error=False)


async def verify_api_key(request: Request) -> bool:
    """
    验证 API Key

    支持两种方式：
    1. Header: Authorization: Bearer <API_KEY>
    2. Query: ?api_key=<API_KEY>

    参数：
        request: FastAPI 请求对象

    返回：
        验证是否通过

    异常：
        HTTPException: 鉴权失败时抛出 401 错误
    """
    # 从配置中获取正确的 API Key
    correct_api_key = settings.API_KEY

    # 如果未配置 API Key，则跳过验证
    if not correct_api_key:
        return True

    # 方式 1: 从 Header 中获取 API Key
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        api_key = auth_header.replace("Bearer ", "")
        if api_key == correct_api_key:
            return True

    # 方式 2: 从 Query 参数中获取 API Key
    api_key_query = request.query_params.get("api_key")
    if api_key_query == correct_api_key:
        return True

    # 鉴权失败
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_api_key_from_request(request: Request) -> Optional[str]:
    """
    从请求中提取 API Key（不验证）

    参数：
        request: FastAPI 请求对象

    返回：
        API Key 或 None
    """
    # 从 Header 中获取
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")

    # 从 Query 参数中获取
    return request.query_params.get("api_key")
