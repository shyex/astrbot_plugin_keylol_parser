"""下载模块"""

import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, Union
import os
import tempfile

from .exception import DownloadException, DownloadLimitException, SizeLimitException, ZeroSizeException

class Downloader:
    """下载器"""
    
    def __init__(self, config):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        # 确保缓存目录存在
        Path(self.config.cache_dir).mkdir(parents=True, exist_ok=True)
    
    async def get_session(self) -> aiohttp.ClientSession:
        """获取会话"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.common_timeout)
            )
        return self.session
    
    async def download_file(
        self, 
        url: str, 
        headers: Optional[dict] = None, 
        file_name: Optional[str] = None,
        proxy: Optional[str] = None
    ) -> Path:
        """下载文件"""
        session = await self.get_session()
        
        # 生成文件名
        if not file_name:
            file_name = url.split("/")[-1]
        
        # 创建缓存文件
        cache_file = Path(self.config.cache_dir) / file_name
        
        # 下载文件
        retries = self.config.download_retry_times
        for attempt in range(retries + 1):
            try:
                async with session.get(url, headers=headers, proxy=proxy) as response:
                    response.raise_for_status()
                    
                    # 检查文件大小
                    content_length = response.headers.get("Content-Length")
                    if content_length:
                        size = int(content_length)
                        if size == 0:
                            raise ZeroSizeException(f"文件大小为0: {url}")
                        # 这里可以添加大小限制检查
                    
                    with open(cache_file, "wb") as f:
                        async for chunk in response.content:
                            f.write(chunk)
                    
                    # 检查下载后的文件大小
                    if cache_file.stat().st_size == 0:
                        raise ZeroSizeException(f"下载的文件大小为0: {url}")
                    
                    return cache_file
            except Exception as e:
                if attempt < retries:
                    await asyncio.sleep(1 + attempt)
                    continue
                if isinstance(e, aiohttp.ClientResponseError) and e.status == 429:
                    raise DownloadLimitException(f"下载限制: {url}")
                raise DownloadException(f"下载失败: {str(e)}")
    
    async def download_img(
        self, 
        url: str, 
        headers: Optional[dict] = None,
        proxy: Optional[str] = None
    ) -> Path:
        """下载图片"""
        return await self.download_file(url, headers=headers, proxy=proxy)
    
    async def download_video(
        self, 
        url: str, 
        headers: Optional[dict] = None,
        proxy: Optional[str] = None
    ) -> Path:
        """下载视频"""
        return await self.download_file(url, headers=headers, proxy=proxy)
    
    async def download_audio(
        self, 
        url: str, 
        headers: Optional[dict] = None,
        proxy: Optional[str] = None
    ) -> Path:
        """下载音频"""
        return await self.download_file(url, headers=headers, proxy=proxy)
    
    async def close(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()
