# 安装指南

本文档详细说明 DUCC Evaluation System 的安装和配置流程。

## 系统架构

本系统采用**混合部署架构**，避免 Docker in Docker 的复杂性：

```
宿主机
├── PostgreSQL (Docker 容器)          # 数据库
├── Redis (Docker 容器)                # 队列和缓存
├── Backend API (宿主机进程)           # FastAPI 服务
├── RQ Worker (宿主机进程)             # 后台任务处理
└── 评估任务 (Docker 容器 by Worker)   # Worker 调用 Docker 执行
```

**为什么这样设计？**
- ✅ 避免 Docker in Docker (DinD) 的复杂配置
- ✅ Worker 可以直接访问宿主机的 Docker daemon
- ✅ 简化文件路径和网络配置
- ✅ 更好的性能和调试体验

## 系统要求

### 必需组件

| 组件 | 版本要求 | 用途 |
|------|---------|------|
| Python | 3.8+ | Backend 和 Worker |
| pip | 最新版本 | Python 包管理 |
| Docker | 20.10+ | 数据库 + 评估任务容器 |
| docker-compose | 1.29+ | 编排数据库服务 |
| PostgreSQL | 15 (Docker) | 数据存储 |
| Redis | 7 (Docker) | 任务队列 |

### 可选组件

| 组件 | 用途 |
|------|------|
| tmux | 多终端管理（方便同时运行多个服务）|
| VS Code | 开发和调试 |

### 硬件要求

- **CPU**: 4核或更多（并发执行任务）
- **内存**: 8GB+ 推荐
- **磁盘**: 50GB+ 可用空间
  - 数据库: ~5GB
  - 数据集: 根据实际情况
  - 输出结果: ~10GB+

## 安装步骤

### 1. 克隆或下载项目

```bash
cd /Users/yuhaitao01/dev/baidu/explore/test/evaluation
```

### 2. 检查 Docker 环境

确保 Docker 已安装并运行：

```bash
# 检查 Docker 版本
docker --version
# 输出示例: Docker version 24.0.5, build ced0996

# 检查 Docker 是否运行
docker ps
# 应该能正常执行，不报错

# 检查 docker-compose
docker-compose --version
# 输出示例: docker-compose version 1.29.2
```

