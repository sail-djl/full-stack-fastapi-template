from fastapi import APIRouter

from app.api.routes import items, login, menu, private, roles, scheduler, users, utils, polarization, etf, fund, index, user_config, stock, macro, futures, spot, option, bond, forex, us_stock
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
api_router.include_router(index.router)
api_router.include_router(stock.router)
api_router.include_router(macro.router)
api_router.include_router(futures.router)
api_router.include_router(spot.router)
api_router.include_router(option.router)
api_router.include_router(bond.router)
api_router.include_router(forex.router)
api_router.include_router(us_stock.router)
api_router.include_router(scheduler.router)
api_router.include_router(user_config.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
