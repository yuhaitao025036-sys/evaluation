# DUCC 任务评估系统

一个完整的 Web 化任务管理和评估系统，专为 DUCC (代码评估Agent) 设计。

## ✨ 核心特性

- 🎯 **脚本解耦**: 评估逻辑独立于系统，支持任意 Python 脚本
- 📊 **灵活数据集**: JSONB 存储支持任意字段结构的数据集
- 🤖 **模型选择**: 支持 6 种主流 AI 模型（GPT-4, Claude, Gemini 等）
- 🏷️ **标签系统**: 支持同一实例多次运行对比（baseline vs experiments）
- ⚡ **并发执行**: 自动分批并发处理，支持 10+ Workers
- 📈 **结果对比**: 跨模型、跨标签、实例级详细对比
- 🔒 **安全验证**: 白名单参数验证，防止命令注入
- 💓 **实时监控**: WebSocket 心跳机制，任务进度实时推送

## 🏗️ 系统架构

采用**混合部署架构**，避免 Docker in Docker 的复杂性：

```
宿主机
├── PostgreSQL (Docker)          ← 数据存储
├── Redis (Docker)                ← 任务队列
├── Backend API (宿主机进程)     ← FastAPI 服务
├── RQ Worker (宿主机进程)        ← 任务执行
└── 评估任务 (Docker by Worker)  ← Worker 调用 Docker
```

**优势：**
- ✅ 避免 Docker in Docker 配置复杂性
- ✅ Worker 直接访问宿主机 Docker daemon
- ✅ 简化文件路径和网络配置
- ✅ 更好的性能和调试体验

## 🏗️ 技术栈

**后端 (3,200+ 行代码)**:
- FastAPI (Python 3.8+) - REST API 框架
- PostgreSQL 15+ - JSONB 存储
- Redis 7 + RQ - 任务队列
- WebSocket - 实时通信
- SQLAlchemy - ORM
- Pydantic - 数据验证

**API 完整实现**:
- 28 个 REST API 端点
- 6 个功能模块（Models, Datasets, Scripts, Task Groups, Task Instances, Comparisons）
- 完整的 CRUD 操作
- 实时进度监控

**前端** (待开发):
- React 18 + TypeScript
- Vite - 构建工具
- Ant Design - UI 组件库
- Diff 可视化组件

## 📁 项目结构

```
evaluation/
├── backend/              # 后端服务
│   ├── app/
│   │   ├── api/         # REST API 路由
│   │   ├── core/        # 核心模块（验证器等）
│   │   ├── models/      # 数据库模型
│   │   ├── schemas/     # Pydantic 数据模型
│   │   ├── services/    # 业务逻辑
│   │   ├── websocket/   # WebSocket 管理
│   │   ├── workers/     # RQ Worker
│   │   └── main.py      # 应用入口
│   ├── requirements.txt
│   ├── schema.sql       # 数据库 schema
│   └── Dockerfile
│
├── frontend/            # 前端应用（开发中）
│
├── data/                # 数据目录
│   ├── datasets/        # 数据集文件 (.parquet, .csv, .json)
│   ├── scripts/         # 评估脚本 (.py)
│   └── outputs/         # 任务输出
│
├── docs/                # 文档
│   ├── design/          # 系统设计文档（开发用）
│   └── user-guide/      # 使用文档（用户用）
│
├── .agents/rules/       # 接口规范（添加脚本/数据集必读）
│
└── docker-compose.yml   # Docker Compose 配置
```

## 🔒 安全配置

⚠️ **首次使用必读**：项目包含敏感配置文件，请按以下步骤配置：

### 首次配置步骤

1. **复制配置文件模板**
   ```bash
   # 复制 Docker Compose 配置
   cp docker-compose.yml.example docker-compose.yml
   
   # 复制后端配置
   cp backend/app/config.py.example backend/app/config.py
   ```

2. **生成安全密码**
   ```bash
   # 使用 openssl 生成强密码（推荐）
   openssl rand -base64 32
   ```

3. **更新配置文件**
   
   在以下文件中将 `YOUR_SECURE_PASSWORD_HERE` 替换为生成的密码：
   - `docker-compose.yml` (第 39 行：`POSTGRES_PASSWORD`)
   - `backend/app/config.py` (第 17 行：`DATABASE_URL`)

4. **设置文件权限**
   ```bash
   chmod 600 docker-compose.yml
   chmod 600 backend/app/config.py
   ```

