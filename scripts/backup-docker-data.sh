#!/bin/bash

# Agent 评测系统 - Docker 数据备份脚本（增强版）
# 
# 功能：
#   - 备份 PostgreSQL 和 Redis 数据
#   - 自动清理旧备份（保留 30 天）
#   - 磁盘空间检查
#   - 备份验证
#   - 错误通知
# 
# 数据源：/home/dejavu/docker-data/
# 备份目标：/home/dejavu/backups/
# 日志文件：/var/log/eval-backup.log
# 
# 使用方法：
#   手动执行: ./scripts/backup-docker-data.sh
#   查看帮助: ./scripts/backup-docker-data.sh --help
# 
# 定时任务配置（推荐）：
#   每天凌晨 3 点执行，日志输出到 /var/log/eval-backup.log
#   
#   编辑 crontab:
#     crontab -e
#   
#   添加以下行（根据实际路径调整）：
#     0 3 * * * /Users/yuhaitao01/dev/baidu/explore/test/evaluation/scripts/backup-docker-data.sh >> /var/log/eval-backup.log 2>&1
# 
#   或使用 systemd timer（参考文档）

set -e  # 遇到错误立即退出

# ============================================
# 配置参数
# ============================================

BACKUP_DIR="/home/dejavu/backups"
DOCKER_DATA="/home/dejavu/docker-data"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_STR=$(date "+%Y-%m-%d %H:%M:%S")

# 备份保留天数
RETENTION_DAYS=30

# 最小磁盘空间要求（GB）
MIN_DISK_SPACE_GB=10

# 邮件通知配置（可选，设置为空则不发送邮件）
NOTIFICATION_EMAIL=""
# 示例：NOTIFICATION_EMAIL="admin@example.com"

# ============================================
# 工具函数
# ============================================

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ ERROR: $*" >&2
}

log_warning() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  WARNING: $*"
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ SUCCESS: $*"
}

# 发送通知
send_notification() {
    local subject="$1"
    local message="$2"
    
    if [ -n "$NOTIFICATION_EMAIL" ]; then
        echo "$message" | mail -s "$subject" "$NOTIFICATION_EMAIL" 2>/dev/null || true
    fi
}

# 检查磁盘空间
check_disk_space() {
    local target_dir="$1"
    local required_gb="$2"
    
    # 获取可用空间（GB）
    local available_gb=$(df -BG "$target_dir" | tail -1 | awk '{print $4}' | sed 's/G//')
    
    if [ "$available_gb" -lt "$required_gb" ]; then
        log_error "磁盘空间不足: 可用 ${available_gb}GB，需要至少 ${required_gb}GB"
        return 1
    fi
    
    log "磁盘空间检查通过: 可用 ${available_gb}GB"
    return 0
}

# 验证备份文件
verify_backup() {
    local file="$1"
    local type="$2"
    
    if [ ! -f "$file" ]; then
        log_error "备份文件不存在: $file"
        return 1
    fi
    
    local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    if [ "$size" -eq 0 ]; then
        log_error "备份文件为空: $file"
        return 1
    fi
    
    # PostgreSQL 备份验证
    if [ "$type" = "postgres" ]; then
        if ! gunzip -t "$file" 2>/dev/null; then
            log_error "PostgreSQL 备份文件损坏: $file"
            return 1
        fi
    fi
    
    log_success "备份文件验证通过: $file ($(du -h "$file" | cut -f1))"
    return 0
}

# ============================================
# 主备份流程
# ============================================

