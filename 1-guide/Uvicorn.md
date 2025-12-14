# Uvicorn 详解笔记

## 目录
- [什么是 Uvicorn](#什么是-uvicorn)
- [Python 常驻端口实现原理](#python-常驻端口实现原理)
- [项目中 Uvicorn 的使用](#项目中-uvicorn-的使用)
- [开发模式 vs 生产模式](#开发模式-vs-生产模式)
- [常用参数和配置](#常用参数和配置)
- [工作原理详解](#工作原理详解)
- [性能优化](#性能优化)
- [常见问题](#常见问题)

---

## 什么是 Uvicorn

**Uvicorn** 是一个轻量级、高性能的 **ASGI (Asynchronous Server Gateway Interface)** 服务器，用于运行基于 Python 的异步 Web 应用。

### 核心特性

- **ASGI 服务器**：支持异步 Python Web 框架（FastAPI、Starlette 等）
- **高性能**：基于 `uvloop` 和 `httptools`，性能接近 Node.js
- **HTTP/1.1 和 WebSockets**：完整支持
- **热重载**：开发模式下自动重载代码
- **多进程支持**：生产环境可使用多 worker 模式

### ASGI vs WSGI

| 特性 | WSGI | ASGI |
|------|------|------|
| **异步支持** | ❌ 同步 | ✅ 异步 |
| **WebSocket** | ❌ 不支持 | ✅ 支持 |
| **HTTP/2** | ❌ 有限支持 | ✅ 支持 |
| **框架示例** | Flask, Django | FastAPI, Starlette |
| **性能** | 较低 | 较高 |

---

## Python 常驻端口实现原理

### 疑问：Python 不是脚本语言吗？为什么可以常驻运行？

虽然 Python 被称为脚本语言，但它完全可以作为**常驻服务**运行。关键在于：

### 1. 事件循环机制

Uvicorn 使用 Python 的 `asyncio` 事件循环来保持程序运行：

```python
# Uvicorn 内部简化逻辑（伪代码）
import asyncio
import socket

async def main():
    # 创建 socket，绑定端口
    server = await create_server(host="127.0.0.1", port=8000)
    
    # 进入事件循环，持续监听请求
    while True:
        # 等待连接（阻塞等待，但不会阻塞事件循环）
        client, addr = await server.accept()
        
        # 处理请求（异步处理）
        await handle_request(client)
    
# 启动事件循环，程序会一直运行
asyncio.run(main())  # 直到手动停止（Ctrl+C）
```

### 2. 为什么进程不会退出？

**关键点：**
- Python 进程只要有**未完成的异步任务**或**阻塞操作**，就会持续运行
- Uvicorn 的事件循环会持续监听网络连接，所以进程不会退出
- 类似于 Node.js 的 Express、Java 的 Spring Boot，都是进程常驻模式

### 3. 类比其他语言

| 语言/框架 | 常驻方式 | 相似之处 |
|-----------|----------|----------|
| **Node.js (Express)** | Event Loop | 都使用事件循环保持运行 |
| **Java (Spring Boot)** | 主线程阻塞监听 | 都是进程常驻模式 |
| **Python (Uvicorn)** | asyncio Event Loop | 异步事件驱动 |
| **Go (Gin)** | goroutine + 主协程阻塞 | 并发模型不同但都常驻 |

---

## 项目中 Uvicorn 的使用

### 开发模式启动

```powershell
cd E:\finance\api\backend
uv run python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**参数说明：**
- `app.main:app`：应用入口（模块路径:应用实例）
- `--reload`：开启热重载（文件变化自动重启）
- `--host 127.0.0.1`：监听地址（本地）
- `--port 8000`：监听端口

**预期输出：**
```
INFO:     Will watch for changes in these directories: ['E:\\finance\\api\\backend']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 生产模式启动

#### 方式 1：使用 Uvicorn 命令行

```powershell
uv run python -m uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
```

#### 方式 2：使用 FastAPI CLI

```powershell
uv run fastapi run --workers 4 app/main.py
```

**Dockerfile 中的配置：**
```dockerfile
CMD ["fastapi", "run", "--workers", "4", "app/main.py"]
```

**区别：**
- **开发模式**：单进程 + 热重载（方便调试）
- **生产模式**：多进程（提高并发能力）

---

## 开发模式 vs 生产模式

### 开发模式

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**特点：**
- ✅ 自动重载代码（修改文件后自动重启）
- ✅ 单进程运行（便于调试）
- ✅ 详细错误信息
- ✅ 监听文件变化（WatchFiles）
- ❌ 性能较低（不适合生产）

**适用场景：**
- 本地开发
- 调试和测试
- 快速迭代

### 生产模式

```bash
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
```

**特点：**
- ✅ 多进程并发（提高吞吐量）
- ✅ 性能优化
- ✅ 稳定性更好
- ❌ 不支持热重载
- ❌ 调试困难

**Worker 数量选择：**
```
workers = (2 × CPU核心数) + 1
例如：4核CPU → (2×4)+1 = 9 workers
```

---

## 常用参数和配置

### 基础参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--host` | 监听地址 | `127.0.0.1` (本地) 或 `0.0.0.0` (所有接口) |
| `--port` | 监听端口 | `8000` |
| `--reload` | 开启热重载 | 开发模式使用 |
| `--workers` | Worker 进程数 | `4` (生产环境) |
| `--log-level` | 日志级别 | `info`, `debug`, `warning`, `error` |
| `--access-log` | 访问日志 | 默认开启 |
| `--timeout-keep-alive` | Keep-Alive 超时 | `5` (秒) |

### 完整示例

```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info \
  --access-log \
  --timeout-keep-alive 5 \
  --loop uvloop \
  --http httptools
```

### 配置文件方式

创建 `uvicorn_config.py`：

```python
import multiprocessing

# 基本配置
bind = "0.0.0.0:8000"
workers = (2 * multiprocessing.cpu_count()) + 1
worker_class = "uvicorn.workers.UvicornWorker"

# 日志配置
accesslog = "-"
errorlog = "-"
loglevel = "info"

# 性能配置
timeout = 120
keepalive = 5
```

使用配置文件：
```bash
gunicorn -c uvicorn_config.py app.main:app
```

---

## 工作原理详解

### 1. 启动流程

```
启动 Uvicorn
    ↓
创建事件循环 (asyncio)
    ↓
创建 ASGI 应用实例 (app.main:app)
    ↓
绑定 Socket (host:port)
    ↓
进入事件循环
    ↓
等待 HTTP 连接
    ↓
接收请求 → 解析 HTTP
    ↓
调用 ASGI 应用 (await app(scope, receive, send))
    ↓
处理请求 → 返回响应
    ↓
继续等待下一个连接...
```

### 2. 多进程模式（Workers）

```
主进程 (Master)
├── Worker 1 (独立进程，独立事件循环)
│   └── 处理请求 A
├── Worker 2 (独立进程，独立事件循环)
│   └── 处理请求 B
├── Worker 3 (独立进程，独立事件循环)
│   └── 处理请求 C
└── Worker 4 (独立进程，独立事件循环)
    └── 处理请求 D
```

**进程模型：**
- 每个 Worker 是独立的进程（不是线程）
- 每个 Worker 有独立的事件循环和内存空间
- 操作系统负责负载均衡（Round-Robin）
- 一个 Worker 崩溃不会影响其他 Worker

### 3. 热重载机制（开发模式）

```
主进程 (Reloader)
├── 监听文件变化 (WatchFiles)
├── 检测到文件修改
│   └── 发送信号给 Worker 进程
└── Worker 进程
    ├── 接收到信号
    ├── 关闭现有连接
    ├── 重新加载应用
    └── 继续监听请求
```

**实现原理：**
- 使用 `WatchFiles` 或 `StatReload` 监听文件系统
- 检测到变化后，优雅地重启 Worker 进程
- 确保新请求使用新代码

---

## 性能优化

### 1. Worker 数量调优

```python
import multiprocessing

# 推荐公式
workers = (2 × CPU核心数) + 1

# 示例
# 2核 CPU → 5 workers
# 4核 CPU → 9 workers
# 8核 CPU → 17 workers
```

**注意：**
- 过多 Worker 会导致上下文切换开销
- 过少 Worker 无法充分利用 CPU
- I/O 密集型应用可以适当增加

### 2. 使用 uvloop（高性能事件循环）

```bash
pip install uvloop
```

Uvicorn 会自动检测并使用 `uvloop`（如果已安装），性能提升约 **2-4倍**。

### 3. 连接池优化

```python
# app/core/config.py
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,        # 连接池大小
    max_overflow=10,     # 最大溢出连接
    pool_pre_ping=True,  # 连接前检查有效性
)
```

### 4. 日志配置

```python
# 生产环境关闭访问日志（减少 I/O）
uvicorn app.main:app --no-access-log
```

---

## 常见问题

### 1. 端口被占用

**错误信息：**
```
ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): 通常每个套接字地址(协议/网络地址/端口)只允许使用一次
```

**解决方案：**

**Windows PowerShell:**
```powershell
# 查看端口占用
Get-NetTCPConnection -LocalPort 8000

# 杀死占用进程
Stop-Process -Id <PID> -Force
```

**Linux/Mac:**
```bash
# 查看端口占用
lsof -i :8000

# 杀死占用进程
kill -9 <PID>
```

### 2. 热重载不生效

**可能原因：**
- 文件不在监听目录内
- 使用符号链接（可能需要配置）
- 文件系统不支持文件通知

**解决方案：**
```bash
# 使用 StatReload（轮询检测，兼容性更好）
uvicorn app.main:app --reload --reload-engine stat
```

### 3. Worker 进程崩溃

**现象：**
- 部分请求失败
- 日志中出现 Worker 重启信息

**排查：**
- 查看错误日志
- 检查内存使用（可能是内存泄漏）
- 检查异步代码中的异常处理

### 4. 性能问题

**症状：**
- 响应慢
- 并发能力低

**优化建议：**
1. 增加 Worker 数量（但不要过多）
2. 使用 `uvloop`
3. 优化数据库查询（使用索引、连接池）
4. 使用异步数据库驱动（如 `asyncpg`）
5. 启用 HTTP Keep-Alive

### 5. 内存占用高

**可能原因：**
- Worker 数量过多
- 内存泄漏（未关闭的连接、缓存等）
- 同步阻塞操作

**排查：**
```python
import psutil
import os

# 查看进程内存
process = psutil.Process(os.getpid())
print(f"内存使用: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

---

## 与其他服务器对比

| 特性 | Uvicorn | Gunicorn | uWSGI | Hypercorn |
|------|---------|----------|-------|-----------|
| **ASGI 支持** | ✅ | ✅ (with UvicornWorker) | ❌ | ✅ |
| **性能** | 高 | 中 | 高 | 中 |
| **配置复杂度** | 低 | 中 | 高 | 中 |
| **热重载** | ✅ | ❌ | ❌ | ✅ |
| **WebSocket** | ✅ | ✅ (with UvicornWorker) | ✅ | ✅ |
| **HTTP/2** | ❌ | ❌ | ❌ | ✅ |
| **推荐场景** | FastAPI 开发/生产 | Django 生产 | Django/Flask 生产 | HTTP/2 需求 |

---

## 总结

### 核心要点

1. **Uvicorn 是 ASGI 服务器**，支持异步 Python Web 框架
2. **Python 可以常驻运行**，通过 `asyncio` 事件循环实现
3. **开发模式**：单进程 + 热重载（`--reload`）
4. **生产模式**：多进程（`--workers 4`）
5. **性能优化**：使用 `uvloop`、合理设置 Worker 数量

### 最佳实践

- **开发环境**：使用 `--reload` 提高开发效率
- **生产环境**：使用多 Worker 模式，Worker 数量 = (2×CPU核心数)+1
- **监控和日志**：配置适当的日志级别和访问日志
- **错误处理**：确保异步代码中有完善的异常处理

### 相关文档

- [Uvicorn 官方文档](https://www.uvicorn.org/)
- [FastAPI 部署文档](https://fastapi.tiangolo.com/deployment/)
- [ASGI 规范](https://asgi.readthedocs.io/)

---

*最后更新：2025-01-XX*






