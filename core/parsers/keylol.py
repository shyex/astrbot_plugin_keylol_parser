"""其乐论坛解析器"""

import asyncio
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup

from ..config import PluginConfig
from ..data import (
    Author,
    ImageContent,
    MediaContent,
    ParseResult,
    ParseResultKwargs,
    Platform,
)
from ..download import Downloader
from .base import BaseParser


class KeylolParser(BaseParser):
    """其乐论坛解析器"""

    def __init__(self, config: PluginConfig, downloader: Downloader):
        super().__init__(config, downloader)
        self.platform = Platform(name="keylol", display_name="其乐论坛")
        # 添加请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        # 添加 cookies（如果有）
        if config.parser.get("keylol", {}).get("cookies"):
            self.headers["Cookie"] = config.parser["keylol"]["cookies"]

    @BaseParser.handle("keylol.com", r"(?:https?://)?keylol\.com/t(?P<tid>\d+)(?:-\d+-\d+)?")
    async def _parse(self, searched: re.Match[str]) -> ParseResult:
        """解析其乐论坛帖子"""
        url = self._build_url(searched)
        async with self.session.get(url, headers=self.headers) as resp:
            html = await resp.text()
        soup = BeautifulSoup(html, "html.parser")

        # 提取标题
        title = self._extract_title(soup)
        # 提取作者
        author = self._extract_author(soup)
        # 提取发布时间
        timestamp = self._extract_timestamp(soup)
        # 提取帖子内容
        text, images = self._extract_content(soup)

        # 下载图片
        contents = await self._download_images(images)

        # 构建解析结果
        return self.result(
            title=title,
            author=author,
            timestamp=timestamp,
            text=text,
            url=url,
            contents=contents,
        )

    def _build_url(self, searched: re.Match[str]) -> str:
        """构建完整的帖子 URL"""
        tid = searched.group("tid")
        return f"https://keylol.com/t{tid}-1-1"

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """提取帖子标题"""
        title_tag = soup.find("h1", class_="ts")
        if title_tag:
            return title_tag.text.strip()
        return None

    def _extract_author(self, soup: BeautifulSoup) -> Optional[Author]:
        """提取作者信息"""
        author_tag = soup.find("div", class_="authi").find("a", class_="xw1")
        if author_tag:
            author_name = author_tag.text.strip()
            return Author(name=author_name)
        return None

    def _extract_timestamp(self, soup: BeautifulSoup) -> Optional[int]:
        """提取发布时间"""
        time_tag = soup.find("div", class_="authi").find("em")
        if time_tag:
            # 这里需要根据实际的时间格式进行解析
            # 暂时返回 None，实际使用时需要实现
            return None
        return None

    def _extract_content(self, soup: BeautifulSoup) -> Tuple[Optional[str], List[str]]:
        """提取帖子内容和图片"""
        content_tag = soup.find("td", class_="t_f")
        if not content_tag:
            return None, []

        # 提取文本内容（去除标签）
        text = content_tag.get_text(separator="\n", strip=True)

        # 提取图片链接
        images = []
        for img_tag in content_tag.find_all("img"):
            img_url = img_tag.get("src")
            if img_url:
                # 过滤广告图片
                if not self._is_ad_image(img_tag, img_url):
                    images.append(img_url)

        return text, images

    def _is_ad_image(self, img_tag: Any, img_url: str) -> bool:
        """判断是否为广告图片"""
        # 过滤掉明显的广告图片 URL
        ad_keywords = ["ad", "advertisement", "banner", "promotion"]
        if any(keyword in img_url.lower() for keyword in ad_keywords):
            return True

        # 过滤掉小尺寸图片（可能是表情或图标）
        width = img_tag.get("width", "")
        height = img_tag.get("height", "")
        if width and height:
            try:
                if int(width) < 100 or int(height) < 100:
                    return True
            except ValueError:
                pass

        # 过滤掉特定路径的图片
        if "static/image/common" in img_url:
            return True

        return False

    async def _download_images(self, image_urls: List[str]) -> List[MediaContent]:
        """下载图片"""
        contents = []
        for url in image_urls:
            # 确保 URL 完整
            if not url.startswith("http"):
                url = f"https://keylol.com{url}"

            # 下载图片
            try:
                task = asyncio.create_task(self.downloader.download(url))
                contents.append(ImageContent(path_task=task))
            except Exception as e:
                print(f"下载图片失败: {e}")

        return contents

    def result(self, **kwargs: ParseResultKwargs) -> ParseResult:
        """构建解析结果"""
        return ParseResult(platform=self.platform, **kwargs)
