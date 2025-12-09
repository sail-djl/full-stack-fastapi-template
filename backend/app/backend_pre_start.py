import logging
import os

from sqlalchemy import Engine
from sqlmodel import Session, select
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

from app.core.db import engine
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

max_tries = 60 * 5  # 5 minutes
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
def init(db_engine: Engine) -> None:
    try:
        with Session(db_engine) as session:
            # Try to create session to check if DB is awake
            session.exec(select(1))
    except Exception as e:
        logger.error(e)
        raise e


def main() -> None:
    # 打印配置信息（用于调试）
    logger.info("=" * 50)
    logger.info("配置信息（用于调试）")
    logger.info("=" * 50)
    logger.info(f"ENV_PROFILE: {os.getenv('ENV_PROFILE', '未设置')}")
    logger.info(f"ENVIRONMENT: {settings.ENVIRONMENT}")
    logger.info(f"POSTGRES_SERVER: {settings.POSTGRES_SERVER}")
    logger.info(f"POSTGRES_PORT: {settings.POSTGRES_PORT}")
    logger.info(f"POSTGRES_DB: {settings.POSTGRES_DB}")
    logger.info(f"POSTGRES_USER: {settings.POSTGRES_USER}")
    logger.info(f"数据库连接字符串: {settings.SQLALCHEMY_DATABASE_URI}")
    logger.info("=" * 50)
    
    logger.info("Initializing service")
    init(engine)
    logger.info("Service finished initializing")


if __name__ == "__main__":
    main()
