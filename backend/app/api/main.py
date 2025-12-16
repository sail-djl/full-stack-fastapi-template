from fastapi import APIRouter

from app.api.routes import items, login, menu, private, roles, scheduler, users, utils, polarization, etf, fund
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(menu.router)
api_router.include_router(roles.router)
api_router.include_router(polarization.router)
api_router.include_router(etf.router)
api_router.include_router(fund.router)
api_router.include_router(scheduler.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
