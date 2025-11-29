# backend_pre_start.py 文件说明

## 概述

`backend_pre_start.py` 是应用启动前的数据库连接检查脚本。它的主要作用是确保数据库服务已经就绪，可以接受连接，然后再继续执行后续的数据库操作（如迁移、初始化数据等）。

## 使用场景

这个脚本主要用于以下场景：

1. **Docker Compose 环境**：后端容器可能比数据库容器先启动，需要等待数据库就绪
2. **应用部署前**：确保数据库连接正常后再启动应用
3. **自动化脚本**：在 `prestart.sh` 中作为第一步执行

## 文件结构

```python
import logging

from sqlalchemy import Engine
from sqlmodel import Session, select
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

from app.core.db import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

max_tries = 60 * 5  # 5 minutes
wait_seconds = 1

@retry(...)
def init(db_engine: Engine) -> None:
    # 数据库连接检查逻辑

def main() -> None:
    # 主函数

if __name__ == "__main__":
    main()
```

## 代码详解

### 1. 导入模块

```python
import logging

from sqlalchemy import Engine
from sqlmodel import Session, select
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

from app.core.db import engine
```

**模块说明：**
- `logging`: Python 标准日志模块，用于记录执行过程
- `Engine`: SQLAlchemy 数据库引擎类型
- `Session`, `select`: SQLModel 的会话和查询功能
- `tenacity`: 重试库，提供装饰器实现自动重试
- `engine`: 从 `app.core.db` 导入的数据库引擎实例

### 2. 日志配置

```python
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

**功能说明：**
- 配置日志级别为 `INFO`，会输出信息、警告和错误日志
- 创建模块专用的日志记录器
- 用于记录连接尝试和结果

### 3. 重试参数配置

```python
max_tries = 60 * 5  # 5 minutes
wait_seconds = 1
```

**参数说明：**
- `max_tries = 300`: 最多尝试 300 次（60 秒 × 5 分钟）
- `wait_seconds = 1`: 每次重试间隔 1 秒
- **总等待时间**：最多等待 5 分钟（300 秒）

**为什么需要这么长时间？**
- 数据库容器启动可能需要较长时间
- 大型数据库初始化可能需要几分钟
- 网络延迟或临时故障需要重试

### 4. 重试装饰器

```python
@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
def init(db_engine: Engine) -> None:
    ...
```

**装饰器参数详解：**

#### `stop=stop_after_attempt(max_tries)`
- **功能**：指定停止重试的条件
- **参数**：最多尝试 `max_tries` 次（300 次）
- **行为**：达到最大尝试次数后，抛出最后一次异常

#### `wait=wait_fixed(wait_seconds)`
- **功能**：指定重试等待策略
- **参数**：固定等待 `wait_seconds` 秒（1 秒）
- **行为**：每次重试前等待 1 秒

#### `before=before_log(logger, logging.INFO)`
- **功能**：在每次重试前记录日志
- **级别**：`INFO`
- **输出**：记录即将尝试连接的信息

#### `after=after_log(logger, logging.WARN)`
- **功能**：在每次重试后记录日志（失败时）
- **级别**：`WARN`
- **输出**：记录连接失败后的警告信息

### 5. 数据库连接检查函数

```python
def init(db_engine: Engine) -> None:
    try:
        with Session(db_engine) as session:
            # Try to create session to check if DB is awake
            session.exec(select(1))
    except Exception as e:
        logger.error(e)
        raise e
```

**功能说明：**

#### 创建数据库会话
```python
with Session(db_engine) as session:
```
- 使用上下文管理器创建数据库会话
- 自动处理会话的创建和关闭
- 确保资源正确释放

#### 执行简单查询
```python
session.exec(select(1))
```
- `select(1)`: 最简单的 SQL 查询，返回数字 1
- 用于测试数据库连接是否可用
- 不涉及任何表操作，执行速度快

#### 异常处理
```python
except Exception as e:
    logger.error(e)
    raise e
```
- 捕获所有异常（连接错误、超时等）
- 记录错误日志
- 重新抛出异常，触发重试机制

**为什么使用 `select(1)`？**
- 最简单的数据库操作
- 不依赖任何表结构
- 可以快速验证数据库是否响应
- 比 `SELECT 1` 更符合 SQLModel 的用法

### 6. 主函数

```python
def main() -> None:
    logger.info("Initializing service")
    init(engine)
    logger.info("Service finished initializing")
```

**功能说明：**
- 记录开始初始化的日志
- 调用 `init()` 函数检查数据库连接
- 连接成功后记录完成日志

**执行流程：**
1. 输出 "Initializing service"
2. 尝试连接数据库（可能重试多次）
3. 连接成功后输出 "Service finished initializing"

### 7. 脚本入口

```python
if __name__ == "__main__":
    main()
```

**功能说明：**
- 当脚本直接执行时（不是被导入），运行 `main()` 函数
- 允许脚本既可以独立运行，也可以被其他模块导入

## 执行流程

```
1. 脚本启动
   └─> 配置日志
   └─> 导入数据库引擎

2. 调用 main()
   └─> 记录 "Initializing service"

3. 调用 init(engine)
   └─> @retry 装饰器开始工作

