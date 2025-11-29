# FastAPI 后端项目介绍

## 项目概述

这是一个基于 FastAPI 构建的现代化 Python Web API 后端项目。项目采用最佳实践，提供了完整的用户认证、权限管理、数据 CRUD 操作等功能，是构建全栈应用的理想后端基础。

## 技术栈

### 核心框架
- **FastAPI** (>=0.114.2) - 现代、快速的 Python Web 框架
  - 自动生成 OpenAPI/Swagger 文档
  - 基于 Python 类型提示的自动数据验证
  - 异步支持，高性能

### 数据库与 ORM
- **SQLModel** (>=0.0.21) - 基于 SQLAlchemy 和 Pydantic 的 ORM
  - 类型安全的数据模型
  - 自动数据验证
  - 数据库关系管理

- **PostgreSQL** - 生产级关系型数据库
  - 通过 SQLModel 进行 ORM 操作
  - 支持复杂查询和事务

- **Alembic** (>=1.12.1) - 数据库迁移工具
  - 版本化数据库架构管理
  - 自动生成迁移脚本

### 认证与安全
- **JWT (PyJWT)** - JSON Web Token 认证
  - 无状态认证机制
  - Token 过期管理

- **Passlib + Bcrypt** - 密码哈希加密
  - 安全的密码存储
  - Bcrypt 加密算法

### 数据验证
- **Pydantic** (>2.0) - 数据验证和设置管理
  - 类型验证
  - 自动数据转换
  - 配置管理（Pydantic Settings）

### 邮件功能
- **emails** (>=0.6) - 邮件发送库
- **Jinja2** (>=3.1.4) - 模板引擎
  - HTML 邮件模板渲染

### 开发工具
- **uv** - 现代 Python 包管理器
- **Pytest** (>=7.4.3) - 测试框架
- **Ruff** (>=0.2.2) - 快速 Python linter
- **MyPy** (>=1.8.0) - 静态类型检查
- **Coverage** (>=7.4.3) - 测试覆盖率

### 监控与错误追踪
- **Sentry SDK** (>=1.40.6) - 错误追踪和性能监控

## 项目结构

```
backend/
├── app/                          # 应用主目录
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用入口
│   ├── models.py                 # SQLModel 数据模型
│   ├── crud.py                   # CRUD 操作函数
│   ├── utils.py                  # 工具函数（邮件、Token 等）
│   ├── initial_data.py           # 初始化数据脚本
│   │
│   ├── api/                      # API 路由
│   │   ├── __init__.py
│   │   ├── main.py               # API 路由聚合
│   │   ├── deps.py               # 依赖注入（数据库、认证等）
│   │   └── routes/               # 具体路由实现
│   │       ├── login.py          # 登录认证路由
│   │       ├── users.py          # 用户管理路由
│   │       ├── items.py          # 物品管理路由
│   │       ├── utils.py          # 工具路由（健康检查、测试邮件）
│   │       └── private.py        # 私有路由（仅本地环境）
│   │
│   ├── core/                     # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py             # 应用配置（Settings）
│   │   ├── db.py                 # 数据库连接和初始化
│   │   └── security.py           # 安全相关（密码、JWT）
│   │
│   ├── alembic/                  # 数据库迁移
│   │   ├── env.py                # Alembic 环境配置
│   │   ├── versions/             # 迁移版本文件
│   │   └── script.py.mako        # 迁移脚本模板
│   │
│   ├── email-templates/           # 邮件模板
│   │   ├── src/                  # MJML 源文件
│   │   └── build/                # 编译后的 HTML
│   │
│   ├── backend_pre_start.py      # 启动前检查脚本
│   └── tests_pre_start.py       # 测试前检查脚本
│
├── tests/                        # 测试代码
│   ├── api/                      # API 测试
│   ├── crud/                     # CRUD 测试
│   ├── scripts/                  # 脚本测试
│   └── utils/                    # 工具测试
│
├── scripts/                      # 脚本文件
│   ├── prestart.sh               # 启动前脚本
│   ├── test.sh                   # 测试脚本
│   ├── format.sh                 # 代码格式化
│   └── lint.sh                   # 代码检查
│
├── pyproject.toml                # 项目配置和依赖
├── alembic.ini                    # Alembic 配置
├── Dockerfile                     # Docker 镜像构建
└── README.md                      # 项目说明
```

