# prestart.sh 脚本说明

## 概述

`prestart.sh` 是应用启动前的初始化脚本，用于确保数据库就绪、执行数据库迁移和创建初始数据。通常在 Docker 容器启动或应用部署前执行。

## 脚本内容

```bash
#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python app/backend_pre_start.py

# Run migrations
alembic upgrade head

# Create initial data in DB
python app/initial_data.py
```

## 脚本解析

### 1. Shebang 行

```bash
#! /usr/bin/env bash
```

**功能说明：**
- 指定脚本使用 Bash 解释器执行
- `#!/usr/bin/env bash` 使用环境变量中的 bash，兼容性更好

### 2. 错误处理设置

```bash
set -e
set -x
```

**`set -e`：**
- 遇到任何命令返回非零退出码时，立即退出脚本
- 防止错误继续执行，确保脚本的健壮性

**`set -x`：**
- 打印每条执行的命令及其参数
- 便于调试，可以看到脚本的执行过程

### 3. 步骤一：等待数据库就绪

```bash
python app/backend_pre_start.py
```

**功能说明：**
- 检查数据库连接是否可用
- 使用重试机制，最多尝试 5 分钟（300 次，每次间隔 1 秒）
- 确保在数据库完全启动后再继续执行后续步骤

**实现细节：**
- 使用 `tenacity` 库实现重试逻辑
- 通过执行 `SELECT 1` 测试数据库连接
- 如果数据库未就绪，会不断重试直到成功或超时

**为什么需要这一步？**
- Docker Compose 中，后端容器可能比数据库容器先启动
- 数据库需要时间初始化，不能立即连接
- 避免后续步骤因数据库未就绪而失败

### 4. 步骤二：运行数据库迁移

```bash
alembic upgrade head
```

**功能说明：**
- 执行 Alembic 数据库迁移
- `upgrade head` 表示升级到最新的迁移版本
- 创建或更新数据库表结构

**Alembic 迁移：**
- 版本化的数据库架构管理
- 每个迁移文件记录数据库结构的变化
- 支持升级（upgrade）和降级（downgrade）

**迁移文件位置：**
- `app/alembic/versions/` 目录下
- 文件名格式：`{revision}_{description}.py`

**为什么需要这一步？**
- 确保数据库表结构与代码中的模型定义一致
- 支持数据库结构的版本控制和团队协作
- 可以在不同环境间同步数据库结构

### 5. 步骤三：创建初始数据

```bash
python app/initial_data.py
```

**功能说明：**
- 创建应用运行所需的基础数据
- 主要是创建初始超级用户（如果不存在）

**实现逻辑：**
- 检查是否存在配置的初始超级用户
- 如果不存在，创建超级用户账户
- 密码会自动使用 Bcrypt 加密存储

**初始用户配置：**
- 从 `.env` 文件读取：
  - `FIRST_SUPERUSER`: 初始超级用户邮箱
  - `FIRST_SUPERUSER_PASSWORD`: 初始超级用户密码

**为什么需要这一步？**
- 应用首次启动时需要至少一个管理员账户
- 确保应用可以正常使用（登录、管理等）
- 幂等性：如果用户已存在，不会重复创建

## 执行流程

```
1. 脚本开始执行
   └─> set -e (遇到错误立即退出)
   └─> set -x (显示执行命令)

2. backend_pre_start.py
   └─> 尝试连接数据库
       ├─> 成功 → 继续
       └─> 失败 → 等待 1 秒后重试（最多 5 分钟）

3. alembic upgrade head
   └─> 读取迁移文件
   └─> 检查当前数据库版本
   └─> 执行未应用的迁移
   └─> 更新数据库结构

4. initial_data.py
   └─> 连接数据库
   └─> 检查初始用户是否存在
   └─> 如果不存在，创建初始超级用户

5. 脚本执行完成
```

## 使用场景

### 1. Docker Compose 启动

