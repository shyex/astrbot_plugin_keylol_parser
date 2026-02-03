"""插件配置"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from pathlib import Path

class ParserItem(BaseModel):
    """单个解析器配置"""
    enable: bool = Field(default=True, description="是否启用")
    use_proxy: bool = Field(default=False, description="是否使用代理")
    cookies: Optional[str] = Field(default=None, description="Cookies")

class PluginConfig:
    """插件配置"""
    def __init__(self, config: Any = None, context: Any = None):
        # 从 AstrBot 配置中获取插件配置
        self._config = config
        self._context = context
        
        # 通用配置
        self.common_timeout = 30
        self.download_retry_times = 3
        self.proxy = None
        self.forward_threshold = 5
        self.show_download_fail_tip = True
        self.single_heavy_render_card = True
        
        # 缓存配置
        self.cache_dir = Path("data/cache")
        
        # Emoji 配置
        self.emoji_cdn = "https://cdn.jsdelivr.net/npm/twemoji@latest/assets/72x72/"
        self.emoji_style = "twitter"
        
        # 解析器配置
        self.parser = {
            "keylol": ParserItem(),
        }
        
        # 启用的会话列表
        self.enabled_sessions: List[str] = []
        
        # 从配置文件加载配置
        self._load_config()
    
    def _load_config(self):
        """从配置文件加载配置"""
        # 这里可以添加从配置文件加载配置的逻辑
        pass
    
    def save_config(self):
        """保存配置到文件"""
        # 这里可以添加保存配置到文件的逻辑
        pass
    
    def __getitem__(self, key: str) -> Any:
        """支持通过字典方式访问配置"""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return getattr(self, key, default)
