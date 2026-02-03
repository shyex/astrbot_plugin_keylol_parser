"""渲染模块"""

import asyncio
import math
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .data import Author, MediaContent, ParseResult


class Renderer:
    """
    渲染器

    职责：
    - 渲染解析结果为图片卡片
    - 管理字体、emoji 等资源
    """

    # 字体缓存
    _font_cache: Dict[str, ImageFont.FreeTypeFont] = {}
    # 字体路径
    _font_path: Optional[Path] = None
    # Emoji 缓存
    _emoji_cache: Dict[str, Image] = {}

    def __init__(self, config):
        self.cfg = config
        self.cache_dir = Path(config.cache_dir)
        self.emoji_cdn = config.emoji_cdn
        self.emoji_style = config.emoji_style

    @classmethod
    def load_resources(cls):
        """
        加载渲染资源

        目前需要：
        - 字体
        """
        # 字体路径
        font_path = Path("data\resources\fonts\HYSongYunLangHeiW-1.ttf")
        if font_path.exists():
            cls._font_path = font_path
        else:
            # 尝试其他字体路径
            font_paths = [
                Path("C:\\Windows\\Fonts\\simhei.ttf"),  # 黑体
                Path("C:\\Windows\\Fonts\\simsun.ttc"),  # 宋体
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                Path("/usr/share/fonts/truetype/arphic/ukai.ttc"),
                Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
            ]
            for path in font_paths:
                if path.exists():
                    cls._font_path = path
                    break

    @classmethod
    def get_font(cls, size: int) -> ImageFont.FreeTypeFont:
        """
        获取字体

        Args:
            size: 字体大小

        Returns:
            字体对象
        """
        key = f"{cls._font_path}_{size}"
        if key not in cls._font_cache:
            try:
                if cls._font_path:
                    cls._font_cache[key] = ImageFont.truetype(str(cls._font_path), size)
                else:
                    # 使用默认字体
                    cls._font_cache[key] = ImageFont.load_default()
            except Exception:
                # 使用默认字体
                cls._font_cache[key] = ImageFont.load_default()
        return cls._font_cache[key]

    async def render_card(self, result: ParseResult) -> Path | None:
        """
        渲染卡片

        Args:
            result: 解析结果

        Returns:
            渲染后的图片路径
        """
        cache = self.cache_dir / f"card_{result.get_resource_id().replace(':', '_')}.png"
        cache.parent.mkdir(parents=True, exist_ok=True)

        try:
            img = await self._create_card_image(result)
            buf = BytesIO()
            await asyncio.to_thread(img.save, buf, format="PNG")
            async with aiofiles.open(cache, "wb") as fp:
                await fp.write(buf.getvalue())
            return cache
        except Exception as e:
            print(f"渲染卡片失败: {str(e)}")
            return None

    async def _create_card_image(self, result: ParseResult) -> Image.Image:
        """
        创建卡片图片

        Args:
            result: 解析结果

        Returns:
            卡片图片
        """
        # 计算卡片大小
        width = 800
        height = 600

        # 创建画布
        img = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        # 绘制边框
        draw.rectangle([(0, 0), (width - 1, height - 1)], outline=(200, 200, 200), width=2)

        # 绘制平台信息
        platform_font = self.get_font(16)
        draw.text((20, 10), f"平台: {result.platform}", fill=(100, 100, 100), font=platform_font)

        # 绘制标题
        if result.title:
            title_font = self.get_font(24)
            title_text = result.title
            # 文本换行
            title_lines = self._wrap_text(title_text, title_font, width - 40)
            y_offset = 40
            for line in title_lines:
                draw.text((20, y_offset), line, fill=(0, 0, 0), font=title_font)
                y_offset += 30
        else:
            y_offset = 40

        # 绘制作者信息
        if result.author and result.author.name:
            author_font = self.get_font(14)
            draw.text((20, y_offset), f"作者: {result.author.name}", fill=(100, 100, 100), font=author_font)
            y_offset += 20

        # 绘制时间信息
        if result.timestamp:
            time_font = self.get_font(14)
            import datetime
            time_str = datetime.datetime.fromtimestamp(result.timestamp).strftime("%Y-%m-%d %H:%M:%S")
            draw.text((20, y_offset), f"时间: {time_str}", fill=(100, 100, 100), font=time_font)
            y_offset += 20

        # 绘制文本内容
        if result.text:
            text_font = self.get_font(16)
            text_text = result.text
            # 文本换行
            text_lines = self._wrap_text(text_text, text_font, width - 40)
            # 限制行数
            max_lines = 10
            if len(text_lines) > max_lines:
                text_lines = text_lines[:max_lines]
                text_lines.append("...")
            for line in text_lines:
                draw.text((20, y_offset), line, fill=(50, 50, 50), font=text_font)
                y_offset += 20
        else:
            y_offset += 10

        # 绘制链接信息
        if result.url:
            url_font = self.get_font(12)
            url_text = result.url
            # 文本换行
            url_lines = self._wrap_text(url_text, url_font, width - 40)
            for line in url_lines:
                draw.text((20, y_offset), line, fill=(0, 0, 255), font=url_font)
                y_offset += 15

        # 调整图片大小
        img = img.crop((0, 0, width, y_offset + 20))

        return img

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """
        文本换行

        Args:
            text: 文本
            font: 字体
            max_width: 最大宽度

        Returns:
            换行后的文本列表
        """
        lines = []
        current_line = ""
        for char in text:
            test_line = current_line + char
            # 计算文本宽度
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            if width > max_width:
                lines.append(current_line)
                current_line = char
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)
        return lines


# 导入 aiofiles
import aiofiles