### 安全说明

- ✅ **`.gitignore` 保护**：包含真实密码的文件已被 `.gitignore` 忽略，不会提交到 Git
- ✅ **示例文件**：`.example` 后缀的文件使用占位符，可以安全提交
- ✅ **密码强度**：建议使用 24 位以上随机字符
- ⚠️ **不要在文档中记录真实密码**

### Git 安全检查

提交前务必验证：

```bash
# 检查哪些文件会被忽略
git status --ignored

# 验证敏感文件已被忽略
git check-ignore docker-compose.yml
git check-ignore backend/app/config.py

# 查看即将提交的文件
git status
```

**预期结果**：包含真实密码的文件不应出现在待提交列表中。

更多详情请参考：[数据库密码配置说明](docs/DATABASE_PASSWORD.md)

---

## 🚀 快速开始

### 方式 1: 一键安装（推荐）

```bash
# 1. 进入项目目录
cd /Users/yuhaitao01/dev/baidu/explore/test/evaluation

# 2. 运行快速启动脚本
./quickstart.sh
```

脚本会自动：
- ✅ 检查系统依赖（Docker, Python, pip）
- ✅ 启动数据库服务（PostgreSQL, Redis）
- ✅ 安装 Python 依赖
- ✅ 初始化数据库表
- ✅ 创建数据目录

### 方式 2: 手动安装

**第一步：启动数据库服务**

```bash
# 启动 PostgreSQL 和 Redis（Docker 容器）
docker-compose up -d

# 验证服务状态
docker-compose ps
```

**第二步：安装 Backend 依赖**

```bash
cd backend

# 运行安装脚本
./install.sh

# 或手动安装
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**第三步：初始化数据库**

```bash
cd backend
source venv/bin/activate
python init_db.py
```

**第四步：准备数据**

```bash
# 复制评估脚本
cp /path/to/test_tmux_cc_experience.py data/scripts/

# 复制数据集
cp /path/to/swe_bench_pro.parquet data/datasets/
```

### 启动服务

**终端 1 - Backend API:**
```bash
cd backend
./start_backend.sh

# 访问 API 文档: http://localhost:8000/docs
```

**终端 2 - Worker:**
```bash
cd backend
./start_worker.sh
```

### 使用 tmux 管理多个服务

```bash
# 创建会话
tmux new -s ducc

# 窗口 0: Backend
cd backend && ./start_backend.sh

# 新窗口 (Ctrl+b c)
cd backend && ./start_worker.sh

# 切换窗口: Ctrl+b 0/1
# 分离会话: Ctrl+b d
# 重新连接: tmux attach -t ducc
```

## 📖 文档导航

**完整文档中心**: [docs/README.md](docs/README.md) 📚

---

### 📚 接口规范（添加脚本/数据集必读）

**位置**: [`.agents/rules/`](.agents/rules/)

这些是**强制规范**，所有评估脚本和数据集必须遵循：

- **[脚本接口规范 v2.0](.agents/rules/script-interface.md)** ⚡️ - 脚本必须支持的参数和输出
  - 必需参数：`--instance-id`, `--output-dir`, `--model`, `--tag`
  - 单任务执行模式（系统负责调度）
  - [v2.0 变更说明](docs/design/SCRIPT_INTERFACE_V2_CHANGELOG.md)
- **[数据集格式规范](.agents/rules/dataset-format.md)** - 数据集文件格式要求
- **[输出结构规范](.agents/rules/output-structure.md)** - 脚本输出目录结构标准
- **[对比功能要求](.agents/rules/comparison-requirements.md)** - 启用对比功能的额外要求

📖 完整说明：[.agents/rules/README.md](.agents/rules/README.md)

---

### 🏗️ 设计文档（开发系统功能）

**位置**: [`docs/design/`](docs/design/)

这些是**架构设计**，供开发系统功能时参考：

- **[简化数据模型](docs/design/simplified-data-model.md)** ⭐️⭐️ - 三层数据架构（数据→批次→结果）
- **[任务调度与并发控制](docs/design/task-scheduling-and-concurrency.md)** ⭐️⭐️ - 系统级任务调度机制
- **[批次管理机制](docs/design/batch-management.md)** - 批次创建、追加和统计
- **[后端实现总结](docs/design/BACKEND_SUMMARY.md)** - 技术架构和功能清单
- **[开发指南](docs/design/DEVELOPMENT.md)** - 开发流程和规范

📖 完整说明：[docs/design/README.md](docs/design/README.md)

---

### 📘 使用文档（用户操作指南）

**位置**: [`docs/user-guide/`](docs/user-guide/)

这些是**使用指南**，面向系统使用者：

- **[安装指南](docs/user-guide/INSTALLATION.md)** - 详细的安装步骤和系统配置
- **[API 测试指南](docs/user-guide/API_TESTING.md)** - 完整的 API 使用示例和工作流
- **[部署文档](docs/user-guide/DEPLOYMENT.md)** - 生产环境部署说明
- **[备份设置](docs/user-guide/BACKUP_CRON_SETUP.md)** - 数据库备份配置

📖 完整说明：[docs/user-guide/README.md](docs/user-guide/README.md)

---

### 🔧 环境配置

**位置**: [`docs/setup/`](docs/setup/)

- **[数据库密码配置](docs/setup/DATABASE_PASSWORD.md)** - 密码安全配置
- **[Conda 环境配置](docs/setup/CONDA_SETUP.md)** - Conda 环境管理

📖 完整说明：[docs/setup/README.md](docs/setup/README.md)

---

### 🔧 示例代码

- **[示例脚本模板](data/scripts/example_script.py)** - 完整的 v2.0 评估脚本模板
- **[SWE-Bench 适配器](data/scripts/ducc_swebench_adapter.py)** - 现有脚本适配示例

## 🔍 快速验证

```bash
# 1. 健康检查
curl http://localhost:8000/health

