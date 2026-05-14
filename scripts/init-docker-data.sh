#!/bin/bash

# DUCC 评测系统 - Docker 数据目录初始化脚本
# 
# 功能：创建 Docker 数据存储目录
# 位置：/home/dejavu/docker-data/
# 
# 使用方法：
#   ./scripts/init-docker-data.sh

echo "======================================"
echo "初始化 Docker 数据目录"
echo "======================================"
echo ""

DATA_ROOT="/home/dejavu/docker-data"

# 检查目录是否已存在
if [ -d "$DATA_ROOT/postgres/data" ] && [ "$(ls -A $DATA_ROOT/postgres/data)" ]; then
    echo "⚠️  警告: PostgreSQL 数据目录已存在且非空"
    echo "位置: $DATA_ROOT/postgres/data"
    read -p "是否继续？这可能会影响现有数据 (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "操作已取消"
        exit 1
    fi
fi

# 创建目录结构
echo "创建目录结构..."
mkdir -p "$DATA_ROOT/postgres/data"
mkdir -p "$DATA_ROOT/redis/data"

# 设置权限
echo "设置目录权限..."
chmod -R 755 "$DATA_ROOT"

# 显示结果
echo ""
echo "✅ 目录创建完成！"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "数据存储位置:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PostgreSQL: $DATA_ROOT/postgres/data"
echo "  Redis:      $DATA_ROOT/redis/data"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "磁盘使用情况:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
df -h "$DATA_ROOT" 2>/dev/null || df -h /home

echo ""
echo "下一步操作:"
echo "  1. 启动 Docker 服务: docker-compose up -d"
echo "  2. 查看容器状态: docker-compose ps"
echo "  3. 查看日志: docker-compose logs -f"
