"""发送模块"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .data import MediaContent, ParseResult
from .render import Renderer


class Sender:
    """
    发送器

    职责：
    - 发送解析结果
    - 管理发送计划
    """

    def __init__(self, config, renderer: Renderer):
        self.cfg = config
        self.renderer = renderer

    async def send_parse_result(self, event, result: ParseResult):
        """
        发送解析结果

        Args:
            event: 事件对象
            result: 解析结果
        """
        # 构建发送计划
        plan = self._build_send_plan(result)

        # 发送预览卡片
        await self._send_preview_card(event, result, plan)

        # 构建消息段
        segs = await self._build_segments(result, plan)

        # 合并消息段（如果需要）
        segs = self._merge_segments_if_needed(event, segs, plan["force_merge"])

        # 发送消息段
        if segs:
            for seg in segs:
                await event.send(seg)

    def _build_send_plan(self, result: ParseResult) -> Dict[str, bool]:
        """
        构建发送计划

        Args:
            result: 解析结果

        Returns:
            发送计划
        """
        plan = {
            "send_preview": True,
            "send_contents": True,
            "force_merge": False,
        }

        # 根据内容类型和数量调整发送计划
        if len(result.contents) > self.cfg.forward_threshold:
            plan["force_merge"] = True

        return plan

    async def _send_preview_card(self, event, result: ParseResult, plan: Dict[str, bool]):
        """
        发送预览卡片

        Args:
            event: 事件对象
            result: 解析结果
            plan: 发送计划
        """
        if not plan["send_preview"]:
            return

        # 渲染预览卡片
        card_path = await self.renderer.render_card(result)
        if card_path:
            # 发送卡片
            from astrbot.core.message import MessageSegment
            seg = MessageSegment.image(path=str(card_path))
            await event.send(seg)

    async def _build_segments(self, result: ParseResult, plan: Dict[str, bool]) -> List:
        """
        构建消息段

        Args:
            result: 解析结果
            plan: 发送计划

        Returns:
            消息段列表
        """
        segs = []

        if plan["send_contents"]:
            for content in result.contents:
                seg = await self._build_segment(content)
                if seg:
                    segs.append(seg)

        return segs

    async def _build_segment(self, content: MediaContent) -> Optional:
        """
        构建单个消息段

        Args:
            content: 媒体内容

        Returns:
            消息段
        """
        from astrbot.core.message import MessageSegment

        path = await content.get_path()
        if isinstance(content, MediaContent):
            return MessageSegment.image(path=str(path))
        return None

    def _merge_segments_if_needed(self, event, segs: List, force_merge: bool) -> List:
        """
        合并消息段（如果需要）

        Args:
            event: 事件对象
            segs: 消息段列表
            force_merge: 是否强制合并

        Returns:
            合并后的消息段列表
        """
        if not force_merge and len(segs) <= 1:
            return segs

        # 构建合并转发
        from astrbot.core.message import MessageChain, MessageSegment

        merged = []
        for seg in segs:
            merged.append({
                "type": "node",
                "data": {
                    "name": "机器人",
                    "uin": "123456",
                    "content": MessageChain([seg])
                }
            })

        return [MessageSegment.forward(node_list=merged)]