如果 Docker 未安装，请访问 [Docker 官网](https://www.docker.com/get-started) 下载安装。

### 3. 启动数据库服务

使用 Docker Compose 启动 PostgreSQL 和 Redis：

```bash
# 在项目根目录
cd /Users/yuhaitao01/dev/baidu/explore/test/evaluation

# 启动数据库服务（后台运行）
docker-compose up -d

# 查看服务状态
docker-compose ps
```

输出应该类似：

```
NAME              COMMAND                  SERVICE    STATUS      PORTS
ducc_postgres     "docker-entrypoint.s…"   postgres   Up          0.0.0.0:5432->5432/tcp
ducc_redis        "docker-entrypoint.s…"   redis      Up          0.0.0.0:6379->6379/tcp
```

**验证数据库连接：**

```bash
# 测试 PostgreSQL 连接
docker exec ducc_postgres psql -U ducc -d ducc_eval -c "SELECT version();"

# 测试 Redis 连接
docker exec ducc_redis redis-cli ping
# 输出: PONG
```

### 4. 安装 Python 依赖

```bash
cd backend

# 运行安装脚本
./install.sh
```

安装脚本会自动：
1. 创建 Python 虚拟环境 (`venv/`)
2. 升级 pip
3. 安装所有 Python 依赖
4. 复制环境变量模板 (`.env`)
5. 创建数据目录

**手动安装（如果脚本失败）：**

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt

# 复制环境变量
cp .env.example .env
```

### 5. 配置环境变量

编辑 `backend/.env` 文件：

```bash
cd backend
vim .env  # 或使用其他编辑器
```

关键配置项：

```bash
# 应用配置
APP_NAME="DUCC Evaluation System"
DEBUG=True  # 生产环境设置为 False

# 数据库配置（Docker 服务）
# ⚠️ 这是旧配置示例，请参考 .env.example 使用新配置
DATABASE_URL=postgresql://ducc_user:YOUR_SECURE_PASSWORD_HERE@localhost:5432/ducc_evaluation

# Redis 配置（Docker 服务）
REDIS_URL=redis://localhost:6379/0

# 数据目录（确保路径正确）
DATA_DIR=/Users/yuhaitao01/dev/baidu/explore/test/evaluation/data
DATASETS_DIR=/Users/yuhaitao01/dev/baidu/explore/test/evaluation/data/datasets
SCRIPTS_DIR=/Users/yuhaitao01/dev/baidu/explore/test/evaluation/data/scripts
OUTPUTS_DIR=/Users/yuhaitao01/dev/baidu/explore/test/evaluation/data/outputs

# 任务超时（秒）
TASK_TIMEOUT_SECONDS=3600  # 1小时

# CORS 配置
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

### 6. 初始化数据库

```bash
cd backend
source venv/bin/activate  # 确保已激活虚拟环境

# 初始化数据库表
python init_db.py
```

输出应该类似：

```
Creating database tables...
Database tables created successfully!

Created tables:
  - datasets
  - dataset_instances
  - scripts
  - task_groups
  - tasks
  - task_instances
  - task_logs
  - comparisons
```

**验证数据库表：**

```bash
docker exec ducc_postgres psql -U ducc -d ducc_eval -c "\dt"
```

### 7. 准备数据目录

确保数据目录存在并有正确的权限：

```bash
cd /Users/yuhaitao01/dev/baidu/explore/test/evaluation

# 创建目录
mkdir -p data/datasets data/scripts data/outputs

# 检查目录
ls -la data/
```

**放置评估脚本：**

将你的评估脚本（例如 `test_tmux_cc_experience.py`）放到 `data/scripts/` 目录：

```bash
cp /path/to/test_tmux_cc_experience.py data/scripts/
```

**放置数据集：**

将数据集文件放到 `data/datasets/` 目录：

```bash
cp /path/to/swe_bench_pro.parquet data/datasets/
```

## 启动服务

### 方式 1: 使用启动脚本（推荐）

**终端 1 - 启动 Backend API:**

```bash
cd backend
./start_backend.sh
```

输出：

```
======================================
启动 DUCC Evaluation Backend API
======================================

✓ 环境检查通过

启动 Backend API 服务...
访问地址: http://localhost:8000
API 文档: http://localhost:8000/docs

INFO:     Uvicorn running on http://0.0.0.0:8000
```

**终端 2 - 启动 Worker:**

```bash
cd backend
./start_worker.sh
```

输出：

```
======================================
启动 DUCC Evaluation Worker
======================================

✓ 环境检查通过

启动 RQ Worker...
队列: ducc_tasks

Worker started, listening to queue: ducc_tasks
```

### 方式 2: 手动启动

**终端 1 - Backend:**

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**终端 2 - Worker:**

```bash
cd backend
source venv/bin/activate
python worker.py
```

### 方式 3: 使用 tmux（推荐用于开发）

```bash
# 启动 tmux 会话
tmux new -s ducc

# 窗口 0: Backend
cd backend && ./start_backend.sh

# 新建窗口 (Ctrl+b c)
cd backend && ./start_worker.sh

# 切换窗口: Ctrl+b 0/1/2
# 分离会话: Ctrl+b d
# 重新连接: tmux attach -t ducc
```

## 验证安装

### 1. 检查 Backend API

```bash
# 健康检查
curl http://localhost:8000/health
# 输出: {"status":"healthy"}

# 查看 API 信息
curl http://localhost:8000/
# 输出: {"name":"DUCC Evaluation System","version":"1.0.0","status":"running"}
```

### 2. 访问 API 文档

打开浏览器访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 3. 测试数据库连接

```bash
# 扫描数据集
curl -X POST http://localhost:8000/api/v1/datasets/scan

# 扫描脚本
curl -X POST http://localhost:8000/api/v1/scripts/scan

# 获取模型列表
curl http://localhost:8000/api/v1/models
```

### 4. 测试 Worker

查看 Worker 终端日志，应该看到类似输出：

```
Worker started, listening to queue: ducc_tasks
```

### 5. 测试 Docker 访问

Worker 需要能够访问宿主机的 Docker：

```bash
# 在 Worker 环境中测试
cd backend
source venv/bin/activate
python -c "import subprocess; subprocess.run(['docker', 'ps'])"
```

应该能正常执行，不报错。

## 常见问题

### 问题 1: 数据库连接失败

**错误信息:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**解决方案:**

1. 确认 PostgreSQL 容器运行中：
   ```bash
   docker-compose ps postgres
   ```

2. 检查端口是否被占用：
   ```bash
   lsof -i:5432
   ```

3. 检查 `.env` 中的数据库配置是否正确

### 问题 2: Redis 连接失败

**错误信息:**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**解决方案:**

1. 确认 Redis 容器运行中：
   ```bash
   docker-compose ps redis
   ```

2. 测试 Redis 连接：
   ```bash
   redis-cli ping
   ```

### 问题 3: Worker 无法访问 Docker

**错误信息:**
```
无法访问 Docker
```

**解决方案:**

1. 确认 Docker daemon 运行中：
   ```bash
   docker ps
   ```

2. 检查当前用户是否在 docker 组中：
   ```bash
   groups $USER
   ```

3. 如果不在，添加用户到 docker 组：
   ```bash
   sudo usermod -aG docker $USER
   # 然后重新登录
   ```

### 问题 4: 端口被占用

**错误信息:**
```
ERROR: Address already in use
```

**解决方案:**

查找并停止占用端口的进程：

```bash
# 查找占用 8000 端口的进程
lsof -i:8000

# 杀死进程
kill -9 <PID>
```

### 问题 5: 虚拟环境激活失败

**解决方案:**

```bash
# 删除旧的虚拟环境
rm -rf venv

# 重新创建
python3 -m venv venv

# 激活
source venv/bin/activate

# 重新安装依赖
pip install -r requirements.txt
```

## 卸载

### 停止服务

```bash
# 停止 Backend 和 Worker (Ctrl+C)

# 停止数据库服务
cd /Users/yuhaitao01/dev/baidu/explore/test/evaluation
docker-compose down
```

### 删除数据（谨慎）

```bash
# 删除 Docker 数据卷
docker-compose down -v

# 删除虚拟环境
cd backend
rm -rf venv

# 删除数据目录（可选）
cd ..
rm -rf data/outputs/*
```

## 升级

### 更新代码

```bash
cd /Users/yuhaitao01/dev/baidu/explore/test/evaluation
git pull  # 如果使用 Git
```

### 更新依赖

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### 更新数据库

如果有新的 migration：

```bash
cd backend
source venv/bin/activate
# 执行 migration 脚本
psql $DATABASE_URL -f migrations/xxx.sql
```

## 下一步

安装完成后，查看：

- [API 测试指南](API_TESTING.md) - 学习如何使用 API
- [部署文档](DEPLOYMENT.md) - 生产环境部署
- [README](../README.md) - 项目概览

## 技术支持

如果遇到问题：

1. 检查日志文件
2. 查看 [常见问题](#常见问题) 部分
3. 提交 Issue 或联系开发团队
