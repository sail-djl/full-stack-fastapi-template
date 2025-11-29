# core 模块说明

## 概述

`core` 模块是应用的核心基础模块，包含应用运行所需的核心功能：配置管理、数据库连接和安全认证。这些模块在整个应用中被广泛使用，是应用的基础设施层。

## 模块结构

```
app/core/
├── __init__.py          # 模块初始化文件
├── config.py            # 配置管理（Settings 类）
├── db.py                # 数据库连接和初始化
└── security.py          # 安全相关（密码加密、JWT）
```

## 模块文件详解

### 1. config.py - 配置管理

**文件作用：**
- 管理应用的所有配置项
- 从环境变量（`.env` 文件）读取配置
- 提供类型安全的配置访问
- 自动验证配置值的有效性

**核心类：`Settings`**

继承自 `Pydantic BaseSettings`，提供配置管理功能。

#### 主要配置项

##### API 配置
```python
API_V1_STR: str = "/api/v1"  # API 版本前缀
```

##### 安全配置
```python
SECRET_KEY: str = secrets.token_urlsafe(32)  # JWT 加密密钥
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # Token 过期时间（8天）
```

##### 环境配置
```python
ENVIRONMENT: Literal["local", "staging", "production"] = "local"
FRONTEND_HOST: str = "http://localhost:5173"
```

##### CORS 配置
```python
BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = []
```

**计算字段：`all_cors_origins`**
- 自动合并 `BACKEND_CORS_ORIGINS` 和 `FRONTEND_HOST`
- 用于 CORS 中间件配置

##### 数据库配置
```python
POSTGRES_SERVER: str
POSTGRES_PORT: int = 5432
POSTGRES_USER: str
POSTGRES_PASSWORD: str = ""
POSTGRES_DB: str = ""
```

**计算字段：`SQLALCHEMY_DATABASE_URI`**
- 自动构建 PostgreSQL 连接 URI
- 格式：`postgresql+psycopg://user:password@host:port/dbname`

##### 邮件配置
```python
SMTP_TLS: bool = True
SMTP_SSL: bool = False
SMTP_PORT: int = 587
SMTP_HOST: str | None = None
SMTP_USER: str | None = None
SMTP_PASSWORD: str | None = None
EMAILS_FROM_EMAIL: EmailStr | None = None
EMAILS_FROM_NAME: EmailStr | None = None
EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48
```

**计算字段：`emails_enabled`**
- 检查邮件功能是否启用
- 需要 `SMTP_HOST` 和 `EMAILS_FROM_EMAIL` 都配置

##### 用户配置
```python
FIRST_SUPERUSER: EmailStr  # 初始超级用户邮箱
FIRST_SUPERUSER_PASSWORD: str  # 初始超级用户密码
```

#### 配置验证

**安全验证：`_enforce_non_default_secrets`**
- 检查关键配置项是否为默认值 `"changethis"`
- 本地环境：发出警告
- 生产环境：抛出异常，强制修改

**验证项：**
- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `FIRST_SUPERUSER_PASSWORD`

#### 配置加载

```python
model_config = SettingsConfigDict(
    env_file="../.env",  # 从上级目录的 .env 文件加载
    env_ignore_empty=True,  # 忽略空值
    extra="ignore",  # 忽略未定义的字段
)
```

#### 使用方式

```python
from app.core.config import settings

# 访问配置
db_uri = settings.SQLALCHEMY_DATABASE_URI
api_prefix = settings.API_V1_STR
project_name = settings.PROJECT_NAME
```

### 2. db.py - 数据库连接和初始化

**文件作用：**
- 创建数据库引擎
- 提供数据库初始化函数
- 管理数据库连接

#### 数据库引擎

```python
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
```

**功能：**
- 使用 SQLModel 创建数据库引擎
- 连接字符串从 `settings.SQLALCHEMY_DATABASE_URI` 获取
- 全局单例，整个应用共享

#### 数据库初始化函数

```python
def init_db(session: Session) -> None:
    # 检查初始用户是否存在
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    
    # 如果不存在，创建初始超级用户
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)
```

**功能说明：**
- 创建初始超级用户（如果不存在）
- 幂等性：可以安全地重复执行
- 密码会自动加密（通过 `crud.create_user`）

**注意事项：**
- 表结构应该通过 Alembic 迁移创建
- 不要使用 `SQLModel.metadata.create_all(engine)`（已注释）

#### 使用方式

```python
from app.core.db import engine, init_db
from sqlmodel import Session

# 创建数据库会话
with Session(engine) as session:
    # 执行数据库操作
    session.add(...)
    session.commit()

# 初始化数据库
with Session(engine) as session:
    init_db(session)
```

### 3. security.py - 安全相关

**文件作用：**
- 密码加密和验证
- JWT Token 生成

#### 密码加密上下文

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

**功能：**
- 使用 Bcrypt 算法加密密码
- 自动处理密码哈希和验证

#### 密码相关函数

##### `get_password_hash(password: str) -> str`
```python
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
```