# 2. 扫描数据集
curl -X POST http://localhost:8000/api/v1/datasets/scan

# 3. 扫描脚本
curl -X POST http://localhost:8000/api/v1/scripts/scan

# 4. 获取模型列表
curl http://localhost:8000/api/v1/models
```

访问 **Swagger UI**: http://localhost:8000/docs

## 💡 使用示例

### 准备阶段

#### 1. 编写评估脚本

参考 [脚本接口规范 v2.0](.agents/rules/script-interface.md) 和 [示例脚本](data/scripts/example_script.py) 编写你的评估脚本：

```bash
# 复制示例脚本作为模板
cp data/scripts/example_script.py data/scripts/my_evaluation.py

# 或者适配现有脚本
cp data/scripts/ducc_swebench_adapter.py data/scripts/my_adapter.py
```

**脚本必须遵守的规则** ([详见规范](.agents/rules/script-interface.md))：
- ✅ 支持必需参数：`--instance-id`, `--output-dir`, `--model`, `--tag`
- ✅ 只处理单个实例（不循环）
- ✅ 输出 `task_summary.json` 到 `<output-dir>/`
- 📝 推荐输出：`extracted_patch.diff`, `execution_trace.jsonl`
- 🔄 迁移指南：[v1.0 → v2.0 变更说明](docs/design/SCRIPT_INTERFACE_V2_CHANGELOG.md)

#### 2. 准备数据集

参考 [数据集格式规范](.agents/rules/dataset-format.md) 准备数据集：

```bash
# 复制数据集到 datasets 目录
cp my_dataset.parquet data/datasets/
```

**数据集必须遵守的规则** ([详见规范](.agents/rules/dataset-format.md))：
- ✅ 必需字段：`instance_id`
- 📝 推荐字段：`patch`, `problem_statement`, `repo`, `base_commit`

### 运行任务

#### 3. 创建任务组

```bash
curl -X POST http://localhost:8000/api/v1/task-groups \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python Baseline - GPT-4",
    "batch_name": "baseline",
    "dataset_id": 1,
    "script_id": 1,
    "model": "gpt-4-turbo",
    "tag": "baseline",
    "concurrency": 10,
    "start_index": 0,
    "end_index": 100,
    "filter_conditions": {
      "repo_language": "python"
    }
  }'
```

**批次说明**：
- `batch_name`: 批次名称，用于聚合统计（如 baseline, experiment_1）
- 同一批次的多次运行会被聚合在一起计算正确率
- 详见：[批次管理机制](.agents/rules/batch-management.md)

#### 3.2 追加数据到现有批次

```bash
# 追加更多数据到 baseline 批次
curl -X POST http://localhost:8000/api/v1/task-groups \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python Baseline - GPT-4 (Run 2)",
    "batch_name": "baseline",
    "append_to_batch": true,
    "dataset_id": 1,
    "script_id": 1,
    "model": "gpt-4-turbo",
    "tag": "baseline",
    "concurrency": 10,
    "start_index": 100,
    "end_index": 200
  }'