main() {
    log "======================================"
    log "Agent 评测系统数据备份"
    log "======================================"
    log "开始时间: $DATE_STR"
    log ""
    
    # 检查必要目录
    if [ ! -d "$DOCKER_DATA" ]; then
        log_error "数据目录不存在: $DOCKER_DATA"
        send_notification "Agent 评测备份失败" "数据目录不存在: $DOCKER_DATA"
        exit 1
    fi
    
    # 创建备份目录
    mkdir -p "$BACKUP_DIR"
    
    # 检查磁盘空间
    if ! check_disk_space "$BACKUP_DIR" "$MIN_DISK_SPACE_GB"; then
        send_notification "Agent 评测备份失败" "磁盘空间不足，备份中止"
        exit 1
    fi
    
    # 检查 Docker 是否运行
    if ! docker ps > /dev/null 2>&1; then
        log_error "Docker 未运行，备份失败"
        send_notification "Agent 评测备份失败" "Docker 服务未运行"
        exit 1
    fi
    
    # 检查容器状态
    POSTGRES_RUNNING=$(docker ps -q -f name=eval_postgres)
    REDIS_RUNNING=$(docker ps -q -f name=eval_redis)
    
    local backup_failed=0
    
    # ====================================
    # 备份 PostgreSQL
    # ====================================
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "备份 PostgreSQL 数据库"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ -n "$POSTGRES_RUNNING" ]; then
        POSTGRES_BACKUP="$BACKUP_DIR/postgres_$TIMESTAMP.sql.gz"
        
        # 执行备份
        if docker exec eval_postgres pg_dump -U ducc_user ducc_evaluation 2>/dev/null | gzip > "$POSTGRES_BACKUP"; then
            # 验证备份
            if verify_backup "$POSTGRES_BACKUP" "postgres"; then
                log_success "PostgreSQL 备份成功: postgres_$TIMESTAMP.sql.gz"
            else
                log_error "PostgreSQL 备份验证失败"
                rm -f "$POSTGRES_BACKUP"
                backup_failed=1
            fi
        else
            log_error "PostgreSQL 备份失败"
            backup_failed=1
        fi
    else
        log_warning "PostgreSQL 容器未运行，跳过备份"
    fi
    
    # ====================================
    # 备份 Redis
    # ====================================
    log ""
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "备份 Redis 数据"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ -n "$REDIS_RUNNING" ]; then
        # 触发 Redis 保存
        docker exec eval_redis redis-cli BGSAVE > /dev/null 2>&1
        
        # 等待保存完成（最多 15 秒）
        log "等待 Redis BGSAVE 完成..."
        local wait_count=0
        local last_save=$(docker exec eval_redis redis-cli LASTSAVE 2>/dev/null)
        
        while [ $wait_count -lt 15 ]; do
            sleep 1
            local new_save=$(docker exec eval_redis redis-cli LASTSAVE 2>/dev/null)
            if [ "$last_save" != "$new_save" ]; then
                log "Redis BGSAVE 完成"
                break
            fi
            wait_count=$((wait_count + 1))
        done
        
        # 复制 RDB 文件
        if [ -f "$DOCKER_DATA/redis/data/dump.rdb" ]; then
            REDIS_BACKUP="$BACKUP_DIR/redis_$TIMESTAMP.rdb"
            
            if cp "$DOCKER_DATA/redis/data/dump.rdb" "$REDIS_BACKUP"; then
                if verify_backup "$REDIS_BACKUP" "redis"; then
                    log_success "Redis 备份成功: redis_$TIMESTAMP.rdb"
                else
                    log_error "Redis 备份验证失败"
                    rm -f "$REDIS_BACKUP"
                    backup_failed=1
                fi
            else
                log_error "Redis 备份失败（文件复制失败）"
                backup_failed=1
            fi
        else
            log_warning "未找到 Redis RDB 文件"
        fi
    else
        log_warning "Redis 容器未运行，跳过备份"
    fi
    
    # ====================================
    # 清理旧备份
    # ====================================
    log ""
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "清理旧备份（保留最近 ${RETENTION_DAYS} 天）"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local deleted_count=0
    
    # 清理旧的 PostgreSQL 备份
    local old_postgres=$(find "$BACKUP_DIR" -name "postgres_*.sql.gz" -mtime +${RETENTION_DAYS} 2>/dev/null)
    if [ -n "$old_postgres" ]; then
        deleted_count=$(echo "$old_postgres" | wc -l | tr -d ' ')
        find "$BACKUP_DIR" -name "postgres_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
        log "清理了 $deleted_count 个旧的 PostgreSQL 备份"
    fi
    
    # 清理旧的 Redis 备份
    local old_redis=$(find "$BACKUP_DIR" -name "redis_*.rdb" -mtime +${RETENTION_DAYS} 2>/dev/null)
    if [ -n "$old_redis" ]; then
        local redis_count=$(echo "$old_redis" | wc -l | tr -d ' ')
        deleted_count=$((deleted_count + redis_count))
        find "$BACKUP_DIR" -name "redis_*.rdb" -mtime +${RETENTION_DAYS} -delete
        log "清理了 $redis_count 个旧的 Redis 备份"
    fi
    
    if [ $deleted_count -gt 0 ]; then
        log_success "共清理了 $deleted_count 个旧备份文件"
    else
        log "无需清理旧备份"
    fi
    
    # ====================================
    # 备份汇总
    # ====================================
    log ""
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "备份汇总"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
    log ""
    log "备份目录: $BACKUP_DIR"
    log ""
    log "最近 5 个备份文件:"
    ls -lht "$BACKUP_DIR" 2>/dev/null | head -6 || log "无备份文件"
    log ""
    log "磁盘使用情况:"
    df -h "$BACKUP_DIR"
    log ""
    log "备份文件总大小:"
    du -sh "$BACKUP_DIR" 2>/dev/null || log "无法统计"
    log ""
    
    # 发送通知
    if [ $backup_failed -eq 1 ]; then
        log_error "备份过程中出现错误"
        send_notification "Agent 评测备份部分失败" "备份过程中出现错误，请检查日志"
        exit 1
    else
        log_success "备份完成，所有任务成功"
        # 成功时不发送邮件，避免邮件过多
    fi
}

# ============================================
# 帮助信息
# ============================================

show_help() {
    cat << EOF
Agent 评测系统 - Docker 数据备份脚本

用法:
    $0 [选项]

选项:
    --help, -h          显示此帮助信息
    --retention DAYS    设置备份保留天数（默认: 30）
    --notify EMAIL      设置通知邮箱地址
    
示例:
    # 手动执行备份
    $0
    
    # 设置保留 60 天
    $0 --retention 60
    
    # 启用邮件通知
    $0 --notify admin@example.com

配置定时任务（crontab）:
    crontab -e
    
    # 每天凌晨 3 点执行
    0 3 * * * $0 >> /var/log/eval-backup.log 2>&1
    
    # 每天凌晨 3 点和下午 3 点执行
    0 3,15 * * * $0 >> /var/log/eval-backup.log 2>&1
    
    # 每周一凌晨 3 点执行
    0 3 * * 1 $0 >> /var/log/eval-backup.log 2>&1

查看备份日志:
    tail -f /var/log/eval-backup.log

EOF
}

# ============================================
# 入口
# ============================================

# 解析参数
while [ $# -gt 0 ]; do
    case "$1" in
        --help|-h)
            show_help
            exit 0
            ;;
        --retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        --notify)
            NOTIFICATION_EMAIL="$2"
            shift 2
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 执行备份
main
