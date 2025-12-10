import os
import secrets
import warnings
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


def get_env_files() -> list[str]:
    """
    根据 ENV_PROFILE 环境变量加载对应的配置文件
    类似 Spring Boot 的 spring.profiles.active
    
    优先级：
    1. .env.{profile} (如果 ENV_PROFILE 存在，会覆盖基础配置)
    2. .env (基础配置)
    
    特殊处理（测试分支）：
    - 如果没有设置 ENV_PROFILE，不加载任何 .env 文件，直接使用代码中的默认值
    - 这样测试分支就不需要依赖服务器上的配置文件
    - 如果设置了 ENV_PROFILE，按原逻辑加载 .env 和 .env.{profile}
    
    示例：
    - ENV_PROFILE=local -> 加载 .env.local 和 .env
    - ENV_PROFILE=staging -> 加载 .env.staging 和 .env
    - ENV_PROFILE=production -> 加载 .env.production 和 .env
    - 无 ENV_PROFILE -> 不加载任何文件，使用代码默认值（测试分支）
    """
    # 获取 api 目录（backend 的上一级）
    # __file__: backend/app/core/config.py
    # backend_dir: backend
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # api_dir: api (backend 的父目录)
    api_dir = os.path.dirname(backend_dir)
    
    env_files = []
    profile = os.getenv("ENV_PROFILE") or os.getenv("PROFILE")
    
    # 如果没有设置 ENV_PROFILE，不加载任何配置文件，直接使用代码中的默认值（测试分支）
    if not profile:
        print("[Config] 测试分支模式：未设置 ENV_PROFILE，使用代码中的默认测试环境配置")
        return []  # 返回空列表，不加载任何 .env 文件
    
    # 如果设置了 ENV_PROFILE，按原逻辑加载配置文件
    # 先加载基础配置
    base_env = os.path.join(api_dir, ".env")
    if os.path.exists(base_env):
        env_files.append(base_env)
        print(f"[Config] 加载基础配置文件: {base_env}")
    
    # 再加载 profile 特定配置（会覆盖基础配置）
    profile_env = os.path.join(api_dir, f".env.{profile}")
    if os.path.exists(profile_env):
        env_files.append(profile_env)
        print(f"[Config] 加载 Profile 配置文件: {profile_env}")
    else:
        warnings.warn(f"Profile file not found: {profile_env}", stacklevel=1)
    
    return env_files


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # 动态加载环境文件
        env_file=get_env_files(),
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "KaC9MXDkiiBZohHHlS7ZEU5BDHvJeZwAhPwDW5QLZhs"  # 测试环境默认密钥
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://192.168.31.150"  # 测试环境默认前端地址
    ENVIRONMENT: Literal["local", "staging", "production"] = "staging"  # 测试分支默认环境

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = "http://192.168.31.150,http://localhost:5173"  # 测试环境默认 CORS

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    # 测试环境默认配置（测试分支专用，如果环境变量未设置则使用这些默认值）
    PROJECT_NAME: str = "航融金融平台"
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str = "192.168.31.150"  # 测试环境默认服务器
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "Pg2025Secure"  # 测试环境默认密码（不含特殊字符，便于直连）
    POSTGRES_DB: str = "finance"  # 测试环境默认数据库

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        # 密码含特殊字符时需要进行 URL 编码，否则 SQLAlchemy 解析会失败
        encoded_password = quote(self.POSTGRES_PASSWORD, safe="")
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=encoded_password,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: EmailStr | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr = "admin@hangrong.com"  # 测试环境默认值
    FIRST_SUPERUSER_PASSWORD: str = "Admin@2025Secure"  # 测试环境默认值

    # ============================================
    # Tushare Pro 配置
    # ============================================
    TUSHARE_TOKEN: str | None = None  # Tushare Pro API Token
    TUSHARE_API_URL: str = "http://pro.tushare.nlink.vip"  # Tushare Pro API 地址

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            elif self.ENVIRONMENT == "staging":
                # 测试环境：只警告，不报错
                warnings.warn(message, stacklevel=1)
            else:
                # 生产环境：强制要求修改
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        # 测试环境：如果 SECRET_KEY 是 "changethis"，自动使用代码中的默认值
        if self.ENVIRONMENT == "staging" and self.SECRET_KEY == "changethis":
            self.SECRET_KEY = "KaC9MXDkiiBZohHHlS7ZEU5BDHvJeZwAhPwDW5QLZhs"
            warnings.warn(
                "SECRET_KEY was 'changethis' in staging environment, using default test key.",
                stacklevel=1
            )
        
        # 执行检查
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        
        # 生产环境才强制检查其他密钥
        if self.ENVIRONMENT == "production":
            self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
            self._check_default_secret(
                "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
            )

        return self


settings = Settings()  # type: ignore