```

**注意**：
- ✅ 追加时 `model` 和 `tag` 必须与批次一致
- ✅ 支持动态追加，实时更新批次统计
- 📊 批次会自动聚合所有追加的数据计算正确率

### 启动任务

#### 4. 启动任务组

```bash
curl -X POST http://localhost:8000/api/v1/task-groups/1/start
```

#### 5. 查看进度

```bash
curl http://localhost:8000/api/v1/task-groups/1/progress
```

#### 6. 对比结果

对比不同模型或配置的结果，详见 [对比功能要求](.agents/rules/comparison-requirements.md)：

```bash
# 跨模型对比
curl -X POST http://localhost:8000/api/v1/comparisons/compare-by-models \
  -H "Content-Type: application/json" \
  -d '{
    "model_ids": ["gpt-4-turbo", "claude-3.5-sonnet"],
    "tag": "baseline",
    "dataset_id": 1
  }'

# 跨标签对比（同一模型的不同配置）
curl -X POST http://localhost:8000/api/v1/comparisons/compare-by-tags \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4-turbo",
    "tags": ["baseline", "experiment_new_prompt"],
    "dataset_id": 1
  }'
```

**支持的对比维度**：
- 🔄 跨模型对比（GPT-4 vs Claude）
- 🏷️ 跨标签对比（baseline vs experiment）
- 📊 三向对比（Ground Truth vs 生成 vs 原始代码）
- 📈 执行轨迹对比（时间、操作序列、资源消耗）

详见：[对比功能要求](.agents/rules/comparison-requirements.md)

完整工作流请参考 [API 测试指南](docs/API_TESTING.md)。

## 📊 数据库设计

### 核心表

- **datasets**: 数据集元信息
- **dataset_instances**: 实例数据（JSONB 灵活存储）
- **scripts**: 评估脚本
- **task_groups**: 任务组（批量管理）
- **tasks**: 任务
- **task_instances**: 任务实例执行结果
- **comparisons**: 对比配置

### 关键特性

1. **JSONB 灵活存储**: 支持不同数据集的不同字段结构
2. **标签系统**: 同一 instance 可多次运行并对比
3. **任务组管理**: 自动分批，统一管理
4. **完整索引**: B-tree + GIN 索引优化查询性能

## 🔧 核心模块

### 1. 脚本参数验证器

```python
from app.core.script_validator import validator

# 验证用户输入
result = validator.validate("--timeout 1800 --use-tmux")
if not result['valid']:
    print(result['errors'])

# 构建安全命令
cmd = validator.build_safe_command(
    script_path='/path/to/script.py',
    base_args={'dataset-path': 'data.parquet', 'output-dir': 'output/'},
    user_args='--timeout 1800'
)
# cmd = ['python', '/path/to/script.py', '--dataset-path', 'data.parquet', ...]
subprocess.run(cmd, shell=False)  # 安全执行
```

### 2. WebSocket 连接管理

```python
from app.websocket.manager import manager

# 订阅任务更新
await manager.subscribe_task(connection_id, task_id)

# 广播任务更新
await manager.broadcast_task_update(task_id, {
    'type': 'task_update',
    'data': {'status': 'running', 'progress': 50}
})
```

### 3. 任务执行流程

```
用户创建任务 → TaskService → RQ 队列 → Worker 执行脚本 → 结果收集 → 数据库更新 → WebSocket 推送
```

## 📖 API 文档

启动服务后访问: http://localhost:8000/docs

### 核心端点

```
# 数据集管理
GET    /api/v1/datasets          # 列出所有数据集
POST   /api/v1/datasets/scan     # 扫描数据集文件夹
GET    /api/v1/datasets/{id}     # 获取数据集详情

# 脚本管理
GET    /api/v1/scripts           # 列出所有脚本
POST   /api/v1/scripts/scan      # 扫描脚本文件夹

# 任务组管理
POST   /api/v1/task-groups       # 创建任务组（智能分批）
GET    /api/v1/task-groups/{id}  # 获取任务组详情
POST   /api/v1/task-groups/{id}/start   # 启动任务组
POST   /api/v1/task-groups/{id}/pause   # 暂停任务组

# 任务管理
POST   /api/v1/tasks             # 创建单个任务
GET    /api/v1/tasks/{id}        # 获取任务详情
GET    /api/v1/tasks/{id}/instances  # 获取任务实例列表

