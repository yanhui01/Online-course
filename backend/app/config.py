"""应用配置管理，使用 pydantic-settings 从环境变量/.env 加载配置"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "OnlineCourse"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-to-a-random-secret-key"

    # 数据库 - 可通过 DATABASE_URL 环境变量覆盖
    DATABASE_URL: str = ""
    # PostgreSQL（如果 DATABASE_URL 为空则使用以下配置）
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "online_course"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "change-me"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # JWT
    JWT_SECRET_KEY: str = "change-me-to-random-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 加密密钥 (AES, 用于平台账号密码)
    ENCRYPTION_KEY: str = "change-me-to-fernet-generated-key"

    # Playwright 浏览器自动化
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_BROWSER: str = "chromium"
    MAX_CONCURRENT_TASKS: int = 3

    # 题库匹配
    QUESTION_SIMILARITY_THRESHOLD: float = 0.75

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = {
        "env_file": os.environ.get("ENV_FILE", "../.env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()

