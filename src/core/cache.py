"""缓存管理模块

实现 Token 感知的智能缓存机制：
- 支持内存和 Redis 两种后端
- 按 token 边界精确切分内容
- 自动清理完全读取和过期的缓存
"""

import asyncio
import pickle
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import tiktoken

try:
    from redis import asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class CachedContent:
    """缓存的内容条目"""
    uuid: str
    url: str
    markdown: str
    total_tokens: int
    token_offsets: List[int]
    created_at: float
    accessed_at: float
    read_ranges: Set[Tuple[int, int]] = field(default_factory=set)
    fully_read_at: Optional[float] = None

    def is_fully_read(self) -> bool:
        """检查是否已完全读取

        通过合并所有已读区间，检查是否覆盖 [0, total_tokens)
        """
        if not self.read_ranges:
            return False

        # 排序并合并区间
        sorted_ranges = sorted(self.read_ranges)
        merged = []

        for start, end in sorted_ranges:
            if not merged or merged[-1][1] < start:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)

        # 检查是否覆盖 [0, total_tokens)
        return len(merged) == 1 and merged[0][0] == 0 and merged[0][1] >= self.total_tokens


# ============================================================================
# Token 工具函数
# ============================================================================

def count_tokens(text: str, encoding: tiktoken.Encoding) -> int:
    """计算文本的 token 数"""
    return len(encoding.encode(text))


def build_token_offsets(text: str, encoding: tiktoken.Encoding) -> List[int]:
    """构建 token 边界的字符偏移表

    返回：[0, offset1, offset2, ..., len(text)]
    其中 offset_i 表示第 i 个 token 的起始字符位置
    """
    tokens = encoding.encode(text)
    offsets = [0]

    for i in range(len(tokens)):
        # 解码前 i+1 个 tokens，获取累计字符长度
        decoded = encoding.decode(tokens[:i+1])
        offsets.append(len(decoded))

    return offsets


def slice_by_tokens(
    text: str,
    token_offsets: List[int],
    start_token: int,
    end_token: int
) -> str:
    """按 token 区间切分文本

    参数：
        text: 原始文本
        token_offsets: 预计算的 token 边界偏移表
        start_token: 起始 token 索引
        end_token: 结束 token 索引（不包含）

    返回：
        切分后的文本片段
    """
    start_char = token_offsets[start_token]
    end_char = token_offsets[end_token] if end_token < len(token_offsets) else len(text)
    return text[start_char:end_char]


# ============================================================================
# 缓存后端抽象接口
# ============================================================================

class CacheBackend(ABC):
    """缓存后端抽象接口"""

    @abstractmethod
    async def store(self, content: CachedContent) -> None:
        """存储缓存内容"""
        pass

    @abstractmethod
    async def get(self, uuid: str) -> Optional[CachedContent]:
        """获取缓存内容"""
        pass

    @abstractmethod
    async def update(self, uuid: str, content: CachedContent) -> None:
        """更新缓存内容"""
        pass

    @abstractmethod
    async def delete(self, uuid: str) -> None:
        """删除缓存内容"""
        pass

    @abstractmethod
    async def list_all(self) -> List[CachedContent]:
        """列出所有缓存内容"""
        pass


# ============================================================================
# 内存缓存实现
# ============================================================================

class MemoryCacheBackend(CacheBackend):
    """内存缓存后端实现"""

    def __init__(self):
        self._cache: Dict[str, CachedContent] = {}
        self._lock = asyncio.Lock()

    async def store(self, content: CachedContent) -> None:
        async with self._lock:
            self._cache[content.uuid] = content

    async def get(self, uuid: str) -> Optional[CachedContent]:
        async with self._lock:
            return self._cache.get(uuid)

    async def update(self, uuid: str, content: CachedContent) -> None:
        async with self._lock:
            if uuid in self._cache:
                self._cache[uuid] = content

    async def delete(self, uuid: str) -> None:
        async with self._lock:
            self._cache.pop(uuid, None)

    async def list_all(self) -> List[CachedContent]:
        async with self._lock:
            return list(self._cache.values())


# ============================================================================
# Redis 缓存实现
# ============================================================================

