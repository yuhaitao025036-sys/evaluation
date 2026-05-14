# 架构调整说明 - 混合部署模式

## 调整背景

原始设计将所有服务（PostgreSQL, Redis, Backend, Worker）都运行在 Docker 容器中。但考虑到评估任务本身需要在 Docker 中运行，这会导致 **Docker in Docker (DinD)** 的问题。

## 问题分析

### 原架构（Docker 全容器化）

```
宿主机
└── Docker Container (Backend + Worker)
    └── Docker Container (评估任务)  ← Docker in Docker
```

**存在的问题：**
1. ❌ Docker in Docker 配置复杂，需要特权模式
2. ❌ 权限管理困难
3. ❌ 性能开销大（多层虚拟化）
4. ❌ 网络配置复杂
5. ❌ 文件路径映射困难（多层挂载）
6. ❌ 调试和开发体验差

## 新架构（混合部署）

### 架构图

```
宿主机
├── PostgreSQL (Docker)          ← 数据存储
├── Redis (Docker)                ← 任务队列
├── Backend API (宿主机进程)     ← FastAPI 服务
├── RQ Worker (宿主机进程)        ← 任务处理
└── 评估任务 (Docker by Worker)  ← Worker 调用宿主机 Docker
```

### 优势

1. ✅ **避免 DinD**: Worker 运行在宿主机，直接访问宿主机 Docker daemon
2. ✅ **简化配置**: 不需要特权模式、socket 挂载等复杂配置
3. ✅ **更好的性能**: 减少一层虚拟化开销
4. ✅ **简化路径管理**: 直接访问宿主机文件系统
5. ✅ **方便开发调试**: Backend 和 Worker 可以直接调试
6. ✅ **灵活扩展**: Worker 可以轻松扩展到多个进程

## 核心改动

### 1. docker-compose.yml

**改动前：** 4 个服务（postgres, redis, backend, worker）

**改动后：** 2 个服务（postgres, redis）

```yaml
# 只保留数据库服务
services:
  postgres:
    image: postgres:15-alpine
    # ... 配置 ...
  
  redis:
    image: redis:7-alpine
    # ... 配置 ...

# 移除了 backend 和 worker 服务
```

### 2. backend/app/worker/task_executor.py

**核心改动：**
```python
# 改动前（在容器内执行）
base_cmd = [sys.executable, script_path, ...]
result = subprocess.run(base_cmd, ...)

# 改动后（强调在宿主机执行，脚本内部调用 Docker）
# Architecture Note: Worker 运行在宿主机
# 评估脚本（如 test_tmux_cc_experience.py）内部调用 Docker

base_cmd = [sys.executable, script_path, ...]
result = subprocess.run(
    base_cmd,
    cwd=str(work_dir),
    env={**os.environ, 'PYTHONUNBUFFERED': '1'}
)
```

**关键点：**
- Worker 在宿主机上执行
- Worker 执行评估脚本（Python）
- 评估脚本内部调用 `docker run` 启动评估容器
- 避免了 Docker in Docker

### 3. 新增安装和启动脚本

#### backend/install.sh
- 创建 Python 虚拟环境
- 安装依赖
- 配置环境变量
- 创建数据目录

#### backend/start_backend.sh
- 激活虚拟环境
- 检查数据库连接
- 启动 FastAPI 服务

#### backend/start_worker.sh
- 激活虚拟环境
- 检查数据库和 Redis 连接
- **检查 Docker 访问**（关键）
- 启动 RQ Worker

### 4. 新增文档

#### docs/INSTALLATION.md
- 详细的安装步骤
- 系统要求说明
- 混合架构说明
- 常见问题解决

#### quickstart.sh 更新
- 检查 Python 和 Docker
- 引导式安装流程
- 清晰的架构说明

## 部署流程

### 新的部署流程

```bash
# 1. 启动数据库服务（Docker）
docker-compose up -d

# 2. 安装 Backend 依赖（宿主机）
cd backend
./install.sh

# 3. 初始化数据库
source venv/bin/activate
python init_db.py

# 4. 启动 Backend API（宿主机进程）
./start_backend.sh

# 5. 启动 Worker（宿主机进程，新终端）
./start_worker.sh
```

### 服务验证

```bash
# 检查 Docker 服务
docker-compose ps

# 检查 Backend
curl http://localhost:8000/health

# 检查 Worker（查看日志）
# Worker 终端应显示: "Worker started, listening to queue: ducc_tasks"
```

## 数据流

### 任务执行流程

