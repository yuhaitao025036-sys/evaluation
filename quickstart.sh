#!/bin/bash

# DUCC Evaluation System - Quick Start Script
# 
# Architecture: Hybrid Deployment
# - PostgreSQL & Redis: Docker containers
# - Backend & Worker: Host processes
# - Evaluation tasks: Docker (called by Worker)

set -e  # Exit on error

echo "🚀 DUCC Evaluation System - Quick Start"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running from correct directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: Please run this script from the evaluation directory${NC}"
    echo "  cd /Users/yuhaitao01/dev/baidu/explore/test/evaluation"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "📋 Checking prerequisites..."
echo ""

MISSING_DEPS=false

# Check Conda
if ! command_exists conda; then
    echo -e "${RED}✗ Conda not found${NC}"
    echo "  Install: https://docs.conda.io/en/latest/miniconda.html"
    MISSING_DEPS=true
else
    CONDA_VERSION=$(conda --version 2>&1)
    echo -e "${GREEN}✓ ${CONDA_VERSION}${NC}"
    
    # Check if dejavu environment exists
    if conda env list | grep -q "^dejavu "; then
        echo -e "${GREEN}  Conda environment 'dejavu' exists${NC}"
    else
        echo -e "${YELLOW}  ⚠ Conda environment 'dejavu' not found${NC}"
        echo "    Will be created during installation"
    fi
fi

# Check Docker
if ! command_exists docker; then
    echo -e "${RED}✗ Docker not found${NC}"
    echo "  Install: https://docs.docker.com/get-docker/"
    MISSING_DEPS=true
else
    echo -e "${GREEN}✓ Docker found${NC}"
    if docker ps >/dev/null 2>&1; then
        echo -e "${GREEN}  Docker daemon running${NC}"
    else
        echo -e "${YELLOW}  ⚠ Docker daemon not running${NC}"
    fi
fi

# Check docker-compose
if ! command_exists docker-compose; then
    echo -e "${RED}✗ Docker Compose not found${NC}"
    echo "  Install: https://docs.docker.com/compose/install/"
    MISSING_DEPS=true
else
    echo -e "${GREEN}✓ Docker Compose found${NC}"
fi

echo ""

if [ "$MISSING_DEPS" = true ]; then
    echo -e "${RED}❌ Missing required dependencies. Please install them first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites met!${NC}"
echo ""

# Prepare data directories
echo "📂 Preparing data directories..."
mkdir -p data/{datasets,scripts,outputs}
chmod 755 data/{datasets,scripts,outputs}
echo -e "${GREEN}✓ Data directories ready${NC}"
echo ""

# Step 1: Start database services
echo "=========================================="
echo "Step 1: Database Services"
echo "=========================================="
echo ""

read -p "Start PostgreSQL and Redis with Docker? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting database services..."
    docker-compose up -d
    
    echo ""
    echo "⏳ Waiting for databases to be ready..."
    sleep 5
    
    # Check PostgreSQL
    if docker exec ducc_postgres pg_isready -U ducc >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL ready${NC}"
    else
        echo -e "${YELLOW}⚠ PostgreSQL not ready yet${NC}"
    fi
    
    # Check Redis
    if docker exec ducc_redis redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis ready${NC}"
    else
        echo -e "${YELLOW}⚠ Redis not ready yet${NC}"
    fi
else
    echo "Skipped. Start manually with:"
    echo "  docker-compose up -d"
fi

echo ""

# Step 2: Install Python dependencies
echo "=========================================="
echo "Step 2: Python Dependencies"
echo "=========================================="
echo ""

# Initialize conda
eval "$(conda shell.bash hook)"

# Check if dejavu environment exists
if ! conda env list | grep -q "^dejavu "; then
    read -p "Install Python dependencies? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd backend
        ./install.sh
        cd ..
        echo -e "${GREEN}✓ Python dependencies installed${NC}"
    else
        echo "Skipped. Install manually with:"
        echo "  cd backend && ./install.sh"
    fi
else
    echo -e "${GREEN}✓ Conda environment 'dejavu' already exists${NC}"
    conda activate dejavu
    PYTHON_VERSION=$(python --version 2>&1)
    echo -e "${GREEN}  ${PYTHON_VERSION}${NC}"
fi

echo ""

# Step 3: Initialize database
echo "=========================================="
echo "Step 3: Database Initialization"
echo "=========================================="
echo ""

read -p "Initialize database tables? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd backend
    # Check if dejavu environment exists
    if conda env list | grep -q "^dejavu "; then
        conda activate dejavu
        python init_db.py
        echo -e "${GREEN}✓ Database initialized${NC}"
    else
        echo -e "${RED}✗ Conda environment 'dejavu' not found${NC}"
        echo "  Run: cd backend && ./install.sh"
    fi
    cd ..
else
    echo "Skipped. Initialize manually with:"
    echo "  cd backend && conda activate dejavu && python init_db.py"
fi

echo ""

# Copy test files
read -p "📦 Copy test script and dataset? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Copy test script
    if [ -f "../test_tmux_cc_experience.py" ]; then
        cp ../test_tmux_cc_experience.py data/scripts/
        echo -e "${GREEN}✓ Copied test_tmux_cc_experience.py${NC}"
    elif [ -f "test_tmux_cc_experience.py" ]; then
        cp test_tmux_cc_experience.py data/scripts/
        echo -e "${GREEN}✓ Copied test_tmux_cc_experience.py${NC}"
    else
        echo -e "${YELLOW}⚠ test_tmux_cc_experience.py not found, skipping${NC}"
    fi
    
    # Copy dataset
    if ls ../datasets/*.parquet 1> /dev/null 2>&1; then
        cp ../datasets/*.parquet data/datasets/
        echo -e "${GREEN}✓ Copied dataset files${NC}"
    else
        echo -e "${YELLOW}⚠ No .parquet files found, skipping${NC}"
    fi
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "=========================================="
echo ""

echo -e "${BLUE}📍 Architecture:${NC}"
echo "  宿主机"
echo "  ├── PostgreSQL (Docker)   ← 已启动"
echo "  ├── Redis (Docker)        ← 已启动"
echo "  ├── Backend API (宿主机)  ← 需要启动"
echo "  ├── RQ Worker (宿主机)    ← 需要启动"
echo "  └── 评估任务 (Docker)     ← Worker 调用"
echo ""

echo -e "${BLUE}📚 Next Steps:${NC}"
echo ""
echo "1️⃣  启动 Backend API (新终端):"
echo "   cd backend"
echo "   ./start_backend.sh"
echo "   访问: http://localhost:8000/docs"
echo ""

echo "2️⃣  启动 Worker (新终端):"
echo "   cd backend"
echo "   ./start_worker.sh"
echo ""

echo "3️⃣  使用 API 测试系统:"
echo "   查看文档: docs/API_TESTING.md"
echo "   查看安装指南: docs/INSTALLATION.md"
echo ""

echo -e "${BLUE}🛠 管理命令:${NC}"
echo ""
echo "停止数据库:"
echo "  docker-compose down"
echo ""
echo "查看数据库日志:"
echo "  docker-compose logs -f"
echo ""
echo "重启数据库:"
echo "  docker-compose restart"
echo ""

echo -e "${GREEN}祝使用愉快！${NC}"
echo ""
