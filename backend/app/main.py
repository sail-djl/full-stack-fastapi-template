import logging
import sys
import os
from logging.handlers import TimedRotatingFileHandler
import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

# Ensure logs directory exists
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

file_handler = TimedRotatingFileHandler(
    filename=os.path.join(log_dir, "app.log"),
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter('%(levelname)s:     %(name)s:%(message)s'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        file_handler,
        logging.StreamHandler(sys.stdout)
    ]
)

from app.api.main import api_router
from app.core.config import settings
from app.scheduler import init_scheduler


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

# 初始化定时任务调度器
init_scheduler(app)