## 核心模块详解

### 1. 应用入口 (`app/main.py`)

FastAPI 应用的创建和配置：

```python
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)
```

**主要功能：**
- 创建 FastAPI 应用实例
- 配置 CORS 中间件
- 集成 Sentry 错误追踪（生产环境）
- 注册 API 路由

### 2. 配置管理 (`app/core/config.py`)

使用 Pydantic Settings 进行配置管理：

**主要配置项：**
- `API_V1_STR`: API 版本前缀 (`/api/v1`)
- `SECRET_KEY`: JWT 加密密钥
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token 过期时间（默认 8 天）
- `FRONTEND_HOST`: 前端地址
- `BACKEND_CORS_ORIGINS`: CORS 允许的源
- `POSTGRES_*`: 数据库连接配置
- `SMTP_*`: 邮件服务器配置
- `FIRST_SUPERUSER`: 初始超级用户

**特性：**
- 从 `.env` 文件自动加载配置
- 自动验证配置值
- 计算字段（如 `SQLALCHEMY_DATABASE_URI`）
- 安全警告（检测默认值）

### 3. 数据库 (`app/core/db.py`)

数据库连接和初始化：

```python
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
```

**主要功能：**
- 创建数据库引擎
- 初始化数据库（创建初始超级用户）
- 数据库会话管理

### 4. 安全模块 (`app/core/security.py`)

**密码加密：**
- `get_password_hash()`: 使用 Bcrypt 加密密码
- `verify_password()`: 验证密码

**JWT Token：**
- `create_access_token()`: 创建访问令牌
- 使用 HS256 算法
- 支持过期时间设置

### 5. 数据模型 (`app/models.py`)

使用 SQLModel 定义数据模型：

**User 模型：**
- `UserBase`: 基础用户属性
- `UserCreate`: 创建用户时的数据
- `UserUpdate`: 更新用户时的数据
- `User`: 数据库表模型
- `UserPublic`: API 返回的用户数据

**Item 模型：**
- `ItemBase`: 基础物品属性
- `ItemCreate`: 创建物品时的数据
- `ItemUpdate`: 更新物品时的数据
- `Item`: 数据库表模型（关联 User）
- `ItemPublic`: API 返回的物品数据

**关系：**
- User 和 Item 是一对多关系
- 支持级联删除

### 6. CRUD 操作 (`app/crud.py`)

数据库操作的业务逻辑层：

**用户相关：**
- `create_user()`: 创建用户（自动加密密码）
- `update_user()`: 更新用户信息
- `get_user_by_email()`: 根据邮箱获取用户
- `authenticate()`: 用户认证（验证密码）

**物品相关：**
- `create_item()`: 创建物品

### 7. API 依赖 (`app/api/deps.py`)

FastAPI 依赖注入系统：

**数据库依赖：**
- `get_db()`: 获取数据库会话
- `SessionDep`: 类型注解别名

**认证依赖：**
- `get_current_user()`: 获取当前登录用户
- `get_current_active_superuser()`: 获取当前超级用户
- `CurrentUser`: 类型注解别名

**OAuth2：**
- `OAuth2PasswordBearer`: OAuth2 密码流认证

### 8. API 路由

#### 登录路由 (`app/api/routes/login.py`)

- `POST /login/access-token`: OAuth2 兼容的登录接口
- `POST /login/test-token`: 测试 Token 有效性
- `POST /password-recovery/{email}`: 密码重置请求
- `POST /reset-password/`: 重置密码

#### 用户路由 (`app/api/routes/users.py`)

- `GET /users/`: 获取用户列表（超级用户）
- `POST /users/`: 创建用户（超级用户）
- `GET /users/me`: 获取当前用户信息
- `PATCH /users/me`: 更新当前用户信息
- `PATCH /users/me/password`: 修改当前用户密码
- `DELETE /users/me`: 删除当前用户
- `POST /users/signup`: 用户注册
- `GET /users/{user_id}`: 获取指定用户
- `PATCH /users/{user_id}`: 更新指定用户（超级用户）
- `DELETE /users/{user_id}`: 删除指定用户（超级用户）

