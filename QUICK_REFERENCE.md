# DUCC 评估系统 - 快速参考

## 📂 项目位置
```
/Users/yuhaitao01/dev/baidu/explore/test/evaluation/
```

## 🚀 快速启动

### 方式 1: 一键启动（推荐）
```bash
cd /Users/yuhaitao01/dev/baidu/explore/test/evaluation
./quickstart.sh
```

### 方式 2: Docker Compose
```bash
cd /Users/yuhaitao01/dev/baidu/explore/test/evaluation
docker-compose up -d
```

### 方式 3: 本地开发
```bash
# 终端1: 启动后端
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# 终端2: 启动 Worker
python -m rq.cli worker --url redis://localhost:6379/0 ducc_tasks
```

## 🔍 验证安装
```bash
python verify.py
```

## 📍 服务地址

| 服务 | 地址 | 说明 |
|------|------|------|
| Backend API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Health Check | http://localhost:8000/health | 健康检查 |
| PostgreSQL | localhost:5432 | 数据库 |
| Redis | localhost:6379 | 缓存/队列 |

## 🗄️ 数据库连接

```bash
# 连接数据库
psql -U ducc -d ducc_eval

# 或使用 Docker
docker-compose exec postgres psql -U ducc -d ducc_eval
```

默认凭证: `ducc` / `ducc123`

## 📁 目录结构

```
evaluation/
├── backend/           # 后端代码
│   ├── app/          # 应用代码
│   ├── schema.sql    # 数据库 schema
│   └── requirements.txt
├── data/              # 数据目录
│   ├── datasets/     # 数据集 (.parquet)
│   ├── scripts/      # 脚本 (.py)
│   └── outputs/      # 输出结果
├── docs/              # 文档
├── docker-compose.yml # Docker 配置
└── README.md          # 主文档
```

## 🛠️ 常用命令

### Docker 管理
```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f worker

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart

# 查看服务状态
docker-compose ps
```

### 数据库管理
```bash
# 初始化数据库
cd backend
python scripts/init_db.py

# 或使用 SQL
psql -U ducc -d ducc_eval -f schema.sql

# 查看所有表
psql -U ducc -d ducc_eval -c "\dt"

# 删除所有表（重置）
psql -U ducc -d ducc_eval -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

### 数据准备
```bash
# 复制数据集
cp ../datasets/*.parquet data/datasets/

# 复制脚本
cp ../test_tmux_cc_experience.py data/scripts/

# 检查文件
ls -lh data/datasets/
ls -lh data/scripts/
```

## 🧪 API 测试

### 健康检查
```bash
curl http://localhost:8000/health
```

### WebSocket 测试
```bash
# 使用 websocat (需要先安装)
websocat ws://localhost:8000/ws/test-id
```

## 📊 监控

### 查看 Worker 状态
```bash
# 连接到 Redis 查看队列
redis-cli
> LLEN rq:queue:ducc_tasks
> KEYS rq:*
```

### 查看数据库统计
```bash
psql -U ducc -d ducc_eval << 'EOF'
SELECT 
  (SELECT COUNT(*) FROM datasets) as datasets,
  (SELECT COUNT(*) FROM scripts) as scripts,
  (SELECT COUNT(*) FROM tasks) as tasks,
  (SELECT COUNT(*) FROM task_instances) as task_instances;
EOF
```

## 🐛 故障排查

### 端口被占用
```bash
# 查看端口占用
lsof -i :8000  # Backend
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# 杀死进程
kill -9 <PID>
```

### 重置系统
```bash
# 停止并删除所有容器和数据
docker-compose down -v

# 重新启动
docker-compose up -d
```

### 查看详细日志
```bash
# Backend
docker-compose logs --tail=100 backend

# Worker
docker-compose logs --tail=100 worker

# Database
docker-compose logs --tail=100 postgres
```

## 📚 文档位置

| 文档 | 路径 |
|------|------|
| 主文档 | README.md |
| 部署指南 | docs/DEPLOYMENT.md |
| 设计文档 | ~/.comate/plans/DUCC_任务评估系统架构设计_*.plan.md |

## 🔗 相关资源

- FastAPI 文档: https://fastapi.tiangolo.com/
- PostgreSQL 文档: https://www.postgresql.org/docs/
- RQ 文档: https://python-rq.org/
- Docker Compose: https://docs.docker.com/compose/

## 💡 常见工作流

### 1. 创建新任务
```bash
# 1. 扫描数据集
curl -X POST http://localhost:8000/api/v1/datasets/scan

# 2. 扫描脚本
curl -X POST http://localhost:8000/api/v1/scripts/scan

# 3. 创建任务
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": 1, "script_id": 1}'
```

### 2. 查看结果
```bash
# 查看所有任务
curl http://localhost:8000/api/v1/tasks

# 查看特定任务
curl http://localhost:8000/api/v1/tasks/1

# 查看任务实例
curl http://localhost:8000/api/v1/tasks/1/instances
```

## 📞 获取帮助

1. 检查 README.md
2. 阅读 docs/DEPLOYMENT.md
3. 查看 API 文档: http://localhost:8000/docs
4. 查看设计文档了解架构

---

最后更新: 2026-05-13
