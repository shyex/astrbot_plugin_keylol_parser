"""keylol-parser 插件主入口"""

import asyncio
import re

from astrbot.api import logger
from astrbot.api.event import filter
from astrbot.api.star import Context, Star
from astrbot.core import AstrBotConfig
from astrbot.core.platform.astr_message_event import AstrMessageEvent

from .core.config import PluginConfig
from .core.parsers import get_all_parsers
from .core.data import ParseResult
from .core.download import Downloader
from .core.exception import ParseException
from .core.render import Renderer
from .core.sender import MessageSender


class KeylolParserPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.cfg = PluginConfig(config, context=context)
        
        # 下载器
        self.downloader = Downloader(self.cfg)
        
        # 解析器
        self.parsers = get_all_parsers(self.cfg, self.downloader)
        
        # 渲染器
        self.renderer = Renderer(self.cfg)
        
        # 消息发送器
        self.sender = MessageSender(self.cfg, self.renderer)
        
        # 关键词 -> 正则 列表
        self.key_pattern_list: list[tuple[str, re.Pattern[str]]] = []
        
        # 关键词 -> Parser 映射
        self.parser_map: dict[str, BaseParser] = {}  # 注意：这里需要导入 BaseParser

    async def initialize(self):
        """加载、重载插件时触发"""
        # 加载渲染器资源
        await asyncio.to_thread(self.renderer.load_resources)
        # 注册解析器
        self._register_parser()

    async def terminate(self):
        """插件卸载时触发"""
        # 关下载器里的会话
        await self.downloader.close()
        # 关所有解析器里的会话
        for parser in self.parsers:
            await parser.close_session()

    def _register_parser(self):
        """注册解析器"""
        from .core.parsers.base import BaseParser
        
        # 所有 Parser 子类
        all_subclass = BaseParser.get_all_subclass()
        
        enabled_classes: list[type[BaseParser]] = []
        enabled_names: list[str] = []
        
        for cls in all_subclass:
            platform_name = cls.platform.name
            enabled_classes.append(cls)
            enabled_names.append(platform_name)
            
            # 一个平台一个 parser 实例
            parser = cls(self.cfg, self.downloader)
            
            # 关键词 → parser
            for keyword, _ in cls._key_patterns:
                self.parser_map[keyword] = parser
        
        logger.debug(f"启用平台: {'、'.join(enabled_names) if enabled_names else '无'}")
        
        # -------- 关键词-正则表（统一生成） --------
        patterns: list[tuple[str, re.Pattern[str]]] = []
        
        for cls in enabled_classes:
            for kw, pat in cls._key_patterns:
                patterns.append((kw, re.compile(pat) if isinstance(pat, str) else pat))
        
        # 长关键词优先，避免短词抢匹配
        patterns.sort(key=lambda x: -len(x[0]))
        
        self.key_pattern_list = patterns
        
        logger.debug(f"[parser] 关键词-正则对已生成: {[kw for kw, _ in patterns]}")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """消息的统一入口"""
        umo = event.unified_msg_origin
        
        # 消息链
        chain = event.get_messages()
        if not chain:
            return
        
        text = event.message_str
        
        if not text:
            return
        
        # 核心匹配逻辑 ：关键词 + 正则双重判定，汇集了所有解析器的正则对。
        keyword: str = ""
        searched: re.Match[str] | None = None
        for kw, pat in self.key_pattern_list:
            if kw not in text:
                continue
            if m := pat.search(text):
                keyword, searched = kw, m
                break
        if searched is None:
            return
        logger.debug(f"匹配结果: {keyword}, {searched}")
        
        # 解析
        try:
            parse_res = await self.parser_map[keyword].parse(keyword, searched)
            # 发送
            await self.sender.send_parse_result(event, parse_res)
        except Exception as e:
            logger.error(f"解析错误: {str(e)}")
            return
