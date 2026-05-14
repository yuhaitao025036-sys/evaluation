# DUCC 评测系统开发文档

## 目录

1. [系统概述](#系统概述)
2. [技术架构](#技术架构)
3. [开发环境搭建](#开发环境搭建)
4. [后端开发](#后端开发)
5. [前端开发](#前端开发)
6. [数据库设计](#数据库设计)
7. [API 文档](#api-文档)
8. [开发规范](#开发规范)
9. [测试](#测试)
10. [常见问题](#常见问题)

---

## 系统概述

DUCC 评测系统是一个用于管理和执行代码评测任务的 Web 平台，支持：

- 数据集和评测脚本管理
- 批量任务调度和并发执行
- 多模型、多标签对比实验
- 结果分析和可视化

### 核心功能

1. **数据管理**: 数据集、实例、脚本的 CRUD 操作
2. **任务调度**: 任务组创建、自动批次划分、并发执行
3. **进度监控**: 实时任务状态、进度追踪
4. **结果对比**: 模型对比、标签对比、实例对比
5. **失败重试**: 自动重试机制

---

## 技术架构

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                          用户浏览器                            │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/WebSocket
┌──────────────────────────┴──────────────────────────────────┐
│                    前端 (React + Vite)                        │
│  - React 18 + TypeScript                                     │
│  - Ant Design 5 (UI)                                        │
│  - Axios (HTTP Client)                                       │
│  - React Router (路由)                                        │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────┴──────────────────────────────────┐
│              后端 (FastAPI + SQLAlchemy)                     │
│  - FastAPI (Web框架)                                         │
│  - SQLAlchemy (ORM)                                          │
│  - Pydantic (数据验证)                                        │
│  - RQ (任务队列)                                              │
└───────────┬──────────────────────────────┬──────────────────┘
            │                              │
            │ SQL                          │ Enqueue
            ↓                              ↓
┌───────────────────────┐      ┌───────────────────────┐
│  PostgreSQL (Docker)  │      │    Redis (Docker)     │
│  - 数据持久化          │      │  - 任务队列            │
│  - JSONB 灵活存储      │      │  - 缓存               │
└───────────────────────┘      └──────────┬────────────┘
                                          │ Dequeue
                              ┌───────────┴────────────┐
                              │   RQ Worker (宿主机)    │
                              │  - 任务执行              │
                              │  - Docker 调用          │
                              └───────────┬────────────┘
                                          │ Docker API
                              ┌───────────┴────────────┐
                              │  评测任务 (Docker容器)  │
                              │  - 独立环境              │
                              │  - 脚本执行              │
                              └────────────────────────┘
```

### 技术栈

**后端**:
- **Web 框架**: FastAPI 0.104+
- **ORM**: SQLAlchemy 2.0+
- **数据库**: PostgreSQL 15
- **缓存/队列**: Redis 7
- **任务队列**: RQ (Redis Queue)
- **数据验证**: Pydantic V2
- **Python 版本**: 3.12+

**前端**:
- **框架**: React 18
- **语言**: TypeScript 5
- **构建工具**: Vite 5
- **UI 库**: Ant Design 5
- **HTTP 客户端**: Axios
- **路由**: React Router v6
- **状态管理**: Zustand (计划)
- **图表**: Recharts (计划)

**部署**:
- **数据库容器**: Docker + Docker Compose
- **应用进程**: Conda 环境 (宿主机)
- **进程管理**: Supervisor / systemd
- **反向代理**: Nginx
- **HTTPS**: Certbot (Let's Encrypt)

---

## 开发环境搭建

### 前置条件

- macOS / Linux
- Docker 20.10+
- Docker Compose 1.29+
- Conda (Miniconda 或 Anaconda)
- Node.js 16+
- Git

### 1. 克隆项目

```bash
git clone <repository-url>
cd evaluation
```

### 2. 后端环境

```bash
cd backend

# 创建 conda 环境
conda create -n dejavu python=3.12 -y
conda activate dejavu

# 安装依赖
pip install -r requirements.txt

# 创建 .env 文件
cat > .env << 'EOF'
DATABASE_URL=postgresql://ducc_user:ducc_pass@localhost:5432/ducc_evaluation
REDIS_URL=redis://localhost:6379/0
DEBUG=true
SECRET_KEY=dev-secret-key
EOF

# 启动数据库 (Docker)
docker-compose up -d

# 初始化数据库
python -c "from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"

# 创建数据目录
mkdir -p data/scripts data/results data/logs
```

### 3. 前端环境

```bash
cd ../frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 启动服务

**终端 1 - Backend**:
```bash
cd backend
conda activate dejavu
./start_backend.sh
```

**终端 2 - Worker**:
```bash
cd backend
conda activate dejavu
./start_worker.sh
```

**终端 3 - Frontend**:
```bash
cd frontend
npm run dev
```

访问: `http://localhost:5173`

---

## 后端开发

### 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── database.py          # 数据库连接
│   ├── models/              # SQLAlchemy 模型
│   │   └── __init__.py      # 8个表模型
│   ├── schemas/             # Pydantic schemas
│   │   ├── dataset.py
│   │   ├── script.py
│   │   ├── task_group.py
│   │   └── ...
│   ├── api/                 # API 路由
│   │   └── v1/
│   │       ├── datasets.py
│   │       ├── scripts.py
│   │       ├── models.py
│   │       ├── task_groups.py
│   │       ├── task_instances.py
│   │       └── comparisons.py
│   ├── services/            # 业务逻辑
│   │   ├── dataset_service.py
│   │   ├── task_service.py
│   │   └── comparison_service.py
│   └── worker/              # RQ Worker
│       └── task_executor.py # 任务执行器
├── data/                    # 数据目录
│   ├── scripts/             # 评测脚本
│   ├── results/             # 执行结果
│   └── logs/                # 日志文件
├── requirements.txt         # Python 依赖
├── docker-compose.yml       # 数据库服务
├── start_backend.sh         # 后端启动脚本
└── start_worker.sh          # Worker 启动脚本
```

### 添加新的 API 端点

**1. 定义 Schema** (`app/schemas/example.py`):

```python
from pydantic import BaseModel
from typing import Optional

class ExampleCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ExampleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    
    class Config:
        from_attributes = True
```

**2. 创建路由** (`app/api/v1/examples.py`):

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.example import ExampleCreate, ExampleResponse
from app.models import Example

router = APIRouter()

@router.post("/", response_model=ExampleResponse)
def create_example(data: ExampleCreate, db: Session = Depends(get_db)):
    example = Example(**data.dict())
    db.add(example)
    db.commit()
    db.refresh(example)
    return example

@router.get("/{id}", response_model=ExampleResponse)
def get_example(id: int, db: Session = Depends(get_db)):
    example = db.query(Example).filter(Example.id == id).first()
    if not example:
        raise HTTPException(status_code=404, detail="Example not found")
    return example
```

**3. 注册路由** (`app/main.py`):

```python
from app.api.v1 import examples

app.include_router(examples.router, prefix="/api/v1/examples", tags=["examples"])
```

### 添加后台任务

**定义任务** (`app/worker/tasks.py`):

```python
from app.database import SessionLocal
from app.models import TaskInstance

def process_example_task(task_instance_id: int):
    db = SessionLocal()
    try:
        task_instance = db.query(TaskInstance).filter(
            TaskInstance.id == task_instance_id
        ).first()
        
        # 执行任务逻辑
        result = {"status": "success", "data": "..."}
        
        # 更新状态
        task_instance.status = "completed"
        task_instance.result_data = result
        db.commit()
        
    finally:
        db.close()
```

**入队任务**:

```python
from redis import Redis
from rq import Queue

redis_conn = Redis.from_url("redis://localhost:6379/0")
queue = Queue("ducc-tasks", connection=redis_conn)

job = queue.enqueue(
    process_example_task,
    task_instance_id=123,
    timeout=600
)
```

### 数据库迁移 (Alembic)

```bash
# 初始化 Alembic (首次)
alembic init alembic

# 创建迁移
alembic revision --autogenerate -m "Add new column"

# 应用迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

---

## 前端开发

### 项目结构

```
frontend/
├── public/                  # 静态资源
├── src/
│   ├── api/                # API 客户端
│   │   ├── client.ts       # Axios 实例
│   │   ├── datasets.ts     # 数据集 API
│   │   ├── scripts.ts      # 脚本 API
│   │   ├── models.ts       # 模型 API
│   │   ├── taskGroups.ts   # 任务组 API
│   │   ├── taskInstances.ts # 任务实例 API
│   │   └── comparisons.ts  # 对比 API
│   ├── components/         # 公共组件
│   │   └── Layout/         # 布局组件
│   ├── pages/              # 页面组件
│   │   ├── Dashboard/      # 任务面板
│   │   ├── DataManagement/ # 数据管理
│   │   ├── TaskCreate/     # 创建任务
│   │   ├── TaskDetail/     # 任务详情
│   │   └── Comparison/     # 结果对比
│   ├── types/              # TypeScript 类型
│   │   └── index.ts
│   ├── App.tsx             # 根组件
│   ├── main.tsx            # 入口文件
│   └── index.css           # 全局样式
├── index.html              # HTML 模板
├── package.json            # 依赖配置
├── tsconfig.json           # TS 配置
├── vite.config.ts          # Vite 配置
└── start_dev.sh            # 开发启动脚本
```

### 添加新页面

**1. 创建页面组件** (`src/pages/NewPage/index.tsx`):

```typescript
import { Card } from 'antd'

export default function NewPage() {
  return (
    <Card title="新页面">
      <p>页面内容</p>
    </Card>
  )
}
```

**2. 添加路由** (`src/App.tsx`):

```typescript
import NewPage from './pages/NewPage'

<Route path="new-page" element={<NewPage />} />
```

**3. 添加导航** (`src/components/Layout/Sidebar.tsx`):

```typescript
const items: MenuItem[] = [
  // ...
  {
    key: '/new-page',
    icon: <AppstoreOutlined />,
    label: '新页面',
  },
]
```

### 调用 API

**方式一：直接调用**:

```typescript
import { datasetsApi } from '@/api/datasets'

const fetchData = async () => {
  try {
    const response = await datasetsApi.list({ page: 1, page_size: 10 })
    console.log(response.items)
  } catch (error) {
    console.error('Failed to fetch:', error)
  }
}
```

**方式二：结合 React Hooks**:

```typescript
import { useState, useEffect } from 'react'
import { datasetsApi } from '@/api/datasets'
import { Dataset } from '@/types'

export default function DatasetList() {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const res = await datasetsApi.list()
        setDatasets(res.items)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  return <Table dataSource={datasets} loading={loading} />
}
```

### 添加新的 API 服务

**创建服务模块** (`src/api/newService.ts`):

```typescript
import client from './client'
import { NewType } from '@/types'

export const newServiceApi = {
  list: (params?: { page?: number }) => 
    client.get<any, { items: NewType[] }>('/v1/new-service/', { params }),

  get: (id: number) => 
    client.get<any, NewType>(`/v1/new-service/${id}`),

  create: (data: { name: string }) => 
    client.post<any, NewType>('/v1/new-service/', data),

  update: (id: number, data: Partial<NewType>) => 
    client.put<any, NewType>(`/v1/new-service/${id}`, data),

  delete: (id: number) => 
    client.delete(`/v1/new-service/${id}`),
}
```

### 样式规范

使用 Ant Design 的内联样式或 CSS Modules：

```typescript
// 内联样式
<div style={{ padding: 16, marginTop: 24 }}>...</div>

// CSS Module
import styles from './index.module.css'
<div className={styles.container}>...</div>
```

---

## 数据库设计

### ER 图

```
Dataset (数据集)
├── id (PK)
├── name
├── description
├── created_at
└── updated_at

DatasetInstance (数据集实例)
├── id (PK)
├── dataset_id (FK → Dataset)
├── instance_id (唯一标识)
├── data (JSONB, 灵活数据)
├── created_at
└── updated_at

Script (评测脚本)
├── id (PK)
├── name
├── description
├── file_path
├── created_at
└── updated_at

TaskGroup (任务组)
├── id (PK)
├── name
├── description
├── dataset_id (FK → Dataset)
├── script_id (FK → Script)
├── tag (批次标签)
├── model (模型名称)
├── concurrency (并发数)
├── filter_conditions (JSONB, 过滤条件)
├── status (pending/running/completed/failed)
├── total_tasks
├── completed_tasks
├── failed_tasks
├── created_at
└── updated_at

Task (子任务)
├── id (PK)
├── task_group_id (FK → TaskGroup)
├── batch_index (批次索引)
├── model
├── status
├── started_at
├── completed_at
├── created_at
└── updated_at

TaskInstance (任务实例)
├── id (PK)
├── task_id (FK → Task)
├── instance_id (数据实例ID)
├── tag (批次标签)
├── model (模型名称)
├── input_data (JSONB)
├── result_data (JSONB)
├── patch_content (TEXT)
├── status (pending/running/completed/failed/timeout)
├── error_message
├── started_at
├── completed_at
├── duration
├── created_at
└── updated_at
└── UNIQUE (instance_id, tag)

TaskLog (任务日志)
├── id (PK)
├── task_id (FK → Task)
├── log_level (info/warning/error)
├── message
└── created_at

Comparison (对比记录)
├── id (PK)
├── name
├── description
├── baseline_tag
├── comparison_tags (ARRAY)
├── model
├── filter_conditions (JSONB)
├── result_summary (JSONB)
├── created_at
└── updated_at
```

### 关键索引

```sql
-- 高频查询字段索引
CREATE INDEX idx_dataset_instance_dataset_id ON dataset_instances(dataset_id);
CREATE INDEX idx_dataset_instance_instance_id ON dataset_instances(instance_id);
CREATE INDEX idx_task_group_status ON task_groups(status);
CREATE INDEX idx_task_group_tag ON task_groups(tag);
CREATE INDEX idx_task_instance_task_id ON task_instances(task_id);
CREATE INDEX idx_task_instance_instance_id ON task_instances(instance_id);
CREATE INDEX idx_task_instance_tag ON task_instances(tag);
CREATE INDEX idx_task_instance_status ON task_instances(status);

-- JSONB 字段索引
CREATE INDEX idx_dataset_instance_data ON dataset_instances USING GIN(data);
CREATE INDEX idx_task_instance_result_data ON task_instances USING GIN(result_data);
```

---

## API 文档

### Base URL

```
开发环境: http://localhost:8000/api
生产环境: https://your-domain.com/api
```

### 认证

当前版本未实现认证，后续版本将支持 JWT Token。

### 通用响应格式

**成功响应**:
```json
{
  "id": 1,
  "name": "example",
  "created_at": "2024-05-14T12:00:00"
}
```

**分页响应**:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 10,
  "pages": 10
}
```

**错误响应**:
```json
{
  "detail": "Error message"
}
```

### 核心端点

#### 数据集 API

```
GET    /v1/datasets/                     # 列表
POST   /v1/datasets/                     # 创建
GET    /v1/datasets/{id}                 # 详情
PUT    /v1/datasets/{id}                 # 更新
DELETE /v1/datasets/{id}                 # 删除
GET    /v1/datasets/{id}/instances       # 实例列表
POST   /v1/datasets/{id}/instances       # 添加实例
POST   /v1/datasets/{id}/import          # 导入 JSONL
```

#### 脚本 API

```
GET    /v1/scripts/                      # 列表
GET    /v1/scripts/{id}                  # 详情
POST   /v1/scripts/scan                  # 扫描目录
```

#### 模型 API

```
GET    /v1/models/                       # 模型列表
```

#### 任务组 API

```
GET    /v1/task-groups/                  # 列表
POST   /v1/task-groups/                  # 创建
GET    /v1/task-groups/{id}              # 详情
DELETE /v1/task-groups/{id}              # 删除
POST   /v1/task-groups/{id}/start        # 启动
POST   /v1/task-groups/{id}/stop         # 停止
POST   /v1/task-groups/{id}/retry        # 重试失败任务
GET    /v1/task-groups/stats             # 统计
GET    /v1/task-groups/{id}/tasks        # 子任务列表
```

#### 任务实例 API

```
GET    /v1/task-instances/                      # 列表
GET    /v1/task-instances/{id}                  # 详情
POST   /v1/task-instances/{id}/retry            # 重试
GET    /v1/task-instances/instance/{id}         # 按 instance_id 查询
GET    /v1/task-instances/stats                 # 统计
```

#### 对比 API

```
GET    /v1/comparisons/                         # 对比记录列表
POST   /v1/comparisons/                         # 创建对比
GET    /v1/comparisons/{id}                     # 详情
DELETE /v1/comparisons/{id}                     # 删除
POST   /v1/comparisons/compare-models           # 模型对比
POST   /v1/comparisons/compare-tags             # 标签对比
GET    /v1/comparisons/instance/{instance_id}   # 实例对比
GET    /v1/comparisons/tags                     # 标签列表
GET    /v1/comparisons/models-in-use            # 使用中的模型
```

### API 测试

使用 `curl`:

```bash
# 创建数据集
curl -X POST http://localhost:8000/api/v1/datasets/ \
  -H "Content-Type: application/json" \
  -d '{"name": "测试数据集", "description": "描述"}'

# 获取列表
curl http://localhost:8000/api/v1/datasets/?page=1&page_size=10
```

使用 Postman 或 Insomnia 导入 OpenAPI 文档:

```bash
# 访问自动生成的 API 文档
http://localhost:8000/docs
```

---

## 开发规范

### Git 提交规范

使用 Conventional Commits:

```
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式调整
refactor: 重构
test: 测试相关
chore: 构建/工具相关
```

示例:
```bash
git commit -m "feat: add model comparison API"
git commit -m "fix: resolve database connection timeout"
git commit -m "docs: update deployment guide"
```

### 代码风格

**Python (Black + isort)**:

```bash
# 安装工具
pip install black isort flake8

# 格式化代码
black .
isort .

# 检查
flake8 app/
```

**TypeScript (ESLint + Prettier)**:

```bash
# 已在 package.json 中配置
npm run lint
npm run format
```

### 命名规范

**Python**:
- 文件: `snake_case.py`
- 类: `PascalCase`
- 函数/变量: `snake_case`
- 常量: `UPPER_SNAKE_CASE`

**TypeScript**:
- 文件: `PascalCase.tsx` (组件) / `camelCase.ts` (工具)
- 组件: `PascalCase`
- 函数/变量: `camelCase`
- 类型/接口: `PascalCase`
- 常量: `UPPER_SNAKE_CASE`

### 注释规范

**Python (Google Style)**:

```python
def calculate_batch_size(total: int, concurrency: int) -> int:
    """计算批次大小。

    Args:
        total: 总实例数
        concurrency: 并发数

    Returns:
        每个批次的实例数

    Raises:
        ValueError: 当参数无效时
    """
    if concurrency <= 0:
        raise ValueError("concurrency must be positive")
    return math.ceil(total / concurrency)
```

**TypeScript (JSDoc)**:

```typescript
/**
 * 获取任务列表
 * @param params - 查询参数
 * @returns 分页的任务列表
 */
async function fetchTasks(params: TaskQueryParams): Promise<PaginatedResponse<Task>> {
  // ...
}
```

---

## 测试

### 后端测试

**安装依赖**:

```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

**编写测试** (`tests/test_api.py`):

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_dataset():
    response = client.post(
        "/api/v1/datasets/",
        json={"name": "Test Dataset", "description": "Test"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Dataset"

def test_list_datasets():
    response = client.get("/api/v1/datasets/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
```

**运行测试**:

```bash
# 运行所有测试
pytest

# 生成覆盖率报告
pytest --cov=app --cov-report=html

# 查看报告
open htmlcov/index.html
```

### 前端测试

**安装依赖**:

```bash
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom
```

**编写测试** (`src/pages/Dashboard/index.test.tsx`):

```typescript
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import Dashboard from './index'

describe('Dashboard', () => {
  it('renders dashboard title', () => {
    render(<Dashboard />)
    expect(screen.getByText('任务列表')).toBeInTheDocument()
  })
})
```

**运行测试**:

```bash
npm run test
```

---

## 常见问题

### Q1: 启动 Backend 时报 "Cannot connect to database"

**解决方案**:

```bash
# 检查 Docker 容器状态
docker-compose ps

# 查看数据库日志
docker-compose logs postgres

# 重启数据库
docker-compose restart postgres
```

### Q2: Worker 无法执行任务

**解决方案**:

```bash
# 检查 Redis 连接
redis-cli ping

# 查看队列状态
rq info --url redis://localhost:6379/0

# 检查 Docker 权限
docker ps
```

### Q3: 前端无法访问 API (CORS 错误)

**解决方案**:

Backend 已配置 CORS，检查 `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Q4: 如何调试 Worker 任务？

**解决方案**:

```python
# 在任务函数中添加日志
import logging
logger = logging.getLogger(__name__)

def my_task():
    logger.info("Task started")
    # ...
    logger.error("Task failed", exc_info=True)
```

查看日志:

```bash
tail -f backend/data/logs/worker.log
```

### Q5: TypeScript 路径别名不生效

**解决方案**:

确保 `tsconfig.json` 和 `vite.config.ts` 都配置了:

```json
// tsconfig.json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

```typescript
// vite.config.ts
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

### Q6: 如何增加 Worker 并发数？

**解决方案**:

启动多个 Worker 进程:

```bash
# 终端 1
rq worker --url redis://localhost:6379/0 ducc-tasks

# 终端 2
rq worker --url redis://localhost:6379/0 ducc-tasks

# 终端 3
rq worker --url redis://localhost:6379/0 ducc-tasks
```

或使用 Supervisor 配置:

```ini
[program:ducc-worker]
command=rq worker --url redis://localhost:6379/0 ducc-tasks
numprocs=4
process_name=%(program_name)s_%(process_num)02d
```

---

## 相关文档

- [部署文档](DEPLOYMENT.md)
- [前端文档](FRONTEND.md)
- [安装文档](INSTALLATION.md)
- [架构变更说明](ARCHITECTURE_CHANGE.md)
- [Conda 环境配置](CONDA_SETUP.md)

---

**Happy Coding! 🚀**
