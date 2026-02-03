"""数据结构定义"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TypedDict, Union
from asyncio import Task
from pathlib import Path

from pydantic import BaseModel


class Platform:
    """平台信息"""

    def __init__(self, name: str, display_name: str):
        self.name = name
        self.display_name = display_name

    def __str__(self):
        return self.display_name


@dataclass
class Author:
    """作者信息"""

    name: Optional[str] = None
    avatar: Optional[Task[Path]] = None
    description: Optional[str] = None


@dataclass
class ParseResult:
    """解析结果"""

    platform: Platform
    title: Optional[str] = None
    text: Optional[str] = None
    url: Optional[str] = None
    author: Optional[Author] = None
    contents: List["Content"] = field(default_factory=list)
    timestamp: Optional[int] = None
    repost: Optional["ParseResult"] = None

    def get_resource_id(self) -> str:
        """获取资源ID，用于防抖"""
        # 基于平台和URL生成唯一标识
        if self.url:
            return f"{self.platform.name}:{self.url}"
        # 基于平台和标题生成唯一标识
        if self.title:
            return f"{self.platform.name}:{self.title}"
        # 基于平台和时间戳生成唯一标识
        if self.timestamp:
            return f"{self.platform.name}:{self.timestamp}"
        # 基于平台和内容生成唯一标识
        if self.contents:
            return f"{self.platform.name}:{len(self.contents)}"
        # 生成随机标识
        import uuid
        return f"{self.platform.name}:{uuid.uuid4().hex}"


class Content:
    """内容基类"""

    def __init__(self, path: Union[str, Task[Path]]):
        self.path: Union[str, Task[Path]] = path

    async def get_path(self) -> Path:
        """获取路径"""
        if isinstance(self.path, Task):
            return await self.path
        return Path(self.path)


@dataclass
class ImageContent(Content):
    """图片内容"""

    pass


@dataclass
class VideoContent(Content):
    """视频内容"""

    cover: Optional[Task[Path]] = None
    duration: float = 0.0


@dataclass
class AudioContent(Content):
    """音频内容"""

    duration: float = 0.0


@dataclass
class DynamicContent(Content):
    """动态图片内容"""

    pass


@dataclass
class FileContent(Content):
    """文件内容"""

    pass


@dataclass
class GraphicsContent(Content):
    """图文内容"""

    text: Optional[str] = None
    alt: Optional[str] = None
