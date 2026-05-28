"""FastAPI 应用入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings
from app.core.database import Base, engine
from app.core.redis import close_redis, get_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动：创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 预热 Redis 连接
    await get_redis()
    yield
    # 关闭：释放连接
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="OnlineCourse - 多平台网课助手",
    description="统一管理智慧职教、知到、学堂在线的网课自动刷课",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(v1_router)


@app.get("/", tags=["健康检查"])
async def root():
    return {"status": "ok", "app": settings.APP_NAME, "version": "0.1.0"}
