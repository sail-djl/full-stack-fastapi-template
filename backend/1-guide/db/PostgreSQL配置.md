# PostgreSQL 数据库配置指南

## 概述

本项目使用 PostgreSQL 17 作为关系型数据库，通过 Docker Compose 进行容器化部署，使用 SQLModel 作为 ORM，Alembic 进行数据库迁移管理。

## 目录

- [Docker 配置](#docker-配置)
- [环境变量配置](#环境变量配置)
- [数据库连接配置](#数据库连接配置)
- [数据库初始化](#数据库初始化)
- [数据库迁移](#数据库迁移)
- [连接池配置](#连接池配置)
- [数据持久化](#数据持久化)
- [健康检查](#健康检查)
- [本地开发配置](#本地开发配置)
- [生产环境配置](#生产环境配置)
- [常见问题](#常见问题)

## Docker 配置

### Docker Compose 中的 PostgreSQL 服务

在 `docker-compose.yml` 中，PostgreSQL 服务配置如下：

```yaml
db:
  image: postgres:17
  restart: always
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
    interval: 10s
    retries: 5
    start_period: 30s
    timeout: 10s
  volumes:
    - app-db-data:/var/lib/postgresql/data/pgdata
  env_file:
    - .env
  environment:
    - PGDATA=/var/lib/postgresql/data/pgdata
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD?Variable not set}
    - POSTGRES_USER=${POSTGRES_USER?Variable not set}
    - POSTGRES_DB=${POSTGRES_DB?Variable not set}
```

### 配置说明

- **镜像版本**: `postgres:17` - 使用 PostgreSQL 17 版本
- **重启策略**: `always` - 容器总是自动重启
- **数据卷**: `app-db-data` - 持久化存储数据库数据
- **数据目录**: `/var/lib/postgresql/data/pgdata` - PostgreSQL 数据存储路径
- **健康检查**: 使用 `pg_isready` 命令检查数据库是否就绪

## 环境变量配置

### 必需的环境变量

在项目根目录的 `.env` 文件中配置以下变量：

```env
# PostgreSQL 数据库配置
POSTGRES_SERVER=db                    # 数据库服务器地址（Docker 中为服务名）
POSTGRES_PORT=5432                    # 数据库端口（默认 5432）
POSTGRES_USER=postgres                # 数据库用户名
POSTGRES_PASSWORD=changethis          # 数据库密码（必须修改）
POSTGRES_DB=app                       # 数据库名称
```

### 环境变量说明

| 变量名                | 说明             | 默认值 | 必需 |
| --------------------- | ---------------- | ------ | ---- |
| `POSTGRES_SERVER`   | 数据库服务器地址 | -      | ✅   |
| `POSTGRES_PORT`     | 数据库端口       | 5432   | ❌   |
| `POSTGRES_USER`     | 数据库用户名     | -      | ✅   |
| `POSTGRES_PASSWORD` | 数据库密码       | -      | ✅   |
| `POSTGRES_DB`       | 数据库名称       | -      | ✅   |

### 本地开发配置

如果要在本地直接连接 PostgreSQL（不使用 Docker），需要修改：

```env
POSTGRES_SERVER=localhost  # 或 127.0.0.1
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=app
```

## 数据库连接配置

### 连接字符串构建

在 `app/core/config.py` 中，数据库连接字符串通过计算字段自动构建：

```python
@computed_field
@property
def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
    return PostgresDsn.build(
        scheme="postgresql+psycopg",  # 使用 psycopg 驱动
        username=self.POSTGRES_USER,
        password=self.POSTGRES_PASSWORD,
        host=self.POSTGRES_SERVER,
        port=self.POSTGRES_PORT,
        path=self.POSTGRES_DB,
    )
```

### 连接字符串格式

生成的连接字符串格式为：

```
postgresql+psycopg://username:password@host:port/database
```

示例：

```
postgresql+psycopg://postgres:changethis@db:5432/app
```

### 数据库引擎创建

在 `app/core/db.py` 中创建数据库引擎：

```python
from sqlmodel import create_engine
from app.core.config import settings

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
```

## 数据库初始化

### 启动前检查

在 `app/backend_pre_start.py` 中，应用启动前会检查数据库连接：

```python
@retry(
    stop=stop_after_attempt(max_tries),  # 最多尝试 5 分钟
    wait=wait_fixed(wait_seconds),       # 每秒重试一次
)
def init(db_engine: Engine) -> None:
    try:
        with Session(db_engine) as session:
            # 尝试创建会话以检查数据库是否就绪
            session.exec(select(1))
    except Exception as e:
        logger.error(e)
        raise e
```

**功能**：

- 等待数据库服务启动
- 最多重试 300 次（5 分钟）
- 每秒检查一次连接

### 初始化脚本

在 `scripts/prestart.sh` 中执行初始化步骤：

```bash
# 1. 等待数据库就绪
python app/backend_pre_start.py

# 2. 运行数据库迁移
alembic upgrade head

# 3. 创建初始数据
python app/initial_data.py
```

### 初始数据创建

在 `app/initial_data.py` 中创建初始超级用户：

```python
def init_db(session: Session) -> None:
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)
```

## 数据库迁移

### Alembic 配置

#### alembic.ini

```ini
[alembic]
script_location = app/alembic
```

#### app/alembic/env.py

Alembic 环境配置从应用设置中获取数据库连接：

```python
from app.core.config import settings

def get_url():
    return str(settings.SQLALCHEMY_DATABASE_URI)

target_metadata = SQLModel.metadata
```

### 创建迁移

```bash
# 进入后端容器
docker compose exec backend bash

# 创建自动迁移
alembic revision --autogenerate -m "描述信息"

# 创建手动迁移
alembic revision -m "描述信息"
```

### 应用迁移

```bash
# 应用所有待执行的迁移
alembic upgrade head

# 应用特定版本
alembic upgrade <revision>

# 回滚一个版本
alembic downgrade -1

# 回滚到特定版本
alembic downgrade <revision>
```

### 迁移文件位置

迁移文件存储在：

```
backend/app/alembic/versions/
```

### 迁移最佳实践

1. **总是使用迁移**：不要直接修改数据库结构
2. **测试迁移**：在开发环境先测试迁移脚本
3. **版本控制**：将迁移文件提交到 Git
4. **备份数据**：生产环境迁移前先备份

## 连接池配置

### 默认配置

SQLModel 使用 SQLAlchemy 的连接池，默认配置：

- **池大小**: 5 个连接
- **最大溢出**: 10 个连接
- **池回收**: 3600 秒

### 自定义连接池

可以在创建引擎时自定义：

```python
from sqlmodel import create_engine

engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_size=10,           # 连接池大小
    max_overflow=20,        # 最大溢出连接数
    pool_pre_ping=True,     # 连接前检查连接是否有效
    pool_recycle=3600,      # 连接回收时间（秒）
)
```

### 连接池参数说明

| 参数              | 说明                   | 默认值       |
| ----------------- | ---------------------- | ------------ |
| `pool_size`     | 连接池中保持的连接数   | 5            |
| `max_overflow`  | 超出池大小的最大连接数 | 10           |
| `pool_pre_ping` | 使用前检查连接有效性   | False        |
| `pool_recycle`  | 连接回收时间（秒）     | -1（不回收） |
| `echo`          | 是否打印 SQL 语句      | False        |

## 数据持久化

### Docker 数据卷

PostgreSQL 数据存储在 Docker 卷中：

```yaml
volumes:
  app-db-data:
```

### 数据卷位置

- **Docker 卷名**: `app-db-data`
- **容器内路径**: `/var/lib/postgresql/data/pgdata`
- **数据持久化**: 即使容器删除，数据也会保留

### 备份数据

```bash
# 备份数据库
docker compose exec db pg_dump -U postgres app > backup.sql

# 恢复数据库
docker compose exec -T db psql -U postgres app < backup.sql
```

### 删除数据卷

⚠️ **警告**: 删除数据卷会永久删除所有数据！

```bash
# 停止服务
docker compose down

# 删除数据卷
docker volume rm full-stack-fastapi-template_app-db-data
```

## 健康检查

### Docker 健康检查配置

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
  interval: 10s      # 每 10 秒检查一次
  retries: 5         # 失败后重试 5 次
  start_period: 30s  # 启动后 30 秒开始检查
  timeout: 10s       # 超时时间 10 秒
```

### 健康检查命令

`pg_isready` 命令检查 PostgreSQL 是否准备好接受连接：

```bash
pg_isready -U postgres -d app
```

### 检查数据库状态

```bash
# 查看容器健康状态
docker compose ps

# 查看数据库日志
docker compose logs db

# 进入数据库容器
docker compose exec db bash

# 连接数据库
docker compose exec db psql -U postgres -d app
```

## 本地开发配置

### 使用 Docker Compose（推荐）

```bash
# 启动数据库
docker compose up -d db

# 查看日志
docker compose logs -f db

# 停止数据库
docker compose stop db
```

### 使用本地 PostgreSQL

1. **安装 PostgreSQL**

   **Windows**:

   ```bash
   # 使用 Chocolatey
   choco install postgresql

   # 或下载安装包
   # https://www.postgresql.org/download/windows/
   ```

   **macOS**:

   ```bash
   brew install postgresql
   brew services start postgresql
   ```

   **Linux**:

   ```bash
   sudo apt-get install postgresql postgresql-contrib
   sudo systemctl start postgresql
   ```
2. **创建数据库**

   ```bash
   # 连接到 PostgreSQL
   psql -U postgres

   # 创建数据库
   CREATE DATABASE app;

   # 创建用户（可选）
   CREATE USER app_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE app TO app_user;
   ```
3. **配置环境变量**

   ```env
   POSTGRES_SERVER=localhost
   POSTGRES_PORT=5432
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_password
   POSTGRES_DB=app
   ```

### 使用数据库管理工具

#### Adminer（已包含在 Docker Compose 中）

访问：`http://localhost:8080`（如果配置了 Traefik）

连接信息：

- 系统: PostgreSQL
- 服务器: `db`
- 用户名: `${POSTGRES_USER}`
- 密码: `${POSTGRES_PASSWORD}`
- 数据库: `${POSTGRES_DB}`

#### pgAdmin

1. 下载安装 [pgAdmin](https://www.pgadmin.org/)
2. 创建新服务器连接：
   - Host: `localhost`（或 Docker 服务名 `db`）
   - Port: `5432`
   - Database: `app`
   - Username: `postgres`
   - Password: 从 `.env` 文件获取

#### DBeaver

1. 下载安装 [DBeaver](https://dbeaver.io/)
2. 创建 PostgreSQL 连接
3. 配置连接信息

## 生产环境配置

### 安全建议

1. **强密码**

   ```env
   POSTGRES_PASSWORD=<强密码，至少 16 位，包含大小写字母、数字、特殊字符>
   ```
2. **独立数据库用户**

   ```sql
   -- 创建专用应用用户
   CREATE USER app_user WITH PASSWORD 'strong_password';
   GRANT CONNECT ON DATABASE app TO app_user;
   GRANT USAGE ON SCHEMA public TO app_user;
   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
   ```
3. **SSL 连接**

   ```python
   # 在连接字符串中添加 SSL 参数
   engine = create_engine(
       str(settings.SQLALCHEMY_DATABASE_URI),
       connect_args={
           "sslmode": "require"
       }
   )
   ```
4. **网络隔离**

   - 数据库服务不暴露到公网
   - 仅允许应用服务器访问
   - 使用防火墙规则限制访问

### 性能优化

1. **连接池配置**

   ```python
   engine = create_engine(
       str(settings.SQLALCHEMY_DATABASE_URI),
       pool_size=20,
       max_overflow=40,
       pool_pre_ping=True,
       pool_recycle=3600,
   )
   ```
2. **数据库索引**

   - 在模型字段上添加索引
   - 为常用查询字段创建索引
3. **查询优化**

   - 使用 `select()` 而不是加载所有字段
   - 使用 `joinedload()` 避免 N+1 查询
   - 使用分页限制结果集大小

### 备份策略

1. **自动备份脚本**

   ```bash
   #!/bin/bash
   # backup.sh

   BACKUP_DIR="/backups"
   DATE=$(date +%Y%m%d_%H%M%S)
   BACKUP_FILE="$BACKUP_DIR/app_$DATE.sql"

   docker compose exec -T db pg_dump -U postgres app > $BACKUP_FILE

   # 压缩备份
   gzip $BACKUP_FILE

   # 删除 30 天前的备份
   find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
   ```
2. **定时备份**

   使用 cron 定时执行备份：

   ```bash
   # 每天凌晨 2 点备份
   0 2 * * * /path/to/backup.sh
   ```
3. **备份验证**

   ```bash
   # 验证备份文件
   gunzip -c backup.sql.gz | head -n 20
   ```

## 常见问题

### 1. 数据库连接失败

**错误信息**:

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**解决方案**:

1. 检查数据库服务是否运行：

   ```bash
   docker compose ps db
   ```
2. 检查环境变量是否正确：

   ```bash
   docker compose exec backend env | grep POSTGRES
   ```
3. 检查网络连接：

   ```bash
   docker compose exec backend ping db
   ```
4. 查看数据库日志：

   ```bash
   docker compose logs db
   ```

### 2. 迁移失败

**错误信息**:

```
alembic.util.exc.CommandError: Target database is not up to date
```

**解决方案**:

1. 查看当前迁移版本：

   ```bash
   alembic current
   ```
2. 查看迁移历史：

   ```bash
   alembic history
   ```
3. 应用所有迁移：

   ```bash
   alembic upgrade head
   ```

### 3. 权限错误

**错误信息**:

```
permission denied for schema public
```

**解决方案**:

```sql
-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE app TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA public TO postgres;
```

### 4. 连接池耗尽

**错误信息**:

```
QueuePool limit of size X overflow Y reached
```

**解决方案**:

1. 增加连接池大小
2. 检查是否有连接泄漏
3. 优化查询性能，减少连接持有时间

### 5. 数据丢失

**预防措施**:

1. 定期备份数据库
2. 使用版本控制的迁移脚本
3. 在生产环境迁移前先在测试环境验证

**恢复数据**:

```bash
# 从备份恢复
docker compose exec -T db psql -U postgres app < backup.sql
```

## 数据库管理命令

### 常用 SQL 命令

```sql
-- 列出所有数据库
\l

-- 连接到数据库
\c app

-- 列出所有表
\dt

-- 查看表结构
\d table_name

-- 查看表数据
SELECT * FROM table_name LIMIT 10;

-- 退出
\q
```

### Docker 命令

```bash
# 进入数据库容器
docker compose exec db bash

# 连接数据库
docker compose exec db psql -U postgres -d app

# 执行 SQL 文件
docker compose exec -T db psql -U postgres -d app < script.sql

# 导出数据库
docker compose exec db pg_dump -U postgres app > dump.sql

# 导入数据库
docker compose exec -T db psql -U postgres app < dump.sql
```

## 性能监控

### 查看数据库统计

```sql
-- 查看数据库大小
SELECT pg_size_pretty(pg_database_size('app'));

-- 查看表大小
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 查看连接数
SELECT count(*) FROM pg_stat_activity;

-- 查看慢查询
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
```

## 总结

PostgreSQL 配置要点：

1. ✅ **使用 Docker Compose** 简化部署和管理
2. ✅ **环境变量配置** 分离配置和代码
3. ✅ **Alembic 迁移** 版本化数据库变更
4. ✅ **健康检查** 确保服务可用性
5. ✅ **数据持久化** 使用 Docker 卷保存数据
6. ✅ **连接池** 优化数据库连接管理
7. ✅ **安全配置** 生产环境使用强密码和 SSL
8. ✅ **定期备份** 防止数据丢失

通过遵循本指南，可以确保 PostgreSQL 数据库的稳定运行和良好性能。
