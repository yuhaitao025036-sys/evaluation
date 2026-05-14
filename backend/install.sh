#!/bin/bash
# DUCC Evaluation System - Installation Script
# 
# This script installs all dependencies for the backend services
# Backend and Worker will run on host machine with conda environment

set -e

echo "=========================================="
echo "DUCC Evaluation System - 安装脚本"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
echo "检查系统要求..."
echo ""

# Check conda
if ! command -v conda &> /dev/null; then
    echo -e "${RED}✗ Conda 未安装${NC}"
    echo "请安装 Anaconda 或 Miniconda"
    echo "  Miniconda: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

CONDA_VERSION=$(conda --version 2>&1)
echo -e "${GREEN}✓ ${CONDA_VERSION}${NC}"

# Initialize conda for bash
eval "$(conda shell.bash hook)"

# Check if dejavu environment exists
if conda env list | grep -q "^dejavu "; then
    echo -e "${GREEN}✓ Conda 环境 'dejavu' 已存在${NC}"
    DEJAVU_EXISTS=true
else
    echo -e "${YELLOW}⚠ Conda 环境 'dejavu' 不存在${NC}"
    DEJAVU_EXISTS=false
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠ Docker 未安装${NC}"
    echo "  Worker 需要 Docker 来运行评估任务"
    echo "  请从 https://www.docker.com/get-started 安装 Docker"
else
    echo -e "${GREEN}✓ Docker${NC}"
    # Check Docker daemon
    if docker ps &> /dev/null; then
        echo -e "${GREEN}✓ Docker daemon 运行中${NC}"
    else
        echo -e "${YELLOW}⚠ Docker daemon 未运行${NC}"
        echo "  请启动 Docker"
    fi
fi

# Check docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}⚠ docker-compose 未安装${NC}"
    echo "  需要 docker-compose 来运行 PostgreSQL 和 Redis"
    echo "  请安装 docker-compose"
else
    echo -e "${GREEN}✓ docker-compose${NC}"
fi

echo ""
echo "=========================================="
echo "安装步骤"
echo "=========================================="
echo ""

# Step 1: Create or verify conda environment
if [ "$DEJAVU_EXISTS" = false ]; then
    echo "步骤 1/4: 创建 Conda 环境..."
    read -p "是否创建 conda 环境 'dejavu' (Python 3.12)? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        conda create -n dejavu python=3.12 -y
        echo -e "${GREEN}  ✓ Conda 环境 'dejavu' 创建完成${NC}"
    else
        echo -e "${YELLOW}  跳过环境创建${NC}"
        echo "  请手动创建: conda create -n dejavu python=3.12"
    fi
else
    echo "步骤 1/4: 验证 Conda 环境..."
    conda activate dejavu
    PYTHON_VERSION=$(python --version 2>&1)
    echo -e "${GREEN}  ✓ 环境已存在: ${PYTHON_VERSION}${NC}"
fi

# Activate dejavu environment for remaining steps
conda activate dejavu

# Step 2: Upgrade pip
echo ""
echo "步骤 2/4: 升级 pip..."
pip install --upgrade pip setuptools wheel -q
echo -e "${GREEN}  ✓ pip 已升级${NC}"

# Step 3: Install dependencies
echo ""
echo "步骤 3/4: 安装 Python 依赖..."
echo "  这可能需要几分钟时间..."

# Check if user wants to use conda or pip
read -p "使用 conda 安装依赖? (推荐使用 pip: n) (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "  使用 conda 安装主要依赖..."
    conda install -y fastapi uvicorn sqlalchemy psycopg2 redis-py pandas pyarrow websockets pydantic
    echo "  使用 pip 安装剩余依赖..."
    pip install -r requirements.txt -q
else
    echo "  使用 pip 安装所有依赖..."
    pip install -r requirements.txt -q
fi

echo -e "${GREEN}  ✓ Python 依赖安装完成${NC}"

# Step 4: Setup environment file
echo ""
echo "步骤 4/4: 配置环境变量..."
if [ -f ".env" ]; then
    echo "  .env 文件已存在，跳过"
else
    cp .env.example .env
    echo -e "${GREEN}  ✓ 已创建 .env 文件${NC}"
    echo -e "${YELLOW}  ⚠ 请检查并修改 .env 文件中的配置${NC}"
fi

# Create data directories
echo ""
echo "创建数据目录..."
cd ..
mkdir -p data/datasets data/scripts data/outputs
echo -e "${GREEN}  ✓ 数据目录创建完成${NC}"
cd backend

echo ""
echo "=========================================="
echo "✓ 安装完成！"
echo "=========================================="
echo ""
echo "Conda 环境: dejavu"
echo "Python 版本: $(python --version)"
echo ""
echo "下一步:"
echo ""
echo "1. 启动数据库服务:"
echo "   cd .."
echo "   docker-compose up -d"
echo ""
echo "2. 初始化数据库:"
echo "   cd backend"
echo "   conda activate dejavu"
echo "   python init_db.py"
echo ""
echo "3. 启动后端服务:"
echo "   ./start_backend.sh"
echo ""
echo "4. 启动 Worker (新终端):"
echo "   cd backend"
echo "   ./start_worker.sh"
echo ""
echo "访问 API 文档: http://localhost:8000/docs"
echo ""
echo "=========================================="
