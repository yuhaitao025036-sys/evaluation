# DUCC 评测系统 - 生产环境部署文档

## 目录

1. [部署架构](#部署架构)
2. [环境要求](#环境要求)
3. [环境准备](#环境准备)
4. [后端部署](#后端部署)
5. [前端部署](#前端部署)
6. [验证部署](#验证部署)
7. [备份和恢复](#备份和恢复)
8. [监控和维护](#监控和维护)
9. [安全加固](#安全加固)
10. [故障排查](#故障排查)
11. [升级指南](#升级指南)

---

## 部署架构

本系统采用混合部署架构：

```
┌─────────────────┐
│   Nginx (80/443)│  ← 用户访问入口
└────────┬────────┘
         │
    ┌────┴─────┐
    │          │
    ↓          ↓
┌─────────┐ ┌──────────────┐
│ 前端静态 │ │ Backend API  │  ← 宿主机进程 (Conda)
│  文件    │ │ (FastAPI)    │
└─────────┘ └──────┬───────┘
                   │
         ┌─────────┴──────────┐
         │                    │
         ↓                    ↓
    ┌─────────┐         ┌──────────┐
    │ PostgreSQL│        │  Redis   │  ← Docker 容器
    │ (Docker) │        │ (Docker) │
    └─────────┘         └────┬─────┘
                             │
                    ┌────────┴────────┐
                    │   RQ Worker     │  ← 宿主机进程 (Conda)
                    │  (任务执行器)    │
                    └────────┬────────┘
                             │ Docker API
                    ┌────────┴────────┐
                    │ 评测任务 (Docker)│
                    └─────────────────┘
```

### 组件说明

- **数据库服务**（Docker）: PostgreSQL 15 + Redis 7
- **应用服务**（宿主机）: FastAPI Backend + RQ Worker
- **前端**（Nginx）: React SPA 静态文件
- **评测任务**（Docker）: Worker 调用宿主机 Docker 执行

---

## 环境要求

### 硬件要求

- **CPU**: 4核心及以上
- **内存**: 8GB 及以上（建议 16GB）
- **磁盘**: 50GB 可用空间（根据数据量调整）

### 软件要求

- **操作系统**: macOS / Linux (Ubuntu 20.04+ 推荐)
- **Docker**: 20.10+
- **Docker Compose**: 1.29+
- **Conda**: Miniconda 或 Anaconda
- **Python**: 3.12+ (通过 conda 管理)
- **Node.js**: 16.0+ (用于前端构建)
- **npm**: 7.0+
- **Nginx**: 1.18+ (可选，生产环境推荐)

---

## 环境准备

### 1. 安装 Docker 和 Docker Compose

#### macOS

```bash
# 下载 Docker Desktop for Mac
# https://www.docker.com/products/docker-desktop

# 验证安装
docker --version
docker-compose --version
```

#### Linux (Ubuntu)

```bash
# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER
newgrp docker

# 验证安装
docker --version
docker-compose --version
```

### 2. 安装 Conda

```bash
# 下载 Miniconda (如果已安装可跳过)
# macOS
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
bash Miniconda3-latest-MacOSX-x86_64.sh

# Linux
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

# 初始化 conda
conda init bash  # 或 conda init zsh
source ~/.bashrc  # 或 source ~/.zshrc
```

### 3. 安装 Node.js (用于前端构建)

```bash
# macOS (使用 Homebrew)
brew install node

# Linux (Ubuntu)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 验证安装
node --version
npm --version
```

### 4. 安装 Nginx (可选，生产环境推荐)

```bash
# macOS
brew install nginx

# Linux (Ubuntu)
sudo apt-get install nginx

# 验证安装
nginx -v
```

---

## 后端部署

### 1. 准备项目目录

```bash
# 将代码上传到服务器指定目录
# 假设项目目录为: /opt/ducc-evaluation
cd /opt/ducc-evaluation/evaluation
```

### 2. 创建 Conda 环境

```bash
cd backend

# 创建 conda 环境 (如果 dejavu 环境不存在)
conda create -n dejavu python=3.12 -y
conda activate dejavu

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 创建 .env 文件
cat > .env << 'EOF'
# 数据库配置
DATABASE_URL=postgresql://ducc_user:ducc_pass@localhost:5432/ducc_evaluation

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# 应用配置
DEBUG=false
SECRET_KEY=your-secret-key-change-in-production

# 任务配置
TASK_TIMEOUT=600
MAX_CONCURRENCY=10
EOF

# 生成随机 SECRET_KEY
python -c "import secrets; print(f'SECRET_KEY={secrets.token_urlsafe(32)}')" >> .env
```

### 4. 启动数据库服务 (Docker)

```bash
# 启动 PostgreSQL 和 Redis
docker-compose up -d

# 验证服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 5. 初始化数据库

```bash
# 确保 conda 环境已激活
conda activate dejavu

# 创建数据库表
python -c "from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"
```

### 6. 准备数据目录

```bash
# 创建必要的目录
mkdir -p data/scripts
mkdir -p data/results
mkdir -p data/logs

# 将评测脚本复制到 scripts 目录
cp /path/to/your/scripts/*.py data/scripts/
```

### 7. 生产环境部署 (使用 systemd)

#### Backend 服务配置

创建文件 `/etc/systemd/system/ducc-backend.service`:

```ini
[Unit]
Description=DUCC Evaluation Backend API
After=network.target docker.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ducc-evaluation/evaluation/backend
Environment="PATH=/home/user/miniconda3/envs/dejavu/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/ducc-evaluation/evaluation/backend"
ExecStart=/home/user/miniconda3/envs/dejavu/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10
StandardOutput=append:/opt/ducc-evaluation/evaluation/backend/data/logs/backend.log
StandardError=append:/opt/ducc-evaluation/evaluation/backend/data/logs/backend.error.log

[Install]
WantedBy=multi-user.target
```

#### Worker 服务配置

创建文件 `/etc/systemd/system/ducc-worker.service`:

```ini
[Unit]
Description=DUCC Evaluation Worker
After=network.target docker.service redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ducc-evaluation/evaluation/backend
Environment="PATH=/home/user/miniconda3/envs/dejavu/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/ducc-evaluation/evaluation/backend"
ExecStart=/home/user/miniconda3/envs/dejavu/bin/rq worker --url redis://localhost:6379/0 ducc-tasks
Restart=always
RestartSec=10
StandardOutput=append:/opt/ducc-evaluation/evaluation/backend/data/logs/worker.log
StandardError=append:/opt/ducc-evaluation/evaluation/backend/data/logs/worker.error.log

[Install]
WantedBy=multi-user.target
```

#### 启动服务

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start ducc-backend
sudo systemctl start ducc-worker

# 设置开机自启
sudo systemctl enable ducc-backend
sudo systemctl enable ducc-worker

# 查看状态
sudo systemctl status ducc-backend
sudo systemctl status ducc-worker

# 查看日志
sudo journalctl -u ducc-backend -f
sudo journalctl -u ducc-worker -f
```

---

## 前端部署

### 1. 构建生产版本

```bash
cd /opt/ducc-evaluation/evaluation/frontend

# 安装依赖
npm install

# 构建生产版本
npm run build

# 构建产物在 dist/ 目录
ls -la dist/
```

### 2. 配置 Nginx

创建 Nginx 配置文件 `/etc/nginx/sites-available/ducc-evaluation`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 访问日志
    access_log /var/log/nginx/ducc-access.log;
    error_log /var/log/nginx/ducc-error.log;

    # 前端静态文件
    location / {
        root /opt/ducc-evaluation/evaluation/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
        
        # 静态资源缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
}
```

### 3. 启用 Nginx 配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/ducc-evaluation /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx

# 设置开机自启
sudo systemctl enable nginx
```

### 4. 配置 HTTPS (可选但推荐)

```bash
# 安装 Certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取 SSL 证书
sudo certbot --nginx -d your-domain.com

# 测试自动续期
sudo certbot renew --dry-run

# Certbot 会自动修改 Nginx 配置并设置定时任务
```

---

## 验证部署

### 1. 检查服务状态

```bash
# 检查 Docker 服务
docker-compose ps

# 检查 systemd 服务
sudo systemctl status ducc-backend
sudo systemctl status ducc-worker
sudo systemctl status nginx

# 检查端口监听
sudo netstat -tlnp | grep -E '(8000|5432|6379|80|443)'
```

### 2. 测试后端 API

```bash
# 健康检查
curl http://localhost:8000/api/health

# 获取数据集列表
curl http://localhost:8000/api/v1/datasets/

# 查看 API 文档
curl http://localhost:8000/docs
```

### 3. 测试前端访问

```bash
# 通过 Nginx 访问
curl http://your-domain.com

# 或直接访问
curl http://localhost
```

### 4. 功能验证

1. 访问前端: `http://your-domain.com`
2. 创建数据集并导入数据
3. 扫描评测脚本
4. 创建并启动任务
5. 查看任务执行进度
6. 对比不同模型/标签的结果

### 5. 查看日志

```bash
# Backend 日志
tail -f /opt/ducc-evaluation/evaluation/backend/data/logs/backend.log

# Worker 日志
tail -f /opt/ducc-evaluation/evaluation/backend/data/logs/worker.log

# Nginx 日志
tail -f /var/log/nginx/ducc-access.log
tail -f /var/log/nginx/ducc-error.log

# systemd 日志
sudo journalctl -u ducc-backend -f
sudo journalctl -u ducc-worker -f

# Docker 日志
docker-compose logs -f
```

---

## 备份和恢复

### 1. 数据库备份

#### 自动备份脚本

创建 `/opt/ducc-evaluation/scripts/backup-db.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/opt/ducc-evaluation/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/postgres_$TIMESTAMP.sql"

mkdir -p "$BACKUP_DIR"

# 备份数据库
docker exec ducc-postgres pg_dump -U ducc_user ducc_evaluation > "$BACKUP_FILE"

# 压缩备份
gzip "$BACKUP_FILE"

# 只保留最近30天的备份
find "$BACKUP_DIR" -name "postgres_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

#### 设置定时备份

```bash
# 添加 crontab 任务
crontab -e

# 每天凌晨3点备份
0 3 * * * /opt/ducc-evaluation/scripts/backup-db.sh >> /var/log/ducc-backup.log 2>&1
```

#### 恢复数据库

```bash
# 解压备份文件
gunzip /opt/ducc-evaluation/backups/postgres_20240514_030000.sql.gz

# 恢复数据库
docker exec -i ducc-postgres psql -U ducc_user ducc_evaluation < /opt/ducc-evaluation/backups/postgres_20240514_030000.sql
```

### 2. 数据目录备份

```bash
# 备份数据目录
tar -czf backend_data_$(date +%Y%m%d_%H%M%S).tar.gz \
  /opt/ducc-evaluation/evaluation/backend/data/

# 恢复数据目录
tar -xzf backend_data_20240514_030000.tar.gz -C /
```

### 3. 完整系统备份

```bash
#!/bin/bash
# 完整备份脚本

BACKUP_ROOT="/opt/ducc-evaluation/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 备份数据库
docker exec ducc-postgres pg_dump -U ducc_user ducc_evaluation | gzip > "$BACKUP_ROOT/db_$TIMESTAMP.sql.gz"

# 备份数据目录
tar -czf "$BACKUP_ROOT/data_$TIMESTAMP.tar.gz" /opt/ducc-evaluation/evaluation/backend/data/

# 备份配置文件
tar -czf "$BACKUP_ROOT/config_$TIMESTAMP.tar.gz" \
  /opt/ducc-evaluation/evaluation/backend/.env \
  /opt/ducc-evaluation/evaluation/backend/docker-compose.yml \
  /etc/systemd/system/ducc-*.service \
  /etc/nginx/sites-available/ducc-evaluation

echo "Full backup completed at $TIMESTAMP"
```

---

## 监控和维护

### 1. 系统监控

#### 安装监控工具

```bash
# 安装 htop
sudo apt-get install htop

# 安装 iotop
sudo apt-get install iotop

# 安装 nethogs
sudo apt-get install nethogs
```

#### 监控指标

```bash
# CPU 和内存使用
htop

# 磁盘 I/O
sudo iotop

# 网络使用
sudo nethogs

# 磁盘使用情况
df -h

# 数据库连接数
docker exec ducc-postgres psql -U ducc_user ducc_evaluation -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Redis 内存使用
docker exec ducc-redis redis-cli INFO memory

# 任务队列长度
rq info --url redis://localhost:6379/0
```

### 2. 日志轮转

创建 `/etc/logrotate.d/ducc-evaluation`:

```
/opt/ducc-evaluation/evaluation/backend/data/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 www-data www-data
    sharedscripts
    postrotate
        systemctl reload ducc-backend > /dev/null 2>&1 || true
        systemctl reload ducc-worker > /dev/null 2>&1 || true
    endscript
}
```

### 3. 定期维护任务

创建维护脚本 `/opt/ducc-evaluation/scripts/maintenance.sh`:

```bash
#!/bin/bash

# 清理过期任务日志 (保留 30 天)
find /opt/ducc-evaluation/evaluation/backend/data/logs -name "*.log" -mtime +30 -delete

# 清理结果文件 (保留 90 天)
find /opt/ducc-evaluation/evaluation/backend/data/results -name "*.json" -mtime +90 -delete

# 数据库 VACUUM
docker exec ducc-postgres psql -U ducc_user ducc_evaluation -c "VACUUM ANALYZE;"

# 清理 Docker 资源
docker system prune -f --volumes

echo "Maintenance completed at $(date)"
```

添加到 crontab:

```bash
# 每周日凌晨2点执行维护
0 2 * * 0 /opt/ducc-evaluation/scripts/maintenance.sh >> /var/log/ducc-maintenance.log 2>&1
```

### 4. 性能优化

#### PostgreSQL 优化

编辑 `docker-compose.yml`:

```yaml
services:
  postgres:
    command:
      - postgres
      - -c
      - shared_buffers=256MB
      - -c
      - effective_cache_size=1GB
      - -c
      - work_mem=16MB
      - -c
      - maintenance_work_mem=128MB
      - -c
      - max_connections=200
```

#### Redis 优化

```yaml
services:
  redis:
    command:
      - redis-server
      - --maxmemory
      - 512mb
      - --maxmemory-policy
      - allkeys-lru
```

#### Nginx 优化

```nginx
# 添加到 nginx.conf 或 server 块
worker_processes auto;
worker_connections 1024;

client_max_body_size 100M;
client_body_buffer_size 128k;

proxy_buffer_size 4k;
proxy_buffers 8 4k;
proxy_busy_buffers_size 8k;
```

#### Worker 并发优化

启动多个 Worker 进程，修改 systemd 配置:

```ini
# /etc/systemd/system/ducc-worker@.service (模板单元)
[Unit]
Description=DUCC Evaluation Worker %i
After=network.target redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ducc-evaluation/evaluation/backend
Environment="PATH=/home/user/miniconda3/envs/dejavu/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/user/miniconda3/envs/dejavu/bin/rq worker --url redis://localhost:6379/0 ducc-tasks --name worker-%i
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动多个实例:

```bash
# 启动4个 Worker
sudo systemctl start ducc-worker@{1..4}
sudo systemctl enable ducc-worker@{1..4}
```

---

## 安全加固

### 1. 防火墙配置

```bash
# 启用 UFW
sudo ufw enable

# 只开放必要端口
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS

# 查看状态
sudo ufw status
```

### 2. 修改默认密码

```bash
# 修改数据库密码
docker exec -it ducc-postgres psql -U ducc_user ducc_evaluation
ALTER USER ducc_user WITH PASSWORD 'new_secure_password';
\q

# 更新 .env 文件
vi /opt/ducc-evaluation/evaluation/backend/.env
# DATABASE_URL=postgresql://ducc_user:new_secure_password@localhost:5432/ducc_evaluation

# 更新 docker-compose.yml
vi /opt/ducc-evaluation/evaluation/backend/docker-compose.yml

# 重启服务
docker-compose restart
sudo systemctl restart ducc-backend ducc-worker
```

### 3. 限制数据库访问

修改 PostgreSQL 配置，只允许本地访问:

```yaml
# docker-compose.yml
services:
  postgres:
    ports:
      - "127.0.0.1:5432:5432"  # 只绑定到 localhost
```

### 4. 配置文件权限

```bash
# 限制 .env 文件权限
chmod 600 /opt/ducc-evaluation/evaluation/backend/.env

# 限制日志目录权限
chmod 750 /opt/ducc-evaluation/evaluation/backend/data/logs
```

### 5. 启用 Nginx 安全头

```nginx
# 添加到 server 块
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
```

---

## 故障排查

### 问题 1: Backend 无法启动

```bash
# 检查 conda 环境
conda env list
conda activate dejavu

# 检查依赖
pip list | grep fastapi

# 检查数据库连接
psql -h localhost -U ducc_user -d ducc_evaluation

# 查看详细日志
sudo journalctl -u ducc-backend -n 100 --no-pager
```

### 问题 2: Worker 无法执行任务

```bash
# 检查 Docker 权限
docker ps

# 检查 Redis 连接
redis-cli ping

# 查看 Worker 日志
tail -f /opt/ducc-evaluation/evaluation/backend/data/logs/worker.log

# 查看队列状态
rq info --url redis://localhost:6379/0
```

### 问题 3: 前端无法访问 API

```bash
# 检查 Nginx 配置
sudo nginx -t

# 检查 Backend 是否监听
netstat -tlnp | grep 8000

# 测试 API 直接访问
curl http://localhost:8000/api/v1/datasets/

# 查看 Nginx 日志
tail -f /var/log/nginx/ducc-error.log
```

### 问题 4: 数据库连接池耗尽

```bash
# 查看当前连接数
docker exec ducc-postgres psql -U ducc_user ducc_evaluation -c \
  "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# 杀死空闲连接
docker exec ducc-postgres psql -U ducc_user ducc_evaluation -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '5 minutes';"
```

### 问题 5: 磁盘空间不足

```bash
# 检查磁盘使用
df -h

# 查找大文件
du -h /opt/ducc-evaluation | sort -rh | head -20

# 清理 Docker 资源
docker system prune -a --volumes

# 清理旧日志
find /opt/ducc-evaluation/evaluation/backend/data/logs -name "*.log" -mtime +7 -delete
```

---

## 升级指南

### 1. 准备升级

```bash
# 备份数据库
/opt/ducc-evaluation/scripts/backup-db.sh

# 备份数据目录
tar -czf /opt/ducc-evaluation/backups/data_pre_upgrade.tar.gz \
  /opt/ducc-evaluation/evaluation/backend/data/
```

### 2. 升级后端

```bash
# 停止服务
sudo systemctl stop ducc-backend ducc-worker

# 拉取新代码
cd /opt/ducc-evaluation
git pull origin main

# 激活 conda 环境
conda activate dejavu

# 更新依赖
cd evaluation/backend
pip install -r requirements.txt --upgrade

# 运行数据库迁移 (如果有)
# alembic upgrade head

# 重启服务
sudo systemctl start ducc-backend ducc-worker

# 检查状态
sudo systemctl status ducc-backend ducc-worker
```

### 3. 升级前端

```bash
# 拉取新代码
cd /opt/ducc-evaluation/evaluation/frontend
git pull origin main

# 更新依赖
npm install

# 重新构建
npm run build

# Nginx 自动使用新的静态文件，无需重启
```

### 4. 升级 Docker 镜像

```bash
cd /opt/ducc-evaluation/evaluation/backend

# 停止容器
docker-compose down

# 拉取新镜像
docker-compose pull

# 启动容器
docker-compose up -d

# 检查状态
docker-compose ps
```

### 5. 验证升级

```bash
# 检查服务状态
sudo systemctl status ducc-backend ducc-worker

# 测试 API
curl http://localhost:8000/api/health

# 访问前端
curl http://localhost
```

### 6. 回滚 (如果升级失败)

```bash
# 停止服务
sudo systemctl stop ducc-backend ducc-worker

# 回滚代码
cd /opt/ducc-evaluation
git reset --hard <previous-commit-hash>

# 恢复数据库
gunzip /opt/ducc-evaluation/backups/db_pre_upgrade.sql.gz
docker exec -i ducc-postgres psql -U ducc_user ducc_evaluation < /opt/ducc-evaluation/backups/db_pre_upgrade.sql

# 重启服务
sudo systemctl start ducc-backend ducc-worker
```

---

## 相关文档

- [开发文档](DEVELOPMENT.md) - 开发环境搭建和 API 开发
- [前端文档](FRONTEND.md) - 前端开发指南
- [安装文档](INSTALLATION.md) - 本地开发环境安装
- [架构说明](ARCHITECTURE_CHANGE.md) - 系统架构设计
- [Conda 配置](CONDA_SETUP.md) - Conda 环境配置

---

## 获取帮助

- **项目文档**: `/opt/ducc-evaluation/evaluation/docs/`
- **API 文档**: `http://your-domain.com/docs`
- **日志目录**: `/opt/ducc-evaluation/evaluation/backend/data/logs/`

---

**部署完成！祝使用愉快！🚀**
