"""配置管理模块

配置优先级：
1. 代码默认值
2. 环境变量
3. 请求参数
"""

import json
from pathlib import Path
from typing import Dict, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings

# 获取项目根目录（src 的父目录）
PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """应用配置类"""

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # 鉴权配置
    API_KEY: str = ""  # 必填，从 .env 读取

    # curl-cffi 默认配置
    DEFAULT_IMPERSONATE: str = "chrome"  # 默认浏览器类型
    DEFAULT_TIMEOUT: int = 30  # 默认超时（秒）
    DEFAULT_PROXY: str = ""  # 默认代理标识符（如 "sg", "cn"）

    # 代理池配置（从 .env 读取 JSON 字符串）
    # 格式：{"标识符": {"url": "代理URL", "description": "描述"}}
    PROXY_POOL: Dict[str, Dict[str, str]] | None = None

    # html2text 配置
    HTML2TEXT_BODY_WIDTH: int = 0  # 0 表示不换行
    HTML2TEXT_IGNORE_LINKS: bool = False
    HTML2TEXT_IGNORE_IMAGES: bool = False

    # 缓存配置（强制启用）
    CACHE_REDIS_URL: str = ""  # Redis URL（配置后使用 Redis，否则使用内存缓存）

    # 缓存行为配置
    CACHE_TOKEN_THRESHOLD: int = 2000
    CACHE_DEFAULT_CHUNK_SIZE: int = 2000

    # 缓存清理配置
    CACHE_DELETE_DELAY_SECONDS: int = 300  # 完全读取后延迟删除（5 分钟）
    CACHE_TTL_SECONDS: int = 1800  # 未读完缓存的 TTL（30 分钟）
    CACHE_CLEANUP_INTERVAL: int = 300  # 后台清理间隔（5 分钟）

    @field_validator("PROXY_POOL", mode="before")
    @classmethod
    def parse_proxy_pool(cls, v: Any) -> Dict[str, Dict[str, str]]:
        """解析环境变量中的 JSON 字符串为 dict"""
        if v is None:
            return {}
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v if isinstance(v, dict) else {}

    model_config = {
        "env_file_encoding": "utf-8",
        "case_sensitive": True,  # 环境变量名大小写敏感
        "extra": "ignore"  # 忽略额外的环境变量
    }


# 全局配置实例
settings = Settings()