# WebSocket
WS     /ws/{connection_id}       # 实时任务状态
```

## 🎯 使用流程

### 1. 准备数据

```bash
# 将数据集放到 datasets 目录
cp my_dataset.parquet data/datasets/

# 将评估脚本放到 scripts 目录
cp my_script.py data/scripts/
```

### 2. 扫描资源

```bash
# 扫描数据集
curl -X POST http://localhost:8000/api/v1/datasets/scan

# 扫描脚本
curl -X POST http://localhost:8000/api/v1/scripts/scan
```

### 3. 创建任务组

```bash
curl -X POST http://localhost:8000/api/v1/task-groups \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SWE-bench Baseline Run",
    "dataset_id": 1,
    "script_id": 1,
    "tag": "baseline",
    "batch_size": 50,
    "start_index": 0,
    "end_index": 731
  }'
```

系统自动创建 15 个批次任务（731 / 50 = 15批）

### 4. 启动任务组

```bash
curl -X POST http://localhost:8000/api/v1/task-groups/1/start
```

### 5. 实时监控

使用前端 UI 或 WebSocket 连接监控进度。

### 6. 查看结果

```bash
# 获取任务组结果
curl http://localhost:8000/api/v1/task-groups/1/results

# 对比不同标签
curl http://localhost:8000/api/v1/comparisons \
  -d '{"tags": ["baseline", "experiment_1"]}'
```

## 🔒 安全性

### 参数验证

系统使用白名单验证用户输入的脚本参数，防止：
- ✅ 命令注入
- ✅ 路径遍历
- ✅ 资源耗尽

### 安全执行

脚本执行使用 `subprocess.run(cmd_list, shell=False)`，不使用 shell 解析。

## 🧪 测试

```bash
cd backend

# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_validator.py

# 测试覆盖率
pytest --cov=app tests/
```

## 📝 开发指南

### 添加新的脚本参数

编辑 `backend/app/core/script_validator.py`:

```python
ALLOWED_ARGS = {
    ...
    '--your-new-arg': ('string', True, lambda v: len(v) > 0),
}
```

### 添加新的 API 端点

1. 在 `backend/app/api/v1/` 创建新路由文件
2. 在 `backend/app/main.py` 中引入路由
3. 使用 Pydantic 定义请求/响应模型

### 扩展数据库模型

1. 修改 `backend/app/models/__init__.py`
2. 生成迁移: `alembic revision --autogenerate -m "description"`
3. 应用迁移: `alembic upgrade head`

## 🐛 故障排查

详见 [部署文档 - 故障排查](./docs/DEPLOYMENT.md#故障排查)

常见问题:
- 数据库连接失败 → 检查 PostgreSQL 是否运行
- Redis 连接失败 → 检查 Redis 是否运行
- 端口被占用 → 使用 `lsof -i :8000` 检查
- 权限错误 → 检查 data 目录权限

## 📊 性能优化

- **JSONB 查询**: 使用 GIN 索引，复杂查询 50-200ms
- **instance_id 查询**: 使用 B-tree 索引，< 1ms
- **延迟加载**: 数据集按需导入，启动快速
- **批量处理**: 智能分批，避免内存溢出

## 🗺️ 路线图

### Phase 1: MVP (已完成)
- [x] 数据库设计
- [x] 后端核心模块
- [x] 脚本参数验证
- [x] WebSocket 心跳机制
- [x] Docker 部署

### Phase 2: 核心功能 (进行中)
- [ ] 完整 REST API
- [ ] 数据集扫描与导入
- [ ] 任务创建与执行
- [ ] RQ Worker 实现
- [ ] 结果收集

### Phase 3: 高级功能
- [ ] 前端 UI
- [ ] 标签对比功能
- [ ] Diff 可视化
- [ ] 性能优化
- [ ] 完整测试覆盖

### Phase 4: 扩展
- [ ] 用户认证
- [ ] 权限管理
- [ ] 日志监控
- [ ] 数据备份

## 🤝 贡献

欢迎贡献！请遵循以下步骤:

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目基于 MIT 许可证开源。

## 📞 联系方式

- **文档**: `/Users/yuhaitao01/dev/baidu/explore/test/evaluation/docs/`
- **设计文档**: `/Users/yuhaitao01/.comate/plans/DUCC_任务评估系统架构设计_*.plan.md`

---

**Built with ❤️ for DUCC Evaluation**
# evaluation
