"""解析器模块"""

from .base import BaseParser
from .keylol import KeylolParser


def get_all_parsers(config, downloader):
    """获取所有解析器实例"""
    return [
        KeylolParser(config, downloader),
    ]
