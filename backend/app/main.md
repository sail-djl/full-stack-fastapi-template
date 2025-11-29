# main.py 文件说明

## 概述

`main.py` 是 FastAPI 应用的主入口文件，负责初始化应用实例、配置中间件和注册路由。

## 文件结构

### 导入模块

```python
import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
```

- `sentry_sdk`: Sentry 错误监控 SDK，用于生产环境的错误追踪
- `FastAPI`: FastAPI 框架核心类
- `APIRoute`: FastAPI 路由类，用于自定义路由 ID 生成
- `CORSMiddleware`: CORS 跨域中间件
- `api_router`: 主 API 路由器，包含所有 API 端点
- `settings`: 应用配置对象

### 自定义路由 ID 生成函数

```python
def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"
```

**功能说明：**
- 为每个 API 路由生成唯一的 ID
- 格式：`{标签}-{路由名称}`
- 用于 OpenAPI 文档中的操作 ID

**示例：**
- 如果路由标签为 `users`，路由名称为 `read_user`，则生成的 ID 为 `users-read_user`

### Sentry 初始化

```python
if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)
```

**功能说明：**
- 仅在非本地环境且配置了 Sentry DSN 时初始化 Sentry
- `enable_tracing=True`: 启用性能追踪功能
- 用于生产环境的错误监控和性能分析

**条件：**
- `settings.SENTRY_DSN` 必须存在
- `settings.ENVIRONMENT` 不能为 `"local"`

### FastAPI 应用初始化

```python
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)
```

**参数说明：**
- `title`: 应用标题，从配置中读取项目名称
- `openapi_url`: OpenAPI 规范文档的 URL 路径
  - 默认路径：`/api/v1/openapi.json`
- `generate_unique_id_function`: 自定义路由 ID 生成函数

### CORS 中间件配置

```python
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

**功能说明：**
- 配置跨域资源共享（CORS）中间件
- 仅在配置了允许的源时添加中间件

**配置项：**
- `allow_origins`: 允许的源列表（从 `settings.all_cors_origins` 获取）
  - 包含 `BACKEND_CORS_ORIGINS` 和 `FRONTEND_HOST`
- `allow_credentials=True`: 允许携带凭证（如 cookies）
- `allow_methods=["*"]`: 允许所有 HTTP 方法
- `allow_headers=["*"]`: 允许所有请求头

### API 路由注册

```python
app.include_router(api_router, prefix=settings.API_V1_STR)
```

**功能说明：**
- 将主 API 路由器注册到 FastAPI 应用
- 所有 API 端点使用统一的前缀：`/api/v1`
- `api_router` 包含所有子路由（登录、用户、工具、项目等）

## 执行流程

1. **导入依赖**：导入必要的模块和配置
2. **定义辅助函数**：创建自定义路由 ID 生成函数
3. **初始化 Sentry**（可选）：在非本地环境配置错误监控
4. **创建 FastAPI 应用**：初始化应用实例
5. **配置 CORS**（可选）：添加跨域中间件
6. **注册路由**：将 API 路由挂载到应用

## 相关文件

- `app/core/config.py`: 应用配置管理
- `app/api/main.py`: API 路由聚合
- `app/api/routes/`: 各个功能模块的路由定义

## 注意事项

1. **Sentry 配置**：仅在非本地环境启用，避免开发时的干扰
2. **CORS 配置**：确保前端应用能够正常访问 API
3. **路由前缀**：所有 API 端点统一使用 `/api/v1` 前缀
4. **环境变量**：相关配置通过 `.env` 文件管理
