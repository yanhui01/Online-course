"""适配器工厂"""

from app.adapters.base import BasePlatformAdapter
from app.adapters.icve import IcveAdapter
from app.adapters.zhihuishu import ZhihuishuAdapter
from app.adapters.xuetangx import XuetangxAdapter


def get_adapter(platform: str, username: str, password: str, headless: bool = True) -> BasePlatformAdapter:
    """根据平台名创建对应的适配器实例"""
    adapter_map = {
        "icve": IcveAdapter,
        "zhihuishu": ZhihuishuAdapter,
        "xuetangx": XuetangxAdapter,
    }

    adapter_cls = adapter_map.get(platform)
    if adapter_cls is None:
        raise ValueError(f"不支持的平台: {platform}，可选: {list(adapter_map.keys())}")

    return adapter_cls(username=username, password=password, headless=headless)