4. 尝试连接数据库
   ├─> 创建 Session
   ├─> 执行 select(1)
   │
   ├─> 成功 → 返回，继续执行
   │
   └─> 失败 → 抛出异常
       ├─> 记录错误日志
       ├─> before_log 记录重试信息
       ├─> 等待 1 秒
       ├─> after_log 记录警告
       └─> 重试（最多 300 次）

5. 连接成功
   └─> 记录 "Service finished initializing"
   └─> 脚本结束
```

## 重试机制详解

### Tenacity 库

`tenacity` 是一个强大的 Python 重试库，提供了灵活的重试策略。

### 重试行为示例

假设数据库在 30 秒后启动：

```
尝试 1: 失败 → 等待 1 秒
尝试 2: 失败 → 等待 1 秒
...
尝试 30: 成功 → 继续执行
```

### 日志输出示例

```
INFO:app.backend_pre_start:Initializing service
INFO:app.backend_pre_start:Retrying init in 1.0 seconds as it raised OperationalError: ...
WARNING:app.backend_pre_start:Finished call to 'init' after 1.001(s), this was the 1st time calling it.
INFO:app.backend_pre_start:Retrying init in 1.0 seconds as it raised OperationalError: ...
...
INFO:app.backend_pre_start:Service finished initializing
```

## 使用方式

### 1. 直接执行

```bash
python app/backend_pre_start.py
```

### 2. 在 prestart.sh 中使用

```bash
# Let the DB start
python app/backend_pre_start.py
```

### 3. 作为模块导入

```python
from app.backend_pre_start import init
from app.core.db import engine

# 检查数据库连接
init(engine)
```

## 相关文件

### 核心文件
- `app/backend_pre_start.py` - 本文件
- `app/core/db.py` - 数据库引擎定义
- `app/core/config.py` - 数据库配置

### 使用场景
- `scripts/prestart.sh` - 启动前脚本
- `app/initial_data.py` - 初始数据创建（依赖此脚本）

### 测试文件
- `tests/scripts/test_backend_pre_start.py` - 单元测试

## 配置说明

数据库连接配置在 `.env` 文件中：

```env
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changethis
POSTGRES_DB=app
```

这些配置会被 `app/core/config.py` 读取，并生成数据库连接 URI。

## 注意事项

### 1. 重试次数

- 默认最多重试 300 次（5 分钟）
- 如果数据库启动时间超过 5 分钟，脚本会失败
- 可以根据实际情况调整 `max_tries` 值

### 2. 等待间隔

- 固定等待 1 秒
- 如果数据库启动很快，可能会产生不必要的等待
- 可以使用指数退避策略（`wait_exponential`）优化

### 3. 异常类型

- 当前捕获所有异常（`Exception`）
- 可以更精确地捕获特定异常类型（如 `OperationalError`）

### 4. 日志级别

- 使用 `INFO` 级别记录正常流程
- 使用 `WARN` 级别记录重试警告
- 使用 `ERROR` 级别记录错误

### 5. 性能考虑

- `select(1)` 是最轻量的查询
- 不会对数据库造成负担
- 适合频繁重试

## 常见问题

### Q1: 脚本一直重试，数据库连接不上

**可能原因：**
- 数据库服务未启动
- 数据库配置错误（主机、端口、用户名、密码）
- 网络问题或防火墙阻止

**解决方案：**
- 检查数据库服务状态
- 验证 `.env` 文件配置
- 测试数据库连接：`psql -h localhost -U postgres -d app`

### Q2: 如何修改重试次数和等待时间？

**修改参数：**
```python
max_tries = 60 * 10  # 改为 10 分钟
wait_seconds = 2      # 改为等待 2 秒
```

### Q3: 如何禁用重试机制？

**移除装饰器：**
```python
# @retry(...)  # 注释掉装饰器
def init(db_engine: Engine) -> None:
    ...
```

### Q4: 如何只检查一次，不重试？

**使用 `stop=stop_after_attempt(1)`：**
```python
@retry(
    stop=stop_after_attempt(1),  # 只尝试一次
    ...
)
```

### Q5: 如何添加更详细的重试日志？

**使用 `retry_logging`：**
```python
from tenacity import retry_logging

@retry(
    ...
    retry=retry_logging(logger, logging.DEBUG),
)
```

## 优化建议

### 1. 使用指数退避

```python
from tenacity import wait_exponential

@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    ...
)
```

**优势：**
- 初始等待时间短
- 逐渐增加等待时间
- 减少不必要的重试

### 2. 只捕获特定异常

```python
from sqlalchemy.exc import OperationalError

@retry(
    retry=retry_if_exception_type(OperationalError),
    ...
)
```

**优势：**
- 只重试连接相关的错误
- 其他错误立即失败
- 更精确的错误处理

### 3. 添加超时机制

```python
from tenacity import stop_after_delay

@retry(
    stop=stop_after_delay(300),  # 5 分钟后停止
    ...
)
```

## 扩展阅读

- [Tenacity 官方文档](https://tenacity.readthedocs.io/)
- [SQLModel 文档](https://sqlmodel.tiangolo.com/)
- [SQLAlchemy Engine 文档](https://docs.sqlalchemy.org/en/14/core/engines.html)
- [Python Logging 文档](https://docs.python.org/3/library/logging.html)






