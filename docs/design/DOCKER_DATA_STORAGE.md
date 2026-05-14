# Docker 数据存储说明文档

## 📂 数据存储位置

**绝对路径**: `/home/dejavu/docker-data/`

### 目录结构

```
/home/dejavu/docker-data/
├── postgres/
│   └── data/                        # PostgreSQL 数据库文件
│       ├── base/                    # 数据库数据
│       ├── global/                  # 全局对象
│       ├── pg_wal/                  # WAL（预写日志）
│       ├── pg_stat/                 # 统计信息
│       ├── pg_tblspc/               # 表空间
│       ├── postgresql.conf          # 配置文件
│       └── ...
└── redis/
    └── data/                        # Redis 持久化文件
        ├── appendonly.aof           # AOF（追加操作日志）
        └── dump.rdb                 # RDB（快照文件）
```

---

## 🚀 快速开始

### 首次部署

```bash
# 1. 初始化数据目录
cd /Users/yuhaitao01/dev/baidu/explore/test/evaluation
./scripts/init-docker-data.sh

# 2. 启动 Docker 服务
docker-compose up -d

# 3. 验证数据目录
ls -lh /home/dejavu/docker-data/postgres/data
ls -lh /home/dejavu/docker-data/redis/data

# 4. 检查容器状态
docker-compose ps
```

### 从旧版本迁移

如果你之前使用了 Docker 命名卷（`evaluation_postgres_data` 等），需要迁移数据：

```bash
# 1. 执行迁移脚本
./scripts/migrate-docker-data.sh

# 2. 启动服务
docker-compose up -d

# 3. 验证数据完整性
docker exec ducc_postgres psql -U ducc_user ducc_evaluation -c "\dt"
docker exec ducc_redis redis-cli PING

# 4. 确认无误后删除旧卷
docker volume rm evaluation_postgres_data evaluation_redis_data
```

---

## 📊 数据管理

### 查看数据使用情况

```bash
# 使用检查脚本（推荐）
./scripts/check-docker-data.sh

# 或手动查看

# 总体磁盘使用
df -h /home/dejavu/docker-data

# PostgreSQL 数据大小
du -sh /home/dejavu/docker-data/postgres/data

# Redis 数据大小
du -sh /home/dejavu/docker-data/redis/data

# 详细统计
docker exec ducc_postgres psql -U ducc_user ducc_evaluation -c \
  "SELECT pg_size_pretty(pg_database_size('ducc_evaluation'));"

docker exec ducc_redis redis-cli INFO memory | grep used_memory_human
```

### 查看数据库信息

```bash
# PostgreSQL 表列表
docker exec ducc_postgres psql -U ducc_user ducc_evaluation -c "\dt"

# 表大小统计
docker exec ducc_postgres psql -U ducc_user ducc_evaluation -c "
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# Redis 键统计
docker exec ducc_redis redis-cli INFO keyspace
docker exec ducc_redis redis-cli DBSIZE
```

---

## 💾 数据备份

### 自动备份

#### 1. 使用备份脚本

```bash
# 手动执行备份
./scripts/backup-docker-data.sh

# 备份文件位置
ls -lh /home/dejavu/backups/
```

#### 2. 设置定时备份

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨 3 点执行）
0 3 * * * /Users/yuhaitao01/dev/baidu/explore/test/evaluation/scripts/backup-docker-data.sh >> /var/log/ducc-backup.log 2>&1

# 查看 crontab 列表
crontab -l

# 查看备份日志
tail -f /var/log/ducc-backup.log
```

#### 3. 备份保留策略

备份脚本会自动清理超过 30 天的旧备份，你可以修改脚本中的保留天数：

```bash
# 编辑备份脚本
vi scripts/backup-docker-data.sh

# 找到这一行并修改天数（默认 30 天）
find "$BACKUP_DIR" -name "postgres_*.sql.gz" -mtime +30 -delete
```

### 手动备份

#### PostgreSQL 备份

```bash
# 在线备份（推荐）
docker exec ducc_postgres pg_dump -U ducc_user ducc_evaluation | \
  gzip > /home/dejavu/backups/manual_postgres_$(date +%Y%m%d_%H%M%S).sql.gz

# 冷备份（需要停止容器）
docker-compose stop postgres
tar -czf /home/dejavu/backups/postgres_cold_$(date +%Y%m%d_%H%M%S).tar.gz \
  /home/dejavu/docker-data/postgres/data
docker-compose start postgres
```

#### Redis 备份

```bash
# 触发 Redis 保存
docker exec ducc_redis redis-cli BGSAVE

# 等待几秒后复制 RDB 文件
sleep 3
cp /home/dejavu/docker-data/redis/data/dump.rdb \
   /home/dejavu/backups/redis_$(date +%Y%m%d_%H%M%S).rdb

