#!/bin/bash

# Agent 评测系统 - Docker 数据检查脚本
# 
# 功能：检查 Docker 数据存储状态和磁盘使用情况
# 
# 使用方法：
#   ./scripts/check-docker-data.sh

DOCKER_DATA="/home/dejavu/docker-data"

echo "======================================"
echo "Agent 评测系统数据检查"
echo "======================================"
echo "检查时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 检查目录是否存在
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. 目录结构检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -d "$DOCKER_DATA" ]; then
    echo "❌ 数据根目录不存在: $DOCKER_DATA"
    echo ""
    echo "请先运行初始化脚本:"
    echo "  ./scripts/init-docker-data.sh"
    exit 1
fi

echo "✅ 数据根目录: $DOCKER_DATA"

if [ -d "$DOCKER_DATA/postgres/data" ]; then
    echo "✅ PostgreSQL 数据目录存在"
else
    echo "❌ PostgreSQL 数据目录不存在"
fi

if [ -d "$DOCKER_DATA/redis/data" ]; then
    echo "✅ Redis 数据目录存在"
else
    echo "❌ Redis 数据目录不存在"
fi

# 检查数据大小
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. 数据大小统计"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -d "$DOCKER_DATA/postgres/data" ]; then
    POSTGRES_SIZE=$(du -sh "$DOCKER_DATA/postgres/data" 2>/dev/null | cut -f1)
    POSTGRES_FILES=$(find "$DOCKER_DATA/postgres/data" -type f 2>/dev/null | wc -l)
    echo "PostgreSQL:"
    echo "  大小: $POSTGRES_SIZE"
    echo "  文件数: $POSTGRES_FILES"
fi

if [ -d "$DOCKER_DATA/redis/data" ]; then
    REDIS_SIZE=$(du -sh "$DOCKER_DATA/redis/data" 2>/dev/null | cut -f1)
    REDIS_FILES=$(find "$DOCKER_DATA/redis/data" -type f 2>/dev/null | wc -l)
    echo "Redis:"
    echo "  大小: $REDIS_SIZE"
    echo "  文件数: $REDIS_FILES"
fi

TOTAL_SIZE=$(du -sh "$DOCKER_DATA" 2>/dev/null | cut -f1)
echo ""
echo "总计: $TOTAL_SIZE"

# 检查磁盘空间
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. 磁盘空间情况"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

df -h "$DOCKER_DATA" 2>/dev/null || df -h /home

# 空间使用率警告
USAGE=$(df "$DOCKER_DATA" 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$USAGE" -gt 80 ]; then
    echo ""
    echo "⚠️  警告: 磁盘使用率超过 80%，建议清理数据或扩展存储"
elif [ "$USAGE" -gt 90 ]; then
    echo ""
    echo "🚨 严重警告: 磁盘使用率超过 90%，请立即清理！"
fi

# 检查 Docker 容器状态
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. Docker 容器状态"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker ps > /dev/null 2>&1; then
    POSTGRES_STATUS=$(docker ps -f name=eval_postgres --format "{{.Status}}" 2>/dev/null)
    REDIS_STATUS=$(docker ps -f name=eval_redis --format "{{.Status}}" 2>/dev/null)
    
    if [ -n "$POSTGRES_STATUS" ]; then
        echo "✅ PostgreSQL: $POSTGRES_STATUS"
    else
        echo "❌ PostgreSQL: 未运行"
    fi
    
    if [ -n "$REDIS_STATUS" ]; then
        echo "✅ Redis: $REDIS_STATUS"
    else
        echo "❌ Redis: 未运行"
    fi
else
    echo "⚠️  Docker 未运行或无权限访问"
fi

# 检查数据库连接
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. 数据库连接测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker ps -q -f name=eval_postgres > /dev/null 2>&1; then
    DB_SIZE=$(docker exec eval_postgres psql -U ducc_user ducc_evaluation -t -c \
        "SELECT pg_size_pretty(pg_database_size('ducc_evaluation'));" 2>/dev/null | xargs)
    
    if [ -n "$DB_SIZE" ]; then
        echo "✅ PostgreSQL 连接成功"
        echo "   数据库大小: $DB_SIZE"
        
        TABLE_COUNT=$(docker exec eval_postgres psql -U ducc_user ducc_evaluation -t -c \
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | xargs)
        echo "   表数量: $TABLE_COUNT"
    else
        echo "❌ PostgreSQL 连接失败"
    fi
else
    echo "⚠️  PostgreSQL 容器未运行"
fi

if docker ps -q -f name=eval_redis > /dev/null 2>&1; then
    REDIS_MEMORY=$(docker exec eval_redis redis-cli INFO memory 2>/dev/null | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r')
    REDIS_KEYS=$(docker exec eval_redis redis-cli DBSIZE 2>/dev/null | cut -d: -f2 | tr -d '\r')
    
    if [ -n "$REDIS_MEMORY" ]; then
        echo "✅ Redis 连接成功"
        echo "   内存使用: $REDIS_MEMORY"
        echo "   键数量: $REDIS_KEYS"
    else
        echo "❌ Redis 连接失败"
    fi
else
    echo "⚠️  Redis 容器未运行"
fi

# 总结
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "检查完成"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