**功能：**
- 对明文密码进行 Bcrypt 加密
- 返回加密后的哈希值
- 用于存储用户密码

##### `verify_password(plain_password: str, hashed_password: str) -> bool`
```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

**功能：**
- 验证明文密码是否匹配哈希值
- 用于用户登录验证

#### JWT Token 相关

##### `create_access_token(subject: str | Any, expires_delta: timedelta) -> str`
```python
def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

**功能：**
- 创建 JWT 访问令牌
- `subject`: 通常是用户 ID
- `expires_delta`: Token 过期时间
- 使用 `HS256` 算法和 `SECRET_KEY` 签名

**Token 内容：**
- `exp`: 过期时间（UTC）
- `sub`: 主题（用户标识）

#### 使用方式

```python
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token
)

# 加密密码
hashed = get_password_hash("my_password")

# 验证密码
is_valid = verify_password("my_password", hashed)

# 创建 Token
from datetime import timedelta
token = create_access_token(
    subject="user_id",
    expires_delta=timedelta(minutes=30)
)
```

## 模块使用场景

### 1. 应用启动（main.py）

```python
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)
```

### 2. API 路由（api/routes/）

```python
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.core.db import engine
```

### 3. 依赖注入（api/deps.py）

```python
from app.core.db import engine
from app.core import security
from app.core.config import settings
```

### 4. 数据库初始化（initial_data.py）

```python
from app.core.db import engine, init_db
```

### 5. 启动前检查（backend_pre_start.py）

```python
from app.core.db import engine
```

## 模块依赖关系

```
config.py
  ├─> 无依赖（基础模块）
  │
db.py
  ├─> config.py (settings)
  │
security.py
  └─> config.py (settings)
```

**依赖顺序：**
1. `config.py` - 最基础，无依赖
2. `db.py` - 依赖 `config.py`
3. `security.py` - 依赖 `config.py`

## 配置管理最佳实践

### 1. 环境变量配置

在 `.env` 文件中配置（位于项目根目录）：

```env
# 项目配置
PROJECT_NAME=My FastAPI Project

# API 配置
API_V1_STR=/api/v1

# 安全配置
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=11520

# 环境配置
ENVIRONMENT=local
FRONTEND_HOST=http://localhost:5173

# 数据库配置
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
POSTGRES_DB=app

# CORS 配置
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# 邮件配置
SMTP_TLS=True
SMTP_PORT=587
SMTP_HOST=smtp.example.com
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-smtp-password
EMAILS_FROM_EMAIL=noreply@example.com
EMAILS_FROM_NAME=My FastAPI Project

# 初始用户
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=your-admin-password

# Sentry（可选）
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

### 2. 生产环境配置

**重要：**
- 必须修改 `SECRET_KEY`（不能是 `changethis`）
- 必须修改 `POSTGRES_PASSWORD`
- 必须修改 `FIRST_SUPERUSER_PASSWORD`
- 使用环境变量而不是 `.env` 文件存储敏感信息

### 3. 配置验证

配置加载时会自动验证：
- 类型检查（Pydantic 自动验证）
- 安全检查（默认值警告/错误）
- 必填字段检查

## 安全注意事项

### 1. 密码存储

- ✅ 使用 Bcrypt 加密存储
- ✅ 永远不存储明文密码
- ✅ 使用 `get_password_hash()` 加密

### 2. JWT Token

- ✅ 使用强密钥（`SECRET_KEY`）
- ✅ 设置合理的过期时间
- ✅ 使用 HTTPS 传输

### 3. 配置安全

- ✅ 生产环境使用环境变量
- ✅ 不要提交 `.env` 文件到版本控制
- ✅ 定期轮换密钥和密码

## 常见问题

### Q1: 如何修改配置？

**方法 1：修改 `.env` 文件**
```env
PROJECT_NAME=My New Project Name
```

**方法 2：使用环境变量**
```bash
export PROJECT_NAME="My New Project Name"
```

### Q2: 配置不生效？

**检查：**
1. `.env` 文件位置是否正确（项目根目录）
2. 环境变量是否被正确读取
3. 是否重启了应用

### Q3: 如何添加新的配置项？

在 `Settings` 类中添加：

```python
class Settings(BaseSettings):
    # 现有配置...
    
    # 新配置项
    NEW_CONFIG: str = "default_value"
```

### Q4: 数据库连接失败？

**检查：**
1. 数据库服务是否运行
2. 连接配置是否正确
3. 网络是否可达
4. 用户权限是否足够

### Q5: 密码验证失败？

**可能原因：**
1. 密码哈希算法不匹配
2. 密码存储格式错误
3. 密码确实不匹配

**解决方案：**
- 确保使用 `get_password_hash()` 加密
- 确保使用 `verify_password()` 验证

## 扩展阅读

- [Pydantic Settings 文档](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [SQLModel 文档](https://sqlmodel.tiangolo.com/)
- [Passlib 文档](https://passlib.readthedocs.io/)
- [PyJWT 文档](https://pyjwt.readthedocs.io/)
- [FastAPI 配置文档](https://fastapi.tiangolo.com/advanced/settings/)



