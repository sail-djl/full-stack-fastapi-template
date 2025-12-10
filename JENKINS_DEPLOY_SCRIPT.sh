#!/bin/bash
set -e

echo "=========================================="
echo "开始部署 API 项目"
echo "构建号: ${BUILD_NUMBER}"
echo "Jenkins 工作目录: $(pwd)"
echo "=========================================="

# SSH 配置（使用密钥文件）
SSH_HOST="192.168.31.150"
SSH_USER="root"
SSH_KEY="/var/jenkins_home/.ssh/jenkins_key"

# 检查密钥文件
if [ ! -f "${SSH_KEY}" ]; then
    echo "错误: SSH 密钥文件不存在: ${SSH_KEY}"
    exit 1
fi

echo "使用 SSH 密钥文件: ${SSH_KEY}"
echo ""

# 在宿主机上执行构建
ssh -i "${SSH_KEY}" \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "${SSH_USER}@${SSH_HOST}" << 'ENDSSH'
set -e

# 项目路径
API_DIR="/root/finance/api"
BACKEND_DIR="${API_DIR}/backend"

echo "=========================================="
echo "在宿主机上执行构建"
echo "当前目录: $(pwd)"
echo "=========================================="

# 检查环境
echo "检查环境..."
export PATH="$HOME/.cargo/bin:$PATH"
python3 --version
uv --version
echo ""

# 处理代码目录
echo "处理代码目录..."
mkdir -p ${API_DIR}
cd ${API_DIR}

# 如果是 git 仓库，更新代码
if [ -d ".git" ]; then
    echo "检测到现有 git 仓库，更新代码..."
    git fetch origin
    
    # 清理未跟踪的文件（如 .env.staging），避免切换分支时冲突
    echo "清理未跟踪的文件..."
    git clean -fd || true
    
    # 修改：拉取 finance_test 分支（使用 -f 强制切换）
    git checkout -f finance_test || git checkout -b finance_test origin/finance_test
    git pull origin finance_test || echo "Git pull 失败或不需要更新"
else
    # 如果不是 git 仓库，克隆
    echo "代码不存在，开始克隆..."
    # 如果目录不为空，先清理
    if [ "$(ls -A . 2>/dev/null)" ]; then
        echo "目录不为空，清理旧文件..."
        cd /root
        rm -rf ${API_DIR}
        mkdir -p ${API_DIR}
        cd ${API_DIR}
    fi
    # 修改：克隆 finance_test 分支
    git clone -b finance_test https://gitee.com/hangrong_1/api.git . || {
        echo "错误: Git 克隆失败"
        exit 1
    }
    echo "✓ 代码克隆完成"
fi

# 显示当前分支和最新提交
echo "当前分支: $(git branch --show-current)"
echo "最新提交: $(git log -1 --oneline)"

# 进入 backend 目录
cd ${BACKEND_DIR}
echo "当前目录: $(pwd)"

# 安装/更新依赖
echo "安装项目依赖..."
uv sync
echo "依赖安装完成"

# 验证配置加载（调试用）- 不需要设置 ENV_PROFILE，使用代码中的默认值
echo "验证配置加载..."
uv run python << 'PYTHON_SCRIPT'
import os
from app.core.config import settings
print("=" * 50)
print("配置信息（用于调试）")
print("=" * 50)
print(f'ENV_PROFILE: {os.getenv("ENV_PROFILE", "未设置（使用代码默认值）")}')
print(f'POSTGRES_SERVER: {settings.POSTGRES_SERVER}')
print(f'POSTGRES_DB: {settings.POSTGRES_DB}')
print(f'POSTGRES_USER: {settings.POSTGRES_USER}')
print(f'ENVIRONMENT: {settings.ENVIRONMENT}')
print(f'数据库连接: {settings.SQLALCHEMY_DATABASE_URI}')
print("=" * 50)
PYTHON_SCRIPT

# 运行数据库迁移
echo "运行数据库迁移..."
uv run python app/backend_pre_start.py
uv run alembic upgrade head
echo "数据库迁移完成"

# 停止旧服务
echo "停止旧服务..."
systemctl stop finance-api || true
sleep 3

# 启动服务
echo "启动服务..."
systemctl start finance-api
sleep 5

# 检查服务状态
echo "检查服务状态..."
systemctl status finance-api --no-pager || true

# 健康检查
echo "执行健康检查..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -f http://localhost:8000/api/v1/utils/health-check/ 2>/dev/null; then
        echo "✓ 服务健康检查通过"
        break
    fi
    attempt=$((attempt + 1))
    echo "等待服务启动... ($attempt/$max_attempts)"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "✗ 服务健康检查失败"
    journalctl -u finance-api --no-pager -n 50
    exit 1
fi

echo "✓ API 部署完成！"
ENDSSH

echo "=========================================="
echo "✓ 部署流程完成！"
echo "构建号: ${BUILD_NUMBER}"
echo "服务地址: http://192.168.31.150:8000"
echo "健康检查: http://192.168.31.150:8000/api/v1/utils/health-check/"
echo "=========================================="

