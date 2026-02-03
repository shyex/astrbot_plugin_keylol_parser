"""插件配置"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from pathlib import Path

class ParserItem(BaseModel):
    """单个解析器配置"""
    enable: bool = Field(default=True, description="是否启用")
    use_proxy: bool = Field(default=False, description="是否使用代理")
    cookies: Optional[str] = Field(default=None, description="Cookies")

# 配置模板
CONFIG = {
    "common_timeout": 30,
    "download_retry_times": 3,
    "proxy": None,
    "forward_threshold": 5,
    "show_download_fail_tip": True,
    "single_heavy_render_card": True,
    "cache_dir": "data/cache",
    "emoji_cdn": "https://cdn.jsdelivr.net/npm/twemoji@latest/assets/72x72/",
    "emoji_style": "twitter",
    "parser": {
        "keylol": {
            "enable": True,
            "use_proxy": False,
            "cookies": None
        }
    },
    "enabled_sessions": []
}
