"""FastAPI 公共依赖"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