class RedisCacheBackend(CacheBackend):
    """Redis 缓存后端实现"""

    def __init__(self, redis_url: str):
        if not REDIS_AVAILABLE:
            raise ImportError("redis[asyncio] 未安装，无法使用 Redis 缓存")

        self._redis = aioredis.from_url(redis_url, decode_responses=False)
        self._prefix = "curl_cffi_fetch:cache:"

    def _make_key(self, uuid: str) -> str:
        """生成 Redis key"""
        return f"{self._prefix}{uuid}"

    async def store(self, content: CachedContent) -> None:
        key = self._make_key(content.uuid)
        data = pickle.dumps(content)
        await self._redis.set(key, data)

    async def get(self, uuid: str) -> Optional[CachedContent]:
        key = self._make_key(uuid)
        data = await self._redis.get(key)
        if data:
            return pickle.loads(data)
        return None

    async def update(self, uuid: str, content: CachedContent) -> None:
        await self.store(content)

    async def delete(self, uuid: str) -> None:
        key = self._make_key(uuid)
        await self._redis.delete(key)

    async def list_all(self) -> List[CachedContent]:
        pattern = f"{self._prefix}*"
        keys = []
        async for key in self._redis.scan_iter(match=pattern):
            keys.append(key)

        if not keys:
            return []

        values = await self._redis.mget(keys)
        return [pickle.loads(v) for v in values if v]


# ============================================================================
# 缓存管理器
# ============================================================================

class ContentCacheManager:
    """内容缓存管理器"""

    def __init__(
        self,
        redis_url: str = "",
        ttl_seconds: int = 1800,
        delete_delay_seconds: int = 300
    ):
        """初始化缓存管理器

        参数：
            redis_url: Redis URL（配置后使用 Redis，否则使用内存缓存）
            ttl_seconds: 未读完缓存的 TTL（秒）
            delete_delay_seconds: 完全读取后延迟删除时间（秒）
        """
        # 根据 redis_url 自动选择后端
        if redis_url:
            self._backend = RedisCacheBackend(redis_url)
        else:
            self._backend = MemoryCacheBackend()

        self._ttl = ttl_seconds
        self._delete_delay = delete_delay_seconds
        self._encoding = tiktoken.get_encoding("cl100k_base")

    async def store(self, url: str, markdown: str) -> CachedContent:
        """存储内容并返回缓存条目

        参数：
            url: 原始 URL
            markdown: Markdown 内容

        返回：
            缓存条目
        """
        # 生成 UUID
        content_uuid = str(uuid.uuid4())

        # 计算 token 数和偏移表
        total_tokens = count_tokens(markdown, self._encoding)
        token_offsets = build_token_offsets(markdown, self._encoding)

        # 创建缓存条目
        now = time.time()
        content = CachedContent(
            uuid=content_uuid,
            url=url,
            markdown=markdown,
            total_tokens=total_tokens,
            token_offsets=token_offsets,
            created_at=now,
            accessed_at=now
        )

        # 存储到后端
        await self._backend.store(content)

        return content

    async def get_chunk(
        self,
        uuid: str,
        start_token: int,
        end_token: Optional[int] = None
    ) -> Tuple[Optional[str], bool, int]:
        """获取指定 token 区间的内容

        参数：
            uuid: 缓存 UUID
            start_token: 起始 token 位置
            end_token: 结束 token 位置（None 表示读到末尾）

        返回：
            (chunk_content, is_fully_read, actual_end_token)
            如果缓存不存在，返回 (None, False, 0)
        """
        # 获取缓存
        content = await self._backend.get(uuid)
        if not content:
            return None, False, 0

        # 更新访问时间
        content.accessed_at = time.time()

        # 处理 end_token
        if end_token is None:
            end_token = content.total_tokens

        # 边界检查
        start_token = max(0, start_token)
        end_token = min(end_token, content.total_tokens)

        if start_token >= end_token:
            return "", content.is_fully_read(), start_token

        # 切分内容
        chunk = slice_by_tokens(
            content.markdown,
            content.token_offsets,
            start_token,
            end_token
        )

        # 追踪已读区间
        content.read_ranges.add((start_token, end_token))

        # 检查是否完全读取
        is_fully_read = content.is_fully_read()
        if is_fully_read and content.fully_read_at is None:
            content.fully_read_at = time.time()

        # 更新缓存
        await self._backend.update(uuid, content)

        return chunk, is_fully_read, end_token

    async def cleanup_expired(self) -> int:
        """清理过期的未读完缓存

        返回：
            清理的缓存数量
        """
        now = time.time()
        all_contents = await self._backend.list_all()

        deleted_count = 0
        for content in all_contents:
            # 只清理未读完的缓存
            if not content.is_fully_read():
                # 检查是否超过 TTL
                if now - content.created_at > self._ttl:
                    await self._backend.delete(content.uuid)
                    deleted_count += 1

        return deleted_count

    async def cleanup_fully_read(self) -> int:
        """清理完全读取超过延迟时间的缓存

        返回：
            清理的缓存数量
        """
        now = time.time()
        all_contents = await self._backend.list_all()

        deleted_count = 0
        for content in all_contents:
            # 只清理已完全读取的缓存
            if content.fully_read_at is not None:
                # 检查是否超过延迟删除时间
                if now - content.fully_read_at > self._delete_delay:
                    await self._backend.delete(content.uuid)
                    deleted_count += 1

        return deleted_count
