# uv - 现代 Python 包管理器

## 什么是 uv？

**uv** 是由 [Astral](https://astral.sh/) 开发的极速 Python 包管理器和项目管理工具，用 Rust 编写。它是 pip、pip-tools、virtualenv、pipx、pyenv、twine、poetry 等工具的超快替代品。

## 为什么使用 uv？

### 主要优势

1. **极快的速度** ⚡
   - 比 pip 快 10-100 倍
   - 比 pip-tools 快 10-100 倍
   - 比 Poetry 快 10-100 倍
   - 用 Rust 编写，性能优异

2. **统一工具** 🛠️
   - 替代多个工具：pip、virtualenv、pipx、pyenv 等
   - 一个命令完成多个操作
   - 减少工具链复杂度

3. **兼容性** ✅
   - 兼容 pip 和 pip-tools
   - 兼容 pyproject.toml 标准
   - 兼容现有的 Python 项目

4. **现代化** 🚀
   - 支持最新的 Python 包管理标准
   - 自动处理依赖解析
   - 支持锁定文件（uv.lock）

## 安装 uv

### Windows

```powershell
# 使用 PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用 pip
pip install uv
```

### macOS / Linux

```bash
# 使用 curl
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip
pip install uv
```

### 验证安装

```bash
uv --version
```

## 在本项目中的使用

### 项目配置

本项目使用 `uv` 作为包管理器，配置文件：

- **pyproject.toml**: 项目配置和依赖声明
- **uv.lock**: 锁定文件，确保依赖版本一致性

### 基本命令

#### 1. 安装依赖

```bash
# 同步依赖（安装所有依赖）
uv sync

# 同步并安装项目本身
uv sync --install-project
```

**说明**：
- `uv sync` 会根据 `pyproject.toml` 和 `uv.lock` 安装依赖
- 自动创建虚拟环境（`.venv`）
- 如果 `uv.lock` 不存在，会自动生成

#### 2. 激活虚拟环境

```bash
# 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# 或直接使用 uv 运行命令（无需激活）
uv run python app/main.py
```

#### 3. 添加依赖

```bash
# 添加生产依赖
uv add fastapi

# 添加开发依赖
uv add --dev pytest

# 添加带版本的依赖
uv add "fastapi>=0.100.0"
```

#### 4. 移除依赖

```bash
# 移除依赖
uv remove fastapi
```

#### 5. 更新依赖

```bash
# 更新所有依赖
uv sync --upgrade

# 更新特定依赖
uv add --upgrade fastapi
```

#### 6. 锁定依赖

```bash
# 更新锁定文件
uv lock

# 仅锁定，不安装
uv lock --no-install
```

## 项目中的 uv 配置

### pyproject.toml 配置

```toml
[project]
name = "app"
version = "0.1.0"
requires-python = ">=3.10,<4.0"
dependencies = [
    "fastapi[standard]<1.0.0,>=0.114.2",
    "sqlmodel<1.0.0,>=0.0.21",
    # ... 其他依赖
]

[tool.uv]
dev-dependencies = [
    "pytest<8.0.0,>=7.4.3",
    "mypy<2.0.0,>=1.8.0",
    "ruff<1.0.0,>=0.2.2",
    # ... 其他开发依赖
]
```

### uv.lock 文件

- 自动生成的锁定文件
- 记录所有依赖的确切版本
- 确保团队环境一致性
- **应该提交到 Git**

## Docker 中的使用

### Dockerfile 配置

项目在 Docker 中使用 uv，配置如下：

```dockerfile
# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

# 设置环境变量
ENV PATH="/app/.venv/bin:$PATH"
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# 安装依赖（使用缓存）
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

# 同步项目
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync
```

### Docker 优化

1. **使用缓存**：`--mount=type=cache,target=/root/.cache/uv`
   - 加速后续构建
   - 复用已下载的包

2. **冻结模式**：`--frozen`
   - 使用 `uv.lock` 精确安装
   - 确保生产环境一致性

3. **字节码编译**：`UV_COMPILE_BYTECODE=1`
   - 预编译 Python 字节码
   - 提升运行时性能

## 常用工作流

### 本地开发

```bash
# 1. 克隆项目
git clone <repository>
cd backend

# 2. 安装依赖
uv sync

# 3. 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows

# 4. 运行应用
python app/main.py
# 或使用 uv
uv run python app/main.py
```

### 添加新依赖

```bash
# 1. 添加依赖
uv add requests

# 2. 提交更改
git add pyproject.toml uv.lock
git commit -m "Add requests dependency"
```

### 更新依赖

```bash
# 1. 更新所有依赖
uv sync --upgrade

# 2. 更新锁定文件
uv lock

# 3. 测试应用
uv run pytest

# 4. 提交更改
git add pyproject.toml uv.lock
git commit -m "Update dependencies"
```

### 运行脚本

```bash
# 使用 uv 运行 Python 脚本（无需激活虚拟环境）
uv run python script.py

# 运行测试
uv run pytest

# 运行代码检查
uv run ruff check .
uv run mypy app/
```

## uv vs 其他工具

### uv vs pip

| 特性 | pip | uv |
|------|-----|-----|
| 速度 | 慢 | **快 10-100 倍** |
| 依赖解析 | 基础 | **智能解析** |
| 锁定文件 | 需要 pip-tools | **内置支持** |
| 虚拟环境 | 需要 venv | **内置支持** |

### uv vs Poetry

| 特性 | Poetry | uv |
|------|--------|-----|
| 速度 | 慢 | **快 10-100 倍** |
| 锁定文件 | poetry.lock | **uv.lock** |
| 配置格式 | pyproject.toml | **pyproject.toml** |
| 兼容性 | 中等 | **完全兼容** |

### uv vs pip-tools

| 特性 | pip-tools | uv |
|------|-----------|-----|
| 速度 | 慢 | **快 10-100 倍** |
| 命令 | 多个命令 | **统一命令** |
| 锁定文件 | requirements.txt | **uv.lock** |

## 高级用法

### 1. 管理多个 Python 版本

```bash
# 安装特定 Python 版本
uv python install 3.11

# 使用特定版本
uv run --python 3.11 python app/main.py
```

### 2. 创建独立应用

```bash
# 类似 pipx，创建独立环境运行应用
uv tool install black
uv tool run black .
```

### 3. 发布包

```bash
# 构建包
uv build

# 发布到 PyPI
uv publish
```

### 4. 环境变量

```bash
# 设置 uv 缓存目录
export UV_CACHE_DIR=/path/to/cache

# 设置 Python 路径
export UV_PYTHON=/path/to/python
```

## 故障排除

### 问题 1: 找不到 uv 命令

**解决方案**：
```bash
# 检查是否安装
which uv  # Linux/macOS
where uv  # Windows

# 重新安装
pip install uv
```

### 问题 2: 依赖安装失败

**解决方案**：
```bash
# 清理缓存
uv cache clean

# 重新同步
uv sync --reinstall
```

### 问题 3: 锁定文件冲突

**解决方案**：
```bash
# 更新锁定文件
uv lock

# 检查差异
git diff uv.lock
```

### 问题 4: Docker 构建慢

**解决方案**：
- 确保使用缓存：`--mount=type=cache,target=/root/.cache/uv`
- 使用 `--frozen` 模式
- 检查网络连接

## 最佳实践

### 1. 版本控制

✅ **应该提交**：
- `pyproject.toml`
- `uv.lock`

❌ **不应该提交**：
- `.venv/` (虚拟环境目录)
- `__pycache__/` (Python 缓存)

### 2. 依赖管理

✅ **推荐做法**：
- 使用版本范围：`"fastapi>=0.100.0,<1.0.0"`
- 定期更新依赖
- 测试更新后的依赖

❌ **不推荐**：
- 使用 `*` 通配符
- 忽略锁定文件
- 手动编辑 `uv.lock`

### 3. 团队协作

✅ **推荐做法**：
- 所有成员使用相同版本的 uv
- 提交 `uv.lock` 文件
- 使用 `uv sync --frozen` 确保一致性

### 4. CI/CD

```yaml
# GitHub Actions 示例
- name: Install uv
  run: pip install uv

- name: Install dependencies
  run: uv sync --frozen

- name: Run tests
  run: uv run pytest
```

## 性能对比

### 安装速度对比（示例项目）

| 工具 | 时间 |
|------|------|
| pip | ~45 秒 |
| pip-tools | ~60 秒 |
| Poetry | ~90 秒 |
| **uv** | **~3 秒** ⚡ |

### 依赖解析速度

- uv 的依赖解析算法比 pip 快 100 倍以上
- 使用 Rust 实现，性能优异

## 迁移指南

### 从 pip 迁移

```bash
# 1. 安装 uv
pip install uv

# 2. 初始化项目
uv init

# 3. 添加现有依赖
uv add $(cat requirements.txt)

# 4. 测试
uv run pytest
```

### 从 Poetry 迁移

```bash
# 1. 安装 uv
pip install uv

# 2. uv 可以直接读取 pyproject.toml
uv sync

# 3. 生成 uv.lock
uv lock
```

## 官方资源

- **官方网站**: https://astral.sh/uv
- **文档**: https://docs.astral.sh/uv/
- **GitHub**: https://github.com/astral-sh/uv
- **Docker 集成**: https://docs.astral.sh/uv/guides/integration/docker/

## 总结

**uv** 是一个现代化的 Python 包管理器，具有以下特点：

1. ⚡ **极快的速度** - 比传统工具快 10-100 倍
2. 🛠️ **统一工具** - 替代多个工具
3. ✅ **完全兼容** - 兼容现有 Python 生态系统
4. 🚀 **现代化** - 支持最新的 Python 标准

在本项目中，uv 用于：
- 管理 Python 依赖
- 创建和管理虚拟环境
- 在 Docker 中快速安装依赖
- 确保团队环境一致性

使用 uv 可以显著提升开发效率和构建速度！

