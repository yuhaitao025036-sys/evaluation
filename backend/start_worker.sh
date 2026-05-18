#!/bin/bash
# RQ Worker Startup Script

set -e

echo "======================================"
echo "启动 Agent Evaluation Worker"
echo "======================================"
echo ""

# Initialize conda for bash
eval "$(conda shell.bash hook)"

# Check if conda environment exists
if ! conda env list | grep -q "^dejavu "; then
    echo "错误: conda 环境 'dejavu' 不存在"
    echo "请创建环境: conda create -n dejavu python=3.12"
    echo "或运行: ./install.sh"
    exit 1
fi

# Activate conda environment
echo "激活 conda 环境 dejavu..."
conda activate dejavu

# Check Python version
PYTHON_VERSION=$(python --version 2>&1)
echo "Python 版本: ${PYTHON_VERSION}"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "警告: .env 文件不存在，使用 .env.example 创建..."
    cp .env.example .env
fi

# Check database connection
echo "检查数据库连接..."
python -c "from app.database import engine; engine.connect()" 2>/dev/null || {
    echo "错误: 无法连接到数据库"
    echo "请确保 PostgreSQL 已启动: cd .. && docker-compose up -d postgres"
    exit 1
}

# Check Redis connection
echo "检查 Redis 连接..."
python -c "from redis import Redis; from app.config import settings; Redis.from_url(settings.REDIS_URL).ping()" 2>/dev/null || {
    echo "错误: 无法连接到 Redis"
    echo "请确保 Redis 已启动: cd .. && docker-compose up -d redis"
    exit 1
}

# Check Docker access
echo "检查 Docker 访问..."
docker ps >/dev/null 2>&1 || {
    echo "错误: 无法访问 Docker"
    echo "Worker 需要 Docker 来运行评估任务"
    echo "请确保:"
    echo "  1. Docker 已安装并运行"
    echo "  2. 当前用户有 Docker 权限"
    exit 1
}

echo ""
echo "✓ 环境检查通过"
echo ""
echo "启动 RQ Worker..."
echo "队列: ducc_tasks"
echo ""
echo "按 Ctrl+C 停止服务"
echo "======================================"
echo ""

# Start worker
python worker.py