# 或备份 AOF 文件
cp /home/dejavu/docker-data/redis/data/appendonly.aof \
   /home/dejavu/backups/redis_aof_$(date +%Y%m%d_%H%M%S).aof
```

---

## 🔄 数据恢复

### PostgreSQL 恢复

#### 方法 1: 从 SQL 备份恢复

```bash
# 1. 停止应用（防止写入）
docker-compose stop backend worker  # 如果在 Docker 中运行

# 2. 删除现有数据库（可选）
docker exec ducc_postgres psql -U ducc_user postgres -c \
  "DROP DATABASE IF EXISTS ducc_evaluation;"

# 3. 重新创建数据库
docker exec ducc_postgres psql -U ducc_user postgres -c \
  "CREATE DATABASE ducc_evaluation OWNER ducc_user;"

# 4. 恢复数据
gunzip < /home/dejavu/backups/postgres_20240514_030000.sql.gz | \
  docker exec -i ducc_postgres psql -U ducc_user ducc_evaluation

# 5. 验证恢复
docker exec ducc_postgres psql -U ducc_user ducc_evaluation -c "\dt"

# 6. 重启应用
docker-compose start backend worker
```

#### 方法 2: 从冷备份恢复

```bash
# 1. 停止 PostgreSQL
docker-compose stop postgres

