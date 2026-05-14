# DUCC 评测系统 - 定时备份配置指南

本文档详细说明如何配置 Docker 数据的定时自动备份。

---

## 📋 备份脚本说明

### 脚本位置
```
/Users/yuhaitao01/dev/baidu/explore/test/evaluation/scripts/backup-docker-data.sh
```

### 功能特性
- ✅ 自动备份 PostgreSQL 数据库（pg_dump）
- ✅ 自动备份 Redis 数据（RDB 快照）
- ✅ 自动清理旧备份（默认保留 30 天）
- ✅ 磁盘空间检查（防止空间不足）
- ✅ 备份文件完整性验证
- ✅ 详细的日志记录
- ✅ 可选的邮件通知
- ✅ 错误处理和告警

### 默认配置
- **备份源**: `/home/dejavu/docker-data/`
- **备份目标**: `/home/dejavu/backups/`
- **保留天数**: 30 天
- **日志文件**: `/var/log/ducc-backup.log`

---

## 🚀 快速开始

### 1. 手动测试备份

首次使用前，建议手动执行一次测试：

```bash
# 进入项目目录
cd /Users/yuhaitao01/dev/baidu/explore/test/evaluation

# 执行备份脚本
./scripts/backup-docker-data.sh

# 查看备份结果
ls -lh /home/dejavu/backups/
```

预期输出：
```
[2024-05-14 15:30:00] ======================================
[2024-05-14 15:30:00] DUCC 评测系统数据备份
[2024-05-14 15:30:00] ======================================
[2024-05-14 15:30:00] 开始时间: 2024-05-14 15:30:00
...
[2024-05-14 15:30:15] ✅ SUCCESS: PostgreSQL 备份成功: postgres_20240514_153000.sql.gz
[2024-05-14 15:30:18] ✅ SUCCESS: Redis 备份成功: redis_20240514_153000.rdb
...
[2024-05-14 15:30:20] ✅ SUCCESS: 备份完成，所有任务成功
```

### 2. 查看帮助信息

```bash
./scripts/backup-docker-data.sh --help
```

---

## ⏰ 配置定时任务（方式一：Crontab）

### 推荐：使用 Crontab

Crontab 是 Linux/macOS 系统标准的定时任务工具，简单易用。

#### 步骤 1: 编辑 Crontab

```bash
# 编辑当前用户的 crontab
crontab -e
```

第一次使用会提示选择编辑器（推荐选择 `vim` 或 `nano`）。

#### 步骤 2: 添加定时任务

在打开的编辑器中添加以下行：

```bash
# DUCC 评测系统数据备份 - 每天凌晨 3 点执行
0 3 * * * /Users/yuhaitao01/dev/baidu/explore/test/evaluation/scripts/backup-docker-data.sh >> /var/log/ducc-backup.log 2>&1
```

**重要说明**：
- 请将路径 `/Users/yuhaitao01/dev/baidu/explore/test/evaluation/` 替换为你的实际项目路径
- 确保脚本路径是**绝对路径**，不要使用相对路径

#### 步骤 3: 保存并退出

- **vim**: 按 `ESC`，输入 `:wq`，回车
- **nano**: 按 `Ctrl+X`，输入 `Y`，回车

#### 步骤 4: 验证配置

```bash
# 查看已配置的定时任务
crontab -l

# 应该能看到刚才添加的行
```

#### 步骤 5: 创建日志目录并设置权限

```bash
# 创建日志文件（如果不存在）
sudo touch /var/log/ducc-backup.log

# 设置权限（允许当前用户写入）
sudo chown $(whoami):$(whoami) /var/log/ducc-backup.log
sudo chmod 644 /var/log/ducc-backup.log
```

---

## 📅 Crontab 时间格式说明

Crontab 时间格式：
```
* * * * * 命令
│ │ │ │ │
│ │ │ │ └─ 星期几 (0-7, 0和7都代表周日)
│ │ │ └─── 月份 (1-12)
│ │ └───── 日期 (1-31)
│ └─────── 小时 (0-23)
└───────── 分钟 (0-59)
```

### 常用定时配置示例

#### 1. 每天备份

```bash
# 每天凌晨 3 点
0 3 * * * /path/to/backup-docker-data.sh >> /var/log/ducc-backup.log 2>&1

# 每天凌晨 2:30
30 2 * * * /path/to/backup-docker-data.sh >> /var/log/ducc-backup.log 2>&1

# 每天上午 10 点和晚上 10 点
0 10,22 * * * /path/to/backup-docker-data.sh >> /var/log/ducc-backup.log 2>&1
```

