#!/bin/bash

# Agent 评测系统 - Docker 数据迁移脚本
# 
# 功能：从旧的 Docker 命名卷迁移数据到新的宿主机目录
# 目标：/home/dejavu/docker-data/
# 
# 使用方法：
#   ./scripts/migrate-docker-data.sh

echo "======================================"
echo "迁移 Docker 数据到新位置"
echo "======================================"
echo ""

NEW_DATA_ROOT="/home/dejavu/docker-data"
OLD_POSTGRES_VOLUME="evaluation_postgres_data"
OLD_REDIS_VOLUME="evaluation_redis_data"

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker"
    exit 1
fi

# 检查旧卷是否存在
POSTGRES_EXISTS=$(docker volume ls -q | grep "^${OLD_POSTGRES_VOLUME}$")
REDIS_EXISTS=$(docker volume ls -q | grep "^${OLD_REDIS_VOLUME}$")

if [ -z "$POSTGRES_EXISTS" ] && [ -z "$REDIS_EXISTS" ]; then
    echo "⚠️  未找到旧的数据卷，无需迁移"
    echo ""
    echo "提示：如果这是首次部署，请直接执行:"
    echo "  ./scripts/init-docker-data.sh"
    echo "  docker-compose up -d"
    exit 0
fi

echo "发现以下旧数据卷:"
[ -n "$POSTGRES_EXISTS" ] && echo "  ✓ $OLD_POSTGRES_VOLUME"
[ -n "$REDIS_EXISTS" ] && echo "  ✓ $OLD_REDIS_VOLUME"
echo ""

read -p "确认开始迁移？(y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "操作已取消"
    exit 1
fi

# 步骤 1: 停止容器
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 1: 停止 Docker 容器"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker-compose down
echo "✅ 容器已停止"

# 步骤 2: 创建新目录
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 2: 创建新数据目录"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
mkdir -p "$NEW_DATA_ROOT/postgres/data"
mkdir -p "$NEW_DATA_ROOT/redis/data"
echo "✅ 目录创建完成"

# 步骤 3: 迁移 PostgreSQL 数据
if [ -n "$POSTGRES_EXISTS" ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "步骤 3: 迁移 PostgreSQL 数据"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "这可能需要几分钟，请稍候..."
    
    docker run --rm \
      -v "$OLD_POSTGRES_VOLUME":/source \
      -v "$NEW_DATA_ROOT/postgres/data":/target \
      alpine sh -c "cp -a /source/. /target/ && echo '✅ PostgreSQL 数据迁移完成'"
    
    if [ $? -ne 0 ]; then
        echo "❌ PostgreSQL 数据迁移失败"
        exit 1
    fi
    
    # 显示数据大小
    POSTGRES_SIZE=$(du -sh "$NEW_DATA_ROOT/postgres/data" 2>/dev/null | cut -f1)
    echo "数据大小: $POSTGRES_SIZE"
fi

# 步骤 4: 迁移 Redis 数据
if [ -n "$REDIS_EXISTS" ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "步骤 4: 迁移 Redis 数据"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    docker run --rm \
      -v "$OLD_REDIS_VOLUME":/source \
      -v "$NEW_DATA_ROOT/redis/data":/target \
      alpine sh -c "cp -a /source/. /target/ && echo '✅ Redis 数据迁移完成'"
    
    if [ $? -ne 0 ]; then
        echo "❌ Redis 数据迁移失败"
        exit 1
    fi
    
    # 显示数据大小
    REDIS_SIZE=$(du -sh "$NEW_DATA_ROOT/redis/data" 2>/dev/null | cut -f1)
    echo "数据大小: $REDIS_SIZE"
fi

# 步骤 5: 设置权限
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 5: 设置目录权限"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
chmod -R 755 "$NEW_DATA_ROOT"
echo "✅ 权限设置完成"

# 完成
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 数据迁移完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "新数据位置:"
echo "  PostgreSQL: $NEW_DATA_ROOT/postgres/data"
echo "  Redis:      $NEW_DATA_ROOT/redis/data"
echo ""
echo "磁盘使用情况:"
df -h "$NEW_DATA_ROOT"
echo ""
echo "下一步操作:"
echo "  1. 启动服务: docker-compose up -d"
echo "  2. 验证数据: docker exec ducc_postgres psql -U ducc_user ducc_evaluation -c '\\dt'"
echo "  3. 确认无误后删除旧卷:"
[ -n "$POSTGRES_EXISTS" ] && echo "     docker volume rm $OLD_POSTGRES_VOLUME"
[ -n "$REDIS_EXISTS" ] && echo "     docker volume rm $OLD_REDIS_VOLUME"