在 `docker-compose.yml` 中配置：

```yaml
backend:
  command: bash scripts/prestart.sh && fastapi run app/main.py
```

### 2. 手动执行

```bash
# 在 backend 目录下
bash scripts/prestart.sh
```

### 3. 在容器内执行

```bash
# 进入容器
docker compose exec backend bash

# 执行脚本
bash scripts/prestart.sh
```

## 相关文件

### 核心文件

- `scripts/prestart.sh` - 本脚本文件
- `app/backend_pre_start.py` - 数据库连接检查
- `app/initial_data.py` - 初始数据创建
- `app/core/db.py` - 数据库初始化和连接

### 配置文件

- `.env` - 环境变量配置（数据库连接、初始用户等）
- `alembic.ini` - Alembic 迁移配置
- `app/alembic/versions/` - 数据库迁移文件

## 注意事项

### 1. 执行顺序

三个步骤必须按顺序执行：
1. 先等待数据库就绪（否则后续步骤会失败）
2. 再执行迁移（创建表结构）
3. 最后创建初始数据（需要表结构已存在）

### 2. 错误处理

- `set -e` 确保任何步骤失败都会停止脚本
- 便于快速定位问题
- 不会在错误状态下继续执行

### 3. 幂等性

- `backend_pre_start.py`：可以重复执行，只是检查连接
- `alembic upgrade head`：只执行未应用的迁移，已应用的会跳过
- `initial_data.py`：检查用户是否存在，不会重复创建

### 4. 环境变量

确保以下环境变量已正确配置：
- `POSTGRES_SERVER` - 数据库服务器地址
- `POSTGRES_PORT` - 数据库端口
- `POSTGRES_USER` - 数据库用户名
- `POSTGRES_PASSWORD` - 数据库密码
- `POSTGRES_DB` - 数据库名称
- `FIRST_SUPERUSER` - 初始超级用户邮箱
- `FIRST_SUPERUSER_PASSWORD` - 初始超级用户密码

### 5. 数据库迁移

- 迁移文件应该通过 `alembic revision --autogenerate` 生成
- 不要手动修改已应用的迁移文件
- 新增迁移后需要提交到版本控制系统

### 6. 生产环境

- 生产环境应该使用强密码
- 确保 `SECRET_KEY` 已更改（不是默认值）
- 建议使用环境变量而不是 `.env` 文件存储敏感信息

## 常见问题

### Q1: 脚本执行失败，提示数据库连接错误

**原因：** 数据库尚未启动或配置错误

**解决方案：**
- 检查数据库服务是否运行
- 验证 `.env` 文件中的数据库配置
- 增加 `backend_pre_start.py` 中的重试次数

### Q2: 迁移执行失败

**原因：** 迁移文件有错误或数据库状态不一致

**解决方案：**
- 检查迁移文件语法
- 查看 Alembic 版本历史：`alembic history`
- 手动修复数据库或回滚迁移

### Q3: 初始用户创建失败

**原因：** 表结构不存在或配置错误

**解决方案：**
- 确保迁移已成功执行
- 检查 `FIRST_SUPERUSER` 和 `FIRST_SUPERUSER_PASSWORD` 配置
- 查看日志了解具体错误信息

### Q4: 如何跳过某个步骤？

**跳过数据库检查：**
```bash
# 注释掉或删除这一行
# python app/backend_pre_start.py
```

**跳过迁移：**
```bash
# 注释掉或删除这一行
# alembic upgrade head
```

**跳过初始数据：**
```bash
# 注释掉或删除这一行
# python app/initial_data.py
```

## 扩展阅读

- [Alembic 官方文档](https://alembic.sqlalchemy.org/)
- [Tenacity 重试库文档](https://tenacity.readthedocs.io/)
- [FastAPI 部署文档](https://fastapi.tiangolo.com/deployment/)
- [Docker Compose 文档](https://docs.docker.com/compose/)






