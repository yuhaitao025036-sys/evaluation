#!/bin/bash
# Backend Service Startup Script

set -e

echo "======================================"
echo "启动 Agent Evaluation Backend API"
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
    echo "已创建 .env 文件，请检查配置是否正确"
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
python -c "from redis import Redis; from app.config import settings; Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT).ping()" 2>/dev/null || {
    echo "错误: 无法连接到 Redis"
    echo "请确保 Redis 已启动: cd .. && docker-compose up -d redis"
    exit 1
}

echo ""
echo "✓ 环境检查通过"
echo ""
echo "启动 Backend API 服务..."
echo "访问地址: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo "======================================"
echo ""

# Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
