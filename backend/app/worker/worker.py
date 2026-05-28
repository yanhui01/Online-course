"""ARQ Worker 启动配置"""

from arq.connections import RedisSettings

from app.config import settings
from app.worker.jobs import execute_task

arq_redis_settings = RedisSettings(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    database=settings.REDIS_DB,
)


class WorkerSettings:
    """ARQ Worker 配置类"""
    functions = [execute_task]
    redis_settings = arq_redis_settings
    max_jobs = settings.MAX_CONCURRENT_TASKS
    job_timeout = 3600 * 8  # 单个任务最长 8 小时
    keep_result = 3600
    poll_delay = 0.5