#### 2. 每周备份

```bash
# 每周一凌晨 3 点
0 3 * * 1 /path/to/backup-docker-data.sh >> /var/log/ducc-backup.log 2>&1

# 每周日凌晨 3 点
0 3 * * 0 /path/to/backup-docker-data.sh >> /var/log/ducc-backup.log 2>&1
```

#### 3. 每月备份

```bash
# 每月 1 号凌晨 3 点
0 3 1 * * /path/to/backup-docker-data.sh >> /var/log/ducc-backup.log 2>&1

# 每月 15 号凌晨 3 点
0 3 15 * * /path/to/backup-docker-data.sh >> /var/log/ducc-backup.log 2>&1
```

#### 4. 每小时备份

```bash
# 每小时整点执行
0 * * * * /path/to/backup-docker-data.sh >> /var/log/ducc-backup.log 2>&1

# 每小时的 30 分执行
30 * * * * /path/to/backup-docker-data.sh >> /var/log/ducc-backup.log 2>&1
```

#### 5. 工作日备份

```bash
# 周一到周五凌晨 3 点
0 3 * * 1-5 /path/to/backup-docker-data.sh >> /var/log/ducc-backup.log 2>&1
```

---

## ⏰ 配置定时任务（方式二：Systemd Timer）

如果你的系统使用 systemd（大多数现代 Linux 发行版），可以使用 systemd timer，功能更强大。

### 创建 Service 文件

创建文件 `/etc/systemd/system/ducc-backup.service`:

```ini
[Unit]
Description=DUCC Evaluation System Backup
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
User=dejavu
WorkingDirectory=/Users/yuhaitao01/dev/baidu/explore/test/evaluation
ExecStart=/Users/yuhaitao01/dev/baidu/explore/test/evaluation/scripts/backup-docker-data.sh
StandardOutput=append:/var/log/ducc-backup.log
StandardError=append:/var/log/ducc-backup.log

[Install]
WantedBy=multi-user.target
```

### 创建 Timer 文件

创建文件 `/etc/systemd/system/ducc-backup.timer`:

```ini
[Unit]
Description=DUCC Backup Timer - Daily at 3 AM
Requires=ducc-backup.service

[Timer]
# 每天凌晨 3 点执行
OnCalendar=daily
OnCalendar=03:00:00

# 如果错过执行时间，立即执行
Persistent=true

[Install]
WantedBy=timers.target
```

### 启用和启动

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启用定时器（开机自启）
sudo systemctl enable ducc-backup.timer

# 启动定时器
sudo systemctl start ducc-backup.timer

# 查看定时器状态
sudo systemctl status ducc-backup.timer

# 查看所有定时器
systemctl list-timers --all | grep ducc

# 手动触发备份（测试）
sudo systemctl start ducc-backup.service

# 查看最近的日志
sudo journalctl -u ducc-backup.service -n 50
```

### Systemd Timer 时间格式

```ini
# 每天 3 点
OnCalendar=03:00:00

# 每天凌晨 2:30
OnCalendar=02:30:00

# 每周一 3 点
OnCalendar=Mon 03:00:00

# 每月 1 号 3 点
OnCalendar=*-*-01 03:00:00

# 每小时
OnCalendar=hourly

# 每天
OnCalendar=daily

# 每周
OnCalendar=weekly

# 每月
OnCalendar=monthly
```

---

## 📊 监控和管理

### 查看备份日志

#### 实时查看日志
```bash
# 实时跟踪日志
tail -f /var/log/ducc-backup.log

# 查看最近 50 行
tail -50 /var/log/ducc-backup.log

# 查看今天的备份日志
grep "$(date '+%Y-%m-%d')" /var/log/ducc-backup.log
```

#### 查看备份文件
```bash
# 列出所有备份
ls -lh /home/dejavu/backups/

# 按时间排序（最新的在前）
ls -lht /home/dejavu/backups/

# 只看 PostgreSQL 备份
ls -lh /home/dejavu/backups/postgres_*.sql.gz

# 只看 Redis 备份
ls -lh /home/dejavu/backups/redis_*.rdb

# 查看备份总大小
du -sh /home/dejavu/backups/
```

#### 检查最近一次备份

```bash
# 查看最新的 PostgreSQL 备份
ls -lt /home/dejavu/backups/postgres_*.sql.gz | head -1

# 查看最新的 Redis 备份
ls -lt /home/dejavu/backups/redis_*.rdb | head -1

