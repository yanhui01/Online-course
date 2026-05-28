"""人类行为模拟工具 — 随机延迟、鼠标轨迹等"""

import random
import asyncio


def random_delay(base_ms: float = 500, variance_ms: float = 300) -> float:
    """
    生成随机延迟（毫秒），使用正态分布模拟人类操作间隔
    base_ms: 基础等待时间
    variance_ms: 方差
    """
    delay = random.gauss(base_ms, variance_ms)
    return max(100, delay) / 1000  # 返回秒，最少 100ms


async def human_wait(base_ms: float = 500, variance_ms: float = 300):
    """随机等待"""
    await asyncio.sleep(random_delay(base_ms, variance_ms))


def random_viewport() -> dict:
    """随机化视口大小，模拟不同屏幕"""
    widths = [1366, 1440, 1536, 1920]
    heights = [768, 900, 864, 1080]
    idx = random.randint(0, len(widths) - 1)
    return {"width": widths[idx], "height": heights[idx]}


def random_user_agent() -> str:
    """随机选择一个常见 User-Agent"""
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    return random.choice(agents)


def typing_delay_per_char() -> float:
    """模拟逐字符输入延迟（秒/字符）"""
    return random.gauss(0.08, 0.03)