```
1. 用户通过 API 创建任务组
   └─> Backend API 接收请求
   
2. Backend 将任务实例加入 Redis 队列
   └─> RQ 队列: ducc_tasks
   
3. Worker (宿主机进程) 从队列取任务
   └─> execute_task_instance(task_id)
   
4. Worker 准备工作目录（宿主机文件系统）
   └─> /path/to/data/outputs/task_X/instance_Y/
   
5. Worker 执行评估脚本（宿主机 Python）
   └─> python test_tmux_cc_experience.py instance_data.json work_dir/
   
6. 评估脚本调用 Docker（宿主机 Docker）
   └─> docker run --rm -v ... evaluation-image
   
7. Docker 容器执行评估任务
   └─> 生成 results.json, generated.patch 等
   
8. Worker 收集结果并更新数据库
   └─> TaskInstance.status = 'completed'
```

### 文件路径

所有路径都在宿主机文件系统：

```
/Users/yuhaitao01/dev/baidu/explore/test/evaluation/
├── data/
│   ├── datasets/          ← 数据集文件
│   ├── scripts/           ← 评估脚本
│   └── outputs/           ← 任务输出
│       └── task_1/
│           └── instance_1/
│               ├── instance_data.json
│               ├── results.json
│               ├── generated.patch
│               ├── stdout.log
│               └── stderr.log
```

Worker 和脚本都可以直接访问这些文件，无需复杂的容器间挂载。

## Docker 访问

### Worker 访问 Docker

Worker 需要能够调用 Docker 命令：

```bash
# Worker 环境检查
docker ps  # 应该能正常执行
```

### 评估脚本调用 Docker

评估脚本（如 `test_tmux_cc_experience.py`）内部使用 Docker：

```python
# 示例：评估脚本内部
import subprocess

# 启动评估容器
subprocess.run([
    'docker', 'run',
    '--rm',
    '-v', f'{work_dir}:/workspace',
    'evaluation-image:latest',
    '/app/run_evaluation.sh'
])
```

这样的调用会使用宿主机的 Docker daemon，**不会**导致 Docker in Docker。

## 环境配置

### .env 文件

```bash
# 数据库连接（localhost，因为 Docker 端口映射）
DATABASE_URL=postgresql://ducc:ducc123@localhost:5432/ducc_eval

# Redis 连接（localhost）
REDIS_URL=redis://localhost:6379/0

# 数据目录（宿主机绝对路径）
DATA_DIR=/Users/yuhaitao01/dev/baidu/explore/test/evaluation/data
DATASETS_DIR=/Users/yuhaitao01/dev/baidu/explore/test/evaluation/data/datasets
SCRIPTS_DIR=/Users/yuhaitao01/dev/baidu/explore/test/evaluation/data/scripts
OUTPUTS_DIR=/Users/yuhaitao01/dev/baidu/explore/test/evaluation/data/outputs
```

**关键点：**
- 数据库和 Redis 使用 `localhost`（Docker 端口映射）
- 所有路径都是宿主机绝对路径

## 优点总结

| 方面 | 原架构（全 Docker） | 新架构（混合部署） |
|------|-------------------|------------------|
| Docker in Docker | ❌ 需要 | ✅ 避免 |
| 配置复杂度 | ❌ 高 | ✅ 低 |
| 性能 | ❌ 多层开销 | ✅ 更好 |
| 开发调试 | ❌ 困难 | ✅ 方便 |
| 文件访问 | ❌ 多层挂载 | ✅ 直接访问 |
| Worker 扩展 | ⚠️ 需要容器编排 | ✅ 简单启动多个进程 |

## 注意事项

1. **Docker 权限**: 确保运行 Backend/Worker 的用户有 Docker 权限
   ```bash
   sudo usermod -aG docker $USER
   ```

2. **虚拟环境**: Backend 和 Worker 使用相同的虚拟环境
   ```bash
   cd backend
   source venv/bin/activate
   ```

3. **端口占用**: 确保 5432 (PostgreSQL), 6379 (Redis), 8000 (Backend) 端口可用

4. **数据持久化**: PostgreSQL 和 Redis 数据通过 Docker volume 持久化

## 迁移指南

如果已经使用旧架构部署，迁移步骤：

```bash
# 1. 停止所有容器
docker-compose down

# 2. 备份数据（可选）
docker-compose down -v  # 删除卷，慎用

# 3. 拉取最新代码

# 4. 安装新架构
./quickstart.sh

# 5. 启动服务
# 终端 1
cd backend && ./start_backend.sh

# 终端 2
cd backend && ./start_worker.sh
```

## 总结

新的混合部署架构：
- ✅ 解决了 Docker in Docker 问题
- ✅ 简化了配置和部署
- ✅ 提升了性能和开发体验
- ✅ 保持了系统功能完整性

这是针对我们特定场景（评估任务需要 Docker）的最佳实践方案。
