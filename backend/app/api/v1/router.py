"""v1 API 路由聚合"""

from fastapi import APIRouter

from app.api.v1 import auth, courses, platform_accounts, questions, tasks, users, ws

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(platform_accounts.router)
router.include_router(courses.router)
router.include_router(tasks.router)
router.include_router(questions.router)
router.include_router(ws.router)