#### 物品路由 (`app/api/routes/items.py`)

- `GET /items/`: 获取物品列表
- `GET /items/{id}`: 获取指定物品
- `POST /items/`: 创建物品
- `PUT /items/{id}`: 更新物品
- `DELETE /items/{id}`: 删除物品

**权限控制：**
- 普通用户只能管理自己的物品
- 超级用户可以管理所有物品

#### 工具路由 (`app/api/routes/utils.py`)

- `POST /utils/test-email/`: 发送测试邮件（超级用户）
- `GET /utils/health-check/`: 健康检查

#### 私有路由 (`app/api/routes/private.py`)

仅在本地环境可用：
- `POST /private/users/`: 快速创建用户（开发用）

### 9. 工具函数 (`app/utils.py`)

**邮件功能：**
- `send_email()`: 发送邮件
- `generate_test_email()`: 生成测试邮件
- `generate_reset_password_email()`: 生成密码重置邮件
- `generate_new_account_email()`: 生成新账户邮件

**Token 功能：**
- `generate_password_reset_token()`: 生成密码重置 Token
- `verify_password_reset_token()`: 验证密码重置 Token

**模板渲染：**
- `render_email_template()`: 使用 Jinja2 渲染邮件模板

## 认证流程

### 1. 用户登录

```
客户端 → POST /api/v1/login/access-token
       (FormData: username=email, password=password)
       ↓
后端验证邮箱和密码
       ↓
生成 JWT Token
       ↓
返回 { "access_token": "...", "token_type": "bearer" }
```

### 2. 访问受保护资源

```
客户端 → 请求头: Authorization: Bearer {token}
       ↓
后端验证 Token
       ↓
从 Token 中提取用户 ID
       ↓
查询数据库获取用户信息
       ↓
返回资源或执行操作
```

### 3. 密码重置

```
客户端 → POST /api/v1/password-recovery/{email}
       ↓
后端生成重置 Token
       ↓
发送包含 Token 的邮件
       ↓
用户点击邮件链接（包含 Token）
       ↓
客户端 → POST /api/v1/reset-password/
       (Body: { "token": "...", "new_password": "..." })
       ↓
后端验证 Token 并更新密码
```

## 数据库迁移

### 创建迁移

```bash
docker compose exec backend bash
alembic revision --autogenerate -m "描述信息"
```

### 应用迁移

```bash
alembic upgrade head
```

### 回滚迁移

```bash
alembic downgrade -1
```

## 开发工作流

### 1. 本地开发

**使用 Docker Compose：**
```bash
docker compose watch
```

**直接运行（需要本地环境）：**
```bash
cd backend
uv sync
source .venv/bin/activate
fastapi run --reload app/main.py
```

### 2. 代码质量

**格式化代码：**
```bash
bash scripts/format.sh
```

**代码检查：**
```bash
bash scripts/lint.sh
```

**类型检查：**
```bash
mypy app/
```

### 3. 测试

**运行所有测试：**
```bash
bash scripts/test.sh
```

**运行特定测试：**
```bash
docker compose exec backend bash scripts/tests-start.sh -x
```

**查看测试覆盖率：**
```bash
# 测试后会生成 htmlcov/index.html
open htmlcov/index.html
```

## 环境配置

### 必需的环境变量

在项目根目录的 `.env` 文件中配置：

```env
# 项目名称
PROJECT_NAME="FastAPI Project"

# 安全密钥（必须修改）
SECRET_KEY="your-secret-key-here"

# 数据库配置
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changethis
POSTGRES_DB=app

# 初始超级用户
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=changethis

# 前端地址
FRONTEND_HOST=http://localhost:5173

# CORS 配置
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# 邮件配置（可选）
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=
EMAILS_FROM_EMAIL=info@example.com

# Sentry（可选）
SENTRY_DSN=
```

