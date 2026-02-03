"""
AstrBot 插件 - 其乐论坛解析器

解析其乐论坛帖子链接，将内容渲染为图片卡片并发送到群聊
"""

import asyncio
from pathlib import Path
from typing import Optional

from astrbot import Star
from astrbot.core.config import ConfigManager
from astrbot.core.filter import filter
from astrbot.core.message import MessageChain
from astrbot.core.plugin import PluginConfig

from .core.config import CONFIG
from .core.parsers import get_all_parsers
from .core.render import Renderer
from .core.sender import Sender
from .core.download import Downloader


class KeylolParserPlugin(Star):
    """其乐论坛解析器插件"""

    def __init__(self):
        super().__init__()
        self.name = "astrbot_plugin_keylol_parser"
        self.display_name = "其乐论坛解析器"
        self.description = "解析其乐论坛帖子链接，将内容渲染为图片卡片并发送到群聊"

        # 模块实例
        self.config_manager: Optional[ConfigManager] = None
        self.config: Optional[PluginConfig] = None
        self.downloader: Optional[Downloader] = None
        self.renderer: Optional[Renderer] = None
        self.sender: Optional[Sender] = None
        self.parsers = []

    async def initialize(self):
        """初始化插件"""
        # 获取配置管理器
        self.config_manager = self.bot.config_manager

        # 加载插件配置
        self.config = await self.config_manager.get_plugin_config(self.name, CONFIG)

        # 确保缓存目录存在
        cache_dir = Path(self.config.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        # 初始化下载器
        self.downloader = Downloader(self.config)

        # 初始化渲染器并加载资源
        self.renderer = Renderer(self.config)
        Renderer.load_resources()

        # 初始化发送器
        self.sender = Sender(self.config, self.renderer)

        # 初始化解析器
        self.parsers = get_all_parsers(self.config, self.downloader)

        # 注册消息处理器
        self.register_message_handler()

        self.logger.info(f"{self.display_name} 插件初始化完成")

    async def terminate(self):
        """终止插件"""
        # 清理下载器
        if self.downloader:
            await self.downloader.close()

        self.logger.info(f"{self.display_name} 插件已终止")

    def register_message_handler(self):
        """注册消息处理器"""

        @filter.event_message_type("GroupMessage")
        async def handle_group_message(event):
            """处理群消息"""
            msg = event.message
            if not msg:
                return

            # 获取消息文本
            msg_text = msg.extract_plain_text().strip()
            if not msg_text:
                return

            # 尝试解析消息中的链接
            for parser in self.parsers:
                try:
                    keyword, searched = parser.search_url(msg_text)
                    result = await parser.parse(keyword, searched)
                    if result:
                        # 发送解析结果
                        await self.sender.send_parse_result(event, result)
                        break
                except Exception:
                    # 解析失败，继续尝试下一个解析器
                    continue


# 插件导出
__star__ = KeylolParserPlugin
