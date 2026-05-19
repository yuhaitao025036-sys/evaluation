#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================"
echo "启动前端开发服务器"
echo "======================================"
echo ""

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 未检测到 Node.js，请先安装 Node.js (v16+)"
    exit 1
fi

NODE_VERSION=$(node -v)
echo "✅ Node.js 版本: $NODE_VERSION"
echo ""

# 检查 npm
if ! command -v npm &> /dev/null; then
    echo "❌ 未检测到 npm，请先安装 npm"
    exit 1
fi

NPM_VERSION=$(npm -v)
echo "✅ npm 版本: $NPM_VERSION"
echo ""

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo "⚠️  未检测到 node_modules 目录，开始安装依赖..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
    echo "✅ 依赖安装成功"
    echo ""
fi

# 启动开发服务器
echo "======================================"
echo "正在启动 Vite 开发服务器..."
echo "访问地址: http://localhost:5173"
echo "API 代理: http://localhost:8080"
echo "======================================"
echo ""

npm run dev
