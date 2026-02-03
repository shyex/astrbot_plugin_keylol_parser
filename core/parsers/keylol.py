import re
from typing import ClassVar

from aiohttp import ClientError
from bs4 import BeautifulSoup, Tag

from ..config import PluginConfig
from ..download import Downloader
from ..exception import ParseException
from .base import BaseParser, Platform, handle


class KeylolParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name="keylol", display_name="其乐")

    def __init__(self, config: PluginConfig, downloader: Downloader):
        super().__init__(config, downloader)
        extra_headers = {
            "Referer": "https://keylol.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.headers.update(extra_headers)
        
        # 获取配置文件中的cookies
        parser_cfg = self.cfg.parser.get("keylol", {})
        self.keylol_ck = parser_cfg.get("cookies", "")
        
        if self.keylol_ck:
            self.headers["Cookie"] = self.keylol_ck

    @staticmethod
    def keylol_url(tid: str | int) -> str:
        return f"https://keylol.com/t{tid}"

    @handle("keylol.com", r"(?:https?://)?keylol\.com/t(?P<tid>\d+)(?:-\d+-\d+)?")
    async def _parse(self, searched: re.Match[str]):
        # 从匹配对象中获取URL部分
        url_part = searched.group(0)
        # 构建完整URL
        if not url_part.startswith("http"):
            url = f"https://{url_part}"
        else:
            url = url_part
        
        async with self.session.get(url, headers=self.headers, allow_redirects=True, proxy=self.proxy) as resp:
            if resp.status != 200:
                raise ParseException(f"无法获取页面, HTTP {resp.status}")
            html = await resp.text()

        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(html, "html.parser")

        # 提取标题
        title = None
        title_tag = soup.find("a", id="thread_subject")
        if title_tag and isinstance(title_tag, Tag):
            title = title_tag.get_text(strip=True)

        # 提取作者
        author = None
        author_tag = soup.find("a", class_="xw1", href=re.compile(r"suid-\d+"))
        if author_tag and isinstance(author_tag, Tag):
            author_name = author_tag.get_text(strip=True)
            author = self.create_author(author_name)

        # 提取时间
        timestamp = None
        time_tag = soup.find("em", id=re.compile(r"authorposton\d+"))
        if time_tag and isinstance(time_tag, Tag):
            time_span = time_tag.find("span", title=re.compile(r"\d{4}-\d{1,2}-\d{1,2} \d{2}:\d{2}:\d{2}"))
            if time_span and isinstance(time_span, Tag):
                timestr = time_span.get("title", "")
                if timestr:
                    # 转换时间格式，其乐论坛的时间格式：2026-1-17 19:49:33
                    try:
                        import time as time_module
                        timestamp = int(time_module.mktime(time_module.strptime(timestr, "%Y-%m-%d %H:%M:%S")))
                    except ValueError:
                        pass

        # 提取帖子内容
        text = None
        content_tag = soup.find("td", class_="t_f", id=re.compile(r"postmessage_\d+"))
        img_urls = []
        if content_tag and isinstance(content_tag, Tag):
            # 提取文本内容，清理HTML标签
            text = content_tag.get_text("\n", strip=True)
            text = self.clean_keylol_text(text)
            
            # 提取图片，过滤广告图片
            img_tags = content_tag.find_all("img")
            for img in img_tags:
                if isinstance(img, Tag):
                    img_url = img.get("src", "")
                    
                    # 检查是否为附件形式的图片（使用占位符）
                    if img_url == "static/image/common/none.gif":
                        # 从file属性获取实际图片URL
                        file_url = img.get("file", "")
                        # 从zoomfile属性获取实际图片URL
                        zoom_url = img.get("zoomfile", "")
                        # 优先使用file属性
                        if file_url and file_url.startswith("http"):
                            img_url = file_url
                        elif zoom_url and zoom_url.startswith("http"):
                            img_url = zoom_url
                    
                    # 检查是否为广告图片
                    is_ad = False
                    
                    # 1. 检查图片URL是否包含广告特征
                    if any(ad_keyword in img_url.lower() for ad_keyword in ["ad", "advertisement", "banner"]):
                        is_ad = True
                    
                    # 2. 检查图片是否被包裹在广告链接中（指向https://keylol.com/hello/）
                    if img.parent and img.parent.name == "a":
                        parent_href = img.parent.get("href", "")
                        if parent_href.startswith("https://keylol.com/hello/"):
                            is_ad = True
                    
                    # 3. 检查图片是否没有aid属性且非附件图片（通常是广告）
                    if not img.get("aid") and img_url != "static/image/common/none.gif":
                        # 检查尺寸是否为广告常见尺寸（120x240）
                        width = img.get("width")
                        height = img.get("height")
                        if width == "120" and height == "240":
                            is_ad = True
                    
                    # 只添加非广告图片
                    if img_url and img_url.startswith("http") and not is_ad:
                        img_urls.append(img_url)
        
        # 创建媒体内容
        contents = []
        if img_urls:
            # 使用GraphicsContent替代ImageContent，这样会将图片和文字一起渲染在卡片上
            for i, img_url in enumerate(img_urls):
                # 为每张图片添加简短描述
                img_alt = f"图片{i+1}"
                # 使用图片前的文本作为图片描述
                img_text = text if i == 0 else None
                # 创建图文内容
                content = self.create_graphics_content(
                    img_url,
                    text=img_text,
                    alt=img_alt
                )
                contents.append(content)
        elif text:
            # 如果没有图片但有文本，创建一个包含文本的内容
            # 这里我们可以创建一个简单的图文内容，或者直接在解析结果中设置text
            pass

        return self.result(
            title=title,
            text=text,
            url=url,
            author=author,
            contents=contents,
            timestamp=timestamp,
        )

    @staticmethod
    def clean_keylol_text(text: str, max_length: int = 500) -> str:
        rules: list[tuple[str, str, int]] = [
            # 移除引用标签内容
            (r"引用.*?：", "", re.DOTALL),
            (r"查看附件.*?", "", re.DOTALL),
            # 移除Steam功能链接文本
            (r"Steam商店.*?复制ASF代码", "", re.DOTALL),
            (r"Steam商店", "", 0),
            (r"Steam评测区", "", 0),
            (r"其乐相关帖", "", 0),
            (r"SteamDB", "", 0),
            (r"AStats", "", 0),
            (r"SCE", "", 0),
            (r"Barter", "", 0),
            (r"Steam客户端中查看", "", 0),
            (r"入库或安装", "", 0),
            (r"复制ASF代码", "", 0),
            # 移除开头的版权声明文本
            (r"本文为.*?严禁转载", "", re.DOTALL),
            # 移除图片文件名及相关参数
            (r"[a-zA-Z0-9_]+\.(jpg|jpeg|png|gif|bmp|webp)", "", 0),  # 图片文件名
            (r"\(\d+(?:\.\d+)? KB, 下载次数: \d+\)", "", 0),  # 图片大小和下载次数（支持带小数点和不带小数点两种格式）
            (r"下载附件", "", 0),  # 下载附件文本
            (r"\d+\s+小时前", "", 0),  # 上传时间
            (r"上传", "", 0),  # 上传文本
            # 清理空白字符
            (r"\n{3,}", "\n\n", 0),  # 多个换行符压缩为两个
            (r"[ \t]+", " ", 0),  # 多个空格/制表符压缩为一个空格
            (r"\n\s+\n", "\n\n", 0),  # 清理空行中的空白字符
            (r"[|]+\s*", "", 0),  # 清理多余的竖线符号
            (r"^\s+", "", 0),  # 清理开头的空白字符
            (r"\s+$", "", 0),  # 清理结尾的空白字符
        ]

        for rule in rules:
            pattern, replacement, flags = rule[0], rule[1], rule[2]
            text = re.sub(pattern, replacement, text, flags=flags)

        text = text.strip()

        # 限制文本长度
        if len(text) > max_length:
            text = text[:max_length] + "..."

        return text