# 2. 删除现有数据
rm -rf /home/dejavu/docker-data/postgres/data/*

# 3. 解压备份
tar -xzf /home/dejavu/backups/postgres_cold_20240514_030000.tar.gz \
  -C / --strip-components=4

# 4. 设置权限
chmod -R 755 /home/dejavu/docker-data/postgres/data

# 5. 启动 PostgreSQL
docker-compose start postgres
```

### Redis 恢复

#### 从 RDB 恢复

```bash
# 1. 停止 Redis
docker-compose stop redis

# 2. 替换 RDB 文件
cp /home/dejavu/backups/redis_20240514_030000.rdb \
   /home/dejavu/docker-data/redis/data/dump.rdb

# 3. 启动 Redis
docker-compose start redis

# 4. 验证数据
docker exec ducc_redis redis-cli DBSIZE
```

#### 从 AOF 恢复

```bash
# 1. 停止 Redis
docker-compose stop redis

# 2. 替换 AOF 文件
cp /home/dejavu/backups/redis_aof_20240514_030000.aof \
   /home/dejavu/docker-data/redis/data/appendonly.aof

# 3. 启动 Redis
docker-compose start redis
```

---

## 🛠️ 常见操作

### 清理数据

#### 清理测试数据

```bash
# PostgreSQL 删除特定表数据
docker exec ducc_postgres psql -U ducc_user ducc_evaluation -c \
  "TRUNCATE task_instances CASCADE;"

# Redis 清空所有键
docker exec ducc_redis redis-cli FLUSHALL

# 或只清空当前数据库
docker exec ducc_redis redis-cli FLUSHDB
```

#### 完全重置

```bash
# ⚠️  警告: 这将删除所有数据！

# 1. 停止容器
docker-compose down

# 2. 删除数据
rm -rf /home/dejavu/docker-data/postgres/data/*
rm -rf /home/dejavu/docker-data/redis/data/*

# 3. 重新初始化
./scripts/init-docker-data.sh

# 4. 启动容器
docker-compose up -d
```

### 数据迁移

#### 迁移到新服务器

```bash
# 在旧服务器上

# 1. 备份数据
./scripts/backup-docker-data.sh

# 2. 打包数据目录
tar -czf ducc-data-export.tar.gz \
  /home/dejavu/docker-data \
  /home/dejavu/backups

# 3. 传输到新服务器
scp ducc-data-export.tar.gz user@new-server:/tmp/


# 在新服务器上

# 1. 解压数据
cd /
sudo tar -xzf /tmp/ducc-data-export.tar.gz

# 2. 设置权限
sudo chown -R $(whoami):$(whoami) /home/dejavu/docker-data

# 3. 启动服务
cd /path/to/evaluation
docker-compose up -d
```

### 性能优化

#### PostgreSQL 性能优化

```bash
# 查看慢查询
docker exec ducc_postgres psql -U ducc_user ducc_evaluation -c \
  "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# VACUUM 优化
docker exec ducc_postgres psql -U ducc_user ducc_evaluation -c \
  "VACUUM ANALYZE;"

# 重建索引
docker exec ducc_postgres psql -U ducc_user ducc_evaluation -c \
  "REINDEX DATABASE ducc_evaluation;"
```

#### Redis 性能优化

```bash
# 查看慢日志
docker exec ducc_redis redis-cli SLOWLOG GET 10

# 查看内存使用详情
docker exec ducc_redis redis-cli INFO memory

# 手动触发 AOF 重写
docker exec ducc_redis redis-cli BGREWRITEAOF
```

---

## ⚠️ 注意事项

### 1. 权限问题

PostgreSQL 容器内运行用户的 UID 通常是 `999` 或 `70`。如果遇到权限错误：

```bash
# 查看当前权限
ls -la /home/dejavu/docker-data/postgres/

# 修改所有者（999 是 postgres 用户的 UID）
sudo chown -R 999:999 /home/dejavu/docker-data/postgres/data

# 或使用 docker 容器查看 UID
docker exec ducc_postgres id postgres
```

### 2. 磁盘空间监控

定期检查磁盘使用情况，避免空间不足：

```bash
# 使用检查脚本
./scripts/check-docker-data.sh

# 手动检查
df -h /home/dejavu/docker-data

# 设置磁盘空间告警（使用率超过 80%）
du -sh /home/dejavu/docker-data | awk '{if($1+0 > 100) print "Warning: " $1 " used"}'
```

当前磁盘状态：
- **总容量**: 3.6TB
- **已使用**: 385GB (11%)
- **可用**: 3.2TB ✅

### 3. 备份验证

定期验证备份文件的完整性：

```bash
# 测试 PostgreSQL 备份文件
gunzip -t /home/dejavu/backups/postgres_20240514_030000.sql.gz

# 测试恢复到临时数据库
gunzip < /home/dejavu/backups/postgres_20240514_030000.sql.gz | \
  docker exec -i ducc_postgres psql -U ducc_user postgres -c \
  "CREATE DATABASE test_restore;" && \
  docker exec -i ducc_postgres psql -U ducc_user test_restore

# 清理测试数据库
docker exec ducc_postgres psql -U ducc_user postgres -c \
  "DROP DATABASE test_restore;"
```

### 4. 数据安全

1. **定期备份**: 建议每天自动备份
2. **异地备份**: 将备份复制到其他服务器或云存储
3. **加密敏感数据**: 对备份文件进行加密
4. **访问控制**: 限制数据目录的访问权限

```bash
# 加密备份文件
gpg --symmetric --cipher-algo AES256 \
  /home/dejavu/backups/postgres_20240514_030000.sql.gz

# 解密
gpg --decrypt \
  /home/dejavu/backups/postgres_20240514_030000.sql.gz.gpg \
  > postgres_restore.sql.gz
```

### 5. Docker Compose 配置

当前 `docker-compose.yml` 中的数据卷配置：

```yaml
services:
  postgres:
    volumes:
      - /home/dejavu/docker-data/postgres/data:/var/lib/postgresql/data
  
  redis:
    volumes:
      - /home/dejavu/docker-data/redis/data:/data
```

**不要修改为相对路径**，绝对路径确保数据位置明确且不受工作目录影响。

---

## 📞 故障排查

### 问题 1: 容器启动失败

```bash
# 查看容器日志
docker-compose logs postgres
docker-compose logs redis

# 检查数据目录权限
ls -la /home/dejavu/docker-data/postgres/data
ls -la /home/dejavu/docker-data/redis/data

# 修复权限
sudo chown -R 999:999 /home/dejavu/docker-data/postgres/data
chmod -R 755 /home/dejavu/docker-data/redis/data
```

### 问题 2: 数据丢失

```bash
# 检查数据目录是否为空
ls -la /home/dejavu/docker-data/postgres/data
ls -la /home/dejavu/docker-data/redis/data

# 从备份恢复（参考上面的恢复步骤）
```

### 问题 3: 磁盘空间不足

```bash
# 清理 Docker 系统
docker system prune -a --volumes

# 清理旧日志
find /home/dejavu/docker-data -name "*.log" -mtime +7 -delete

# 清理旧备份（手动，谨慎操作）
find /home/dejavu/backups -name "*.sql.gz" -mtime +90 -delete
```

### 问题 4: 性能问题

```bash
# PostgreSQL 慢查询分析
docker exec ducc_postgres psql -U ducc_user ducc_evaluation -c \
  "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Redis 慢命令分析
docker exec ducc_redis redis-cli SLOWLOG GET 10

# 资源使用监控
docker stats ducc_postgres ducc_redis
```

---

## 📚 相关文档

- [部署文档](DEPLOYMENT.md) - 生产环境部署指南
- [开发文档](DEVELOPMENT.md) - 开发环境和 API 开发
- [前端文档](FRONTEND.md) - 前端开发指南
- [架构说明](ARCHITECTURE_CHANGE.md) - 系统架构设计

---

## 📋 脚本清单

所有数据管理脚本位于 `scripts/` 目录：

- `init-docker-data.sh` - 初始化数据目录
- `migrate-docker-data.sh` - 从旧卷迁移数据
- `backup-docker-data.sh` - 备份数据
- `check-docker-data.sh` - 检查数据状态

执行权限设置：

```bash
chmod +x scripts/*.sh
```

---

**数据安全无小事，定期备份很重要！** 🔒