# 查看最近一次备份的日志
tail -100 /var/log/ducc-backup.log | grep -A 20 "DUCC 评测系统数据备份"
```

### 停止定时备份

#### Crontab 方式
```bash
# 编辑 crontab
crontab -e

# 注释或删除备份行（在行首添加 # 注释）
# 0 3 * * * /path/to/backup-docker-data.sh >> /var/log/ducc-backup.log 2>&1

# 或完全删除定时任务
crontab -r  # 警告：会删除所有定时任务！
```

#### Systemd Timer 方式
```bash
# 停止定时器
sudo systemctl stop ducc-backup.timer

# 禁用定时器（取消开机自启）
sudo systemctl disable ducc-backup.timer

# 查看状态
sudo systemctl status ducc-backup.timer
```

### 修改备份配置

#### 修改备份保留天数

编辑脚本：
```bash
vi /Users/yuhaitao01/dev/baidu/explore/test/evaluation/scripts/backup-docker-data.sh
```

找到这一行（约第 21 行）：
```bash
RETENTION_DAYS=30
```

修改为你想要的天数，如保留 60 天：
```bash
RETENTION_DAYS=60
```

或在执行时指定：
```bash
./scripts/backup-docker-data.sh --retention 60
```

#### 启用邮件通知

编辑脚本，找到这一行（约第 27 行）：
```bash
NOTIFICATION_EMAIL=""
```

修改为你的邮箱：
```bash
NOTIFICATION_EMAIL="admin@example.com"
```

**注意**: 需要系统配置了邮件发送功能（如 `sendmail` 或 `mailx`）。

---

## 🔔 备份告警和监控

### 方式 1: 使用邮件通知

#### 安装 mailx
```bash
# Ubuntu/Debian
sudo apt-get install mailutils

# CentOS/RHEL
sudo yum install mailx

# macOS
brew install mailutils
```

#### 配置 SMTP（可选）

创建 `~/.mailrc`:
```bash
set smtp=smtp.gmail.com:587
set smtp-use-starttls
set smtp-auth=login
set smtp-auth-user=your-email@gmail.com
set smtp-auth-password=your-app-password
set from=your-email@gmail.com
```

### 方式 2: 使用 Webhook 通知

在脚本中添加 webhook 调用（如钉钉、飞书、企业微信）：

```bash
# 在 send_notification 函数中添加
send_webhook() {
    local message="$1"
    local webhook_url="https://your-webhook-url"
    
    curl -X POST "$webhook_url" \
      -H 'Content-Type: application/json' \
      -d "{\"text\": \"$message\"}" \
      2>/dev/null
}
```

### 方式 3: 监控备份状态

创建一个简单的监控脚本 `scripts/check-backup-status.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/home/dejavu/backups"
MAX_AGE_HOURS=48  # 超过 48 小时没有备份则告警

