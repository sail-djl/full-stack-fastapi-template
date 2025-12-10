#!/bin/bash
# ============================================
# Jenkins 部署脚本
# 使用方法：直接复制整个脚本内容到 Jenkins Build Steps 的"执行 shell"中
# ============================================
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
    
    # 拉取指定分支（从环境变量获取，默认为 finance）
    GIT_BRANCH="${GIT_BRANCH:-finance}"
    # 移除 refs/heads/ 前缀（如果存在）
    GIT_BRANCH=${GIT_BRANCH#refs/heads/}
    GIT_BRANCH=${GIT_BRANCH#origin/}
    echo "拉取分支: ${GIT_BRANCH}"
    git checkout -f ${GIT_BRANCH} || git checkout -b ${GIT_BRANCH} origin/${GIT_BRANCH}
    git pull origin ${GIT_BRANCH} || echo "Git pull 失败或不需要更新"
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
    # 克隆指定分支（从环境变量获取，默认为 finance）
    GIT_BRANCH="${GIT_BRANCH:-finance}"
    GIT_BRANCH=${GIT_BRANCH#refs/heads/}
    GIT_BRANCH=${GIT_BRANCH#origin/}
    echo "克隆分支: ${GIT_BRANCH}"
    git clone -b ${GIT_BRANCH} https://gitee.com/hangrong_1/api.git . || {
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

# 设置生产环境配置
echo "设置生产环境配置..."
export ENV_PROFILE=production
echo "ENV_PROFILE=${ENV_PROFILE}"

# 验证 .env.production 文件是否存在
if [ ! -f "${API_DIR}/.env.production" ]; then
    echo "错误: 生产环境配置文件不存在: ${API_DIR}/.env.production"
    exit 1
fi
echo "✓ 找到生产环境配置文件: ${API_DIR}/.env.production"

# 验证配置加载（调试用）
echo "验证配置加载..."
export ENV_PROFILE=production
uv run python << 'PYTHON_SCRIPT'
import os
from app.core.config import settings
print("=" * 50)
print("配置信息（用于调试）")
print("=" * 50)
print(f'ENV_PROFILE: {os.getenv("ENV_PROFILE", "未设置")}')
print(f'ENVIRONMENT: {settings.ENVIRONMENT}')
print(f'POSTGRES_SERVER: {settings.POSTGRES_SERVER}')
print(f'POSTGRES_PORT: {settings.POSTGRES_PORT}')
print(f'POSTGRES_DB: {settings.POSTGRES_DB}')
print(f'POSTGRES_USER: {settings.POSTGRES_USER}')
print(f'FRONTEND_HOST: {settings.FRONTEND_HOST}')
print(f'数据库连接: {settings.SQLALCHEMY_DATABASE_URI}')
print("=" * 50)
PYTHON_SCRIPT

# 运行数据库迁移（使用生产环境配置）
echo "运行数据库迁移..."
export ENV_PROFILE=production
uv run python app/backend_pre_start.py
uv run alembic upgrade head
echo "数据库迁移完成"

# 检查并自动更新 systemd 服务配置（确保设置了 ENV_PROFILE=production）
echo "检查并更新 systemd 服务配置..."
SERVICE_FILE="/etc/systemd/system/finance-api.service"
if [ -f "${SERVICE_FILE}" ]; then
    if ! grep -q "Environment=\"ENV_PROFILE=production\"" "${SERVICE_FILE}"; then
        echo "检测到 systemd 服务配置中未设置 ENV_PROFILE=production，正在自动添加..."
        # 使用 sed 在 [Service] 部分后添加环境变量
        if grep -q "\[Service\]" "${SERVICE_FILE}"; then
            # 如果 [Service] 部分存在，在它后面添加环境变量（如果还没有 Environment 行）
            if ! grep -q "^Environment=" "${SERVICE_FILE}"; then
                sed -i '/\[Service\]/a Environment="ENV_PROFILE=production"' "${SERVICE_FILE}"
            else
                # 如果已有 Environment 行，检查是否需要添加
                if ! grep -q "ENV_PROFILE=production" "${SERVICE_FILE}"; then
                    sed -i '/^Environment=/a Environment="ENV_PROFILE=production"' "${SERVICE_FILE}"
                fi
            fi
            echo "✓ 已自动添加 ENV_PROFILE=production 到 systemd 服务配置"
            systemctl daemon-reload
            echo "✓ 已重新加载 systemd 配置"
        else
            echo "警告: 未找到 [Service] 部分，请手动检查服务文件"
        fi
    else
        echo "✓ systemd 服务配置已包含 ENV_PROFILE=production"
    fi
else
    echo "警告: systemd 服务文件不存在: ${SERVICE_FILE}"
fi

# 停止旧服务
echo "停止旧服务..."
systemctl stop finance-api || true
sleep 3

# 启动服务（systemd 服务应该已经配置了 ENV_PROFILE=production）
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