### 生成安全密钥

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## API 文档

启动服务后，可以访问：

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/api/v1/openapi.json`

## 测试

### 测试结构

- `tests/api/`: API 端点测试
- `tests/crud/`: CRUD 操作测试
- `tests/conftest.py`: Pytest 配置和 fixtures

### 运行测试

```bash
# 完整测试套件
bash scripts/test.sh

# 在运行中的容器中测试
docker compose exec backend bash scripts/tests-start.sh
```

## 邮件模板

邮件模板使用 MJML 编写，位于 `app/email-templates/src/`：

1. 编辑 `.mjml` 文件
2. 使用 VS Code MJML 扩展导出为 HTML
3. 保存到 `app/email-templates/build/`

## 启动流程

1. **backend_pre_start.py**: 检查数据库连接
2. **prestart.sh**: 
   - 运行数据库检查
   - 执行数据库迁移
   - 创建初始数据
3. **main.py**: 启动 FastAPI 应用

## 最佳实践

### 1. 代码组织
- 使用类型提示
- 遵循 RESTful API 设计
- 分离业务逻辑和路由处理

### 2. 安全
- 永远不要提交 `.env` 文件
- 使用强密码和密钥
- 定期更新依赖

### 3. 数据库
- 使用迁移管理数据库变更
- 不要直接修改数据库结构
- 测试迁移脚本

### 4. 测试
- 编写单元测试和集成测试
- 保持测试覆盖率
- 测试边界情况

## 常见问题

### 1. 数据库连接失败

**问题**: 无法连接到 PostgreSQL

**解决**:
- 检查 `.env` 中的数据库配置
- 确保数据库服务正在运行
- 检查网络连接

### 2. 迁移失败

**问题**: Alembic 迁移出错

**解决**:
- 检查模型定义是否正确
- 查看迁移文件内容
- 必要时回滚迁移

### 3. CORS 错误

**问题**: 前端请求被 CORS 阻止

**解决**:
- 检查 `BACKEND_CORS_ORIGINS` 配置
- 确保包含前端地址
- 重启后端服务

### 4. Token 验证失败

**问题**: JWT Token 无效

**解决**:
- 检查 Token 是否过期
- 验证 `SECRET_KEY` 是否正确
- 检查 Token 格式

## 扩展开发

### 添加新的 API 路由

1. 在 `app/api/routes/` 创建新文件
2. 定义路由和端点
3. 在 `app/api/main.py` 中注册路由

### 添加新的数据模型

1. 在 `app/models.py` 中定义模型
2. 创建迁移：`alembic revision --autogenerate -m "描述"`
3. 应用迁移：`alembic upgrade head`
4. 在 `app/crud.py` 中添加 CRUD 操作

### 添加新的依赖

1. 在 `pyproject.toml` 中添加依赖
2. 运行 `uv sync` 安装

## 性能优化

1. **数据库查询优化**
   - 使用索引
   - 避免 N+1 查询
   - 使用连接查询

2. **缓存策略**
   - 考虑添加 Redis 缓存
   - 缓存频繁查询的数据

3. **异步操作**
   - 使用 FastAPI 的异步特性
   - 异步数据库操作

## 部署

### Docker 部署

项目包含 `Dockerfile`，可以构建 Docker 镜像：

```bash
docker build -t backend .
```

### 生产环境配置

1. 修改所有默认密码和密钥
2. 配置正确的数据库连接
3. 设置 `ENVIRONMENT=production`
4. 配置 Sentry 错误追踪
5. 设置 HTTPS
6. 配置反向代理（Nginx/Traefik）

## 学习资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com)
- [SQLModel 文档](https://sqlmodel.tiangolo.com)
- [Pydantic 文档](https://docs.pydantic.dev)
- [Alembic 文档](https://alembic.sqlalchemy.org)

## 总结

这个 FastAPI 后端项目提供了一个完整的、生产就绪的 API 基础架构。它遵循最佳实践，包含用户认证、权限管理、数据库操作等核心功能。通过清晰的代码结构和完善的文档，可以快速扩展和定制以满足特定业务需求。