# 查找最新的备份文件
LATEST_BACKUP=$(find "$BACKUP_DIR" -name "postgres_*.sql.gz" -type f -printf '%T@ %p\n' | sort -n | tail -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ 警告: 没有找到任何备份文件"
    exit 1
fi

# 提取时间戳和文件名
BACKUP_TIME=$(echo "$LATEST_BACKUP" | cut -d' ' -f1)
BACKUP_FILE=$(echo "$LATEST_BACKUP" | cut -d' ' -f2-)
CURRENT_TIME=$(date +%s)
AGE_HOURS=$(( (CURRENT_TIME - ${BACKUP_TIME%.*}) / 3600 ))

if [ "$AGE_HOURS" -gt "$MAX_AGE_HOURS" ]; then
    echo "❌ 警告: 最新备份已过时 ($AGE_HOURS 小时前)"
    echo "文件: $BACKUP_FILE"
    exit 1
else
    echo "✅ 备份状态正常，最新备份: $AGE_HOURS 小时前"
    echo "文件: $BACKUP_FILE"
    exit 0
fi
```

将监控脚本加入 crontab（每小时检查一次）：
```bash
0 * * * * /path/to/check-backup-status.sh || echo "备份状态异常" | mail -s "DUCC 备份告警" admin@example.com
```

---

## 🧪 测试和验证

### 1. 手动执行测试
```bash
# 执行备份
./scripts/backup-docker-data.sh

# 检查返回值（0 表示成功）
echo $?
```

### 2. 测试定时任务

#### Crontab 测试
```bash
# 添加一个临时的测试任务（1分钟后执行）
# 当前时间 +1 分钟，例如现在是 15:30，则设置为 15:31
crontab -e

# 添加（根据实际时间调整）：
31 15 * * * /path/to/backup-docker-data.sh >> /tmp/backup-test.log 2>&1

# 等待执行，然后查看日志
tail -f /tmp/backup-test.log

# 测试完成后删除该行
```

### 3. 验证备份文件完整性

```bash
# 测试 PostgreSQL 备份
gunzip -t /home/dejavu/backups/postgres_20240514_030000.sql.gz

# 如果没有输出，说明文件完整
echo $?  # 返回 0 表示成功
```

### 4. 模拟恢复测试

定期（如每月）测试恢复流程：

```bash
# 1. 创建测试数据库
docker exec ducc_postgres psql -U ducc_user postgres -c \
  "CREATE DATABASE test_restore OWNER ducc_user;"

# 2. 恢复到测试数据库
gunzip < /home/dejavu/backups/postgres_20240514_030000.sql.gz | \
  docker exec -i ducc_postgres psql -U ducc_user test_restore

# 3. 验证数据
docker exec ducc_postgres psql -U ducc_user test_restore -c "\dt"

# 4. 清理
docker exec ducc_postgres psql -U ducc_user postgres -c \
  "DROP DATABASE test_restore;"
```

---

## ❓ 常见问题

### Q1: 定时任务不执行？

**排查步骤**：

1. 检查 crontab 是否正确配置
   ```bash
   crontab -l
   ```

2. 检查脚本权限
   ```bash
   ls -l /path/to/backup-docker-data.sh
   chmod +x /path/to/backup-docker-data.sh
   ```

3. 检查 cron 服务是否运行
   ```bash
   # macOS
   sudo launchctl list | grep cron
   
   # Linux
   sudo systemctl status cron
   ```

4. 查看系统日志
   ```bash
   # macOS
   tail -f /var/log/system.log | grep cron
   
   # Linux
   tail -f /var/log/syslog | grep CRON
   ```

5. 测试脚本路径
   ```bash
   # 使用绝对路径手动执行
   /Users/yuhaitao01/dev/baidu/explore/test/evaluation/scripts/backup-docker-data.sh
   ```

### Q2: 备份文件过大占用空间？

**解决方案**：

1. 减少保留天数
   ```bash
   ./scripts/backup-docker-data.sh --retention 15
   ```

2. 手动清理旧备份
   ```bash
   find /home/dejavu/backups -name "*.sql.gz" -mtime +15 -delete
   find /home/dejavu/backups -name "*.rdb" -mtime +15 -delete
   ```

3. 压缩备份文件（已默认使用 gzip）

4. 将旧备份移动到其他存储
   ```bash
   rsync -av --remove-source-files \
     /home/dejavu/backups/ \
     /path/to/archive/
   ```

### Q3: Docker 容器未运行导致备份失败？

脚本会自动检测容器状态并跳过未运行的服务。

查看日志确认：
```bash
tail -50 /var/log/ducc-backup.log | grep "未运行"
```

确保 Docker 容器在备份时运行：
```bash
docker-compose ps
docker-compose start postgres redis
```

### Q4: 如何查看某一天的备份？

```bash
# 查看 2024年5月14日 的备份
ls -lh /home/dejavu/backups/*20240514*

# 查看 5月 的所有备份
ls -lh /home/dejavu/backups/*202405*
```

### Q5: 权限问题导致无法写入日志？

```bash
# 修复日志文件权限
sudo touch /var/log/ducc-backup.log
sudo chown $(whoami):$(whoami) /var/log/ducc-backup.log
sudo chmod 644 /var/log/ducc-backup.log
```

---

## 📚 相关文档

- [Docker 数据存储文档](DOCKER_DATA_STORAGE.md)
- [部署文档](DEPLOYMENT.md)
- [运维手册](OPERATIONS.md)

---

## 🎯 推荐配置总结

### 生产环境推荐配置

```bash
# 1. 添加到 crontab
crontab -e

# 每天凌晨 3 点备份
0 3 * * * /Users/yuhaitao01/dev/baidu/explore/test/evaluation/scripts/backup-docker-data.sh >> /var/log/ducc-backup.log 2>&1

# 2. 设置日志轮转（防止日志文件过大）
sudo tee /etc/logrotate.d/ducc-backup << 'EOF'
/var/log/ducc-backup.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $(whoami) $(whoami)
}
EOF

# 3. 创建备份状态检查脚本（每小时检查一次）
0 * * * * /Users/yuhaitao01/dev/baidu/explore/test/evaluation/scripts/check-backup-status.sh
```

---

**定时备份已配置完成！数据安全有保障！** 🔒
