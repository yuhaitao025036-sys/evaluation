# API 测试指南

本文档提供了系统 API 的测试示例和使用说明。

## 前置条件

确保系统已启动：
```bash
docker-compose up -d
```

或本地开发环境：
```bash
# 启动 Redis
redis-server

# 启动后端
cd backend
uvicorn app.main:app --reload --port 8000

# 启动 Worker
cd backend
python worker.py
```

## API 端点概览

### 基础信息

- 基础 URL: `http://localhost:8000/api/v1`
- 所有请求和响应均为 JSON 格式

### 端点分类

1. **Models** - 模型管理 (`/models`)
2. **Datasets** - 数据集管理 (`/datasets`)
3. **Scripts** - 脚本管理 (`/scripts`)
4. **Task Groups** - 任务组管理 (`/task-groups`)
5. **Task Instances** - 任务实例管理 (`/task-instances`)
6. **Comparisons** - 结果对比 (`/comparisons`)

## 完整工作流测试

### 1. 获取可用模型

```bash
curl http://localhost:8000/api/v1/models
```

响应示例：
```json
[
  {
    "id": "gpt-4-turbo",
    "name": "GPT-4 Turbo",
    "provider": "openai",
    "description": "Most capable GPT-4 model"
  }
]
```

### 2. 扫描数据集

```bash
curl -X POST http://localhost:8000/api/v1/datasets/scan
```

响应示例：
```json
{
  "message": "Scan completed: 1 new datasets registered",
  "registered_count": 1,
  "datasets": [
    {
      "id": 1,
      "name": "swe-bench-pro",
      "file_name": "swe_bench_pro.parquet"
    }
  ]
}
```

### 3. 查看数据集列表

```bash
curl http://localhost:8000/api/v1/datasets
```

### 4. 导入数据集实例

```bash
curl -X POST http://localhost:8000/api/v1/datasets/1/import
```

这会将数据集中的所有实例导入到数据库。

### 5. 扫描脚本

```bash
curl -X POST http://localhost:8000/api/v1/scripts/scan
```

响应示例：
```json
{
  "message": "Scan completed: 1 new, 0 updated",
  "registered_count": 1,
  "scripts": [
    {
      "id": 1,
      "file_name": "test_tmux_cc_experience.py",
      "status": "registered"
    }
  ]
}
```

### 6. 创建任务组（核心功能）

创建一个任务组，指定模型、并发数、过滤条件：

```bash
curl -X POST http://localhost:8000/api/v1/task-groups \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SWE-bench Python Baseline - GPT-4",
    "description": "Baseline run with GPT-4 on Python repositories",
    "dataset_id": 1,
    "script_id": 1,
    "model": "gpt-4-turbo",
    "tag": "baseline",
    "concurrency": 10,
    "filter_conditions": {
      "repo_language": "python"
    },
    "script_args": "--timeout 1800"
  }'
```

响应示例：
```json
{
  "id": 1,
  "name": "SWE-bench Python Baseline - GPT-4",
  "status": "created",
  "total_instances": 450,
  "concurrency": 10,
  "model": "gpt-4-turbo",
  "tag": "baseline",
  "total_batches": 10
}
```

### 7. 启动任务组

```bash
curl -X POST http://localhost:8000/api/v1/task-groups/1/start
```

响应示例：
```json
{
  "message": "Task group 1 started, 450 instances enqueued",
  "status": "queued",
  "enqueued_count": 450
}
```

### 8. 查看任务组进度

```bash
curl http://localhost:8000/api/v1/task-groups/1/progress
```

响应示例：
```json
{
  "task_group_id": 1,
  "status": "running",
  "total_instances": 450,
  "completed_instances": 120,
  "failed_instances": 5,
  "pending_instances": 325,
  "progress_percentage": 27.78,
  "success_rate": 96.0,
  "avg_duration_seconds": 245.3
}
```

### 9. 查看任务实例列表

```bash
# 查看所有实例
curl http://localhost:8000/api/v1/task-instances

# 按状态过滤
curl "http://localhost:8000/api/v1/task-instances?status=completed&limit=20"

# 按模型和标签过滤
curl "http://localhost:8000/api/v1/task-instances?model=gpt-4-turbo&tag=baseline"
```

### 10. 查看单个实例详情

```bash
curl http://localhost:8000/api/v1/task-instances/123
```

响应包含完整的测试结果、生成的补丁等。

### 11. 对比不同模型的结果

创建另一个使用不同模型的任务组：

```bash
curl -X POST http://localhost:8000/api/v1/task-groups \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SWE-bench Python Baseline - Claude",
    "dataset_id": 1,
    "script_id": 1,
    "model": "claude-3.5-sonnet",
    "tag": "baseline",
    "concurrency": 10,
    "filter_conditions": {
      "repo_language": "python"
    }
  }'
```

启动并等待完成后，对比两个模型：

```bash
curl -X POST http://localhost:8000/api/v1/comparisons/compare-by-models \
  -H "Content-Type: application/json" \
  -d '{
    "model_ids": ["gpt-4-turbo", "claude-3.5-sonnet"],
    "tag": "baseline",
    "dataset_id": 1
  }'
```

响应示例：
```json
{
  "tag": "baseline",
  "model_ids": ["gpt-4-turbo", "claude-3.5-sonnet"],
  "comparison_stats": {
    "gpt-4-turbo": {
      "total_instances": 450,
      "completed": 445,
      "failed": 5,
      "success_count": 320,
      "success_rate": 0.711,
      "avg_duration_seconds": 245.3
    },
    "claude-3.5-sonnet": {
      "total_instances": 450,
      "completed": 448,
      "failed": 2,
      "success_count": 335,
      "success_rate": 0.744,
      "avg_duration_seconds": 198.7
    }
  },
  "instance_comparisons": [
    {
      "instance_id": "django__django-12345",
      "results_by_model": {
        "gpt-4-turbo": {
          "status": "completed",
          "validation_success": true,
          "duration_seconds": 234.5
        },
        "claude-3.5-sonnet": {
          "status": "completed",
          "validation_success": true,
          "duration_seconds": 189.2
        }
      }
    }
  ]
}
```

### 12. 对比不同标签（实验配置）

```bash
curl -X POST http://localhost:8000/api/v1/comparisons/compare-by-tags \
  -H "Content-Type: application/json" \
  -d '{
    "tags": ["baseline", "experiment-1"],
    "model_id": "gpt-4-turbo",
    "dataset_id": 1
  }'
```

### 13. 对比单个实例的多次运行

```bash
curl -X POST http://localhost:8000/api/v1/comparisons/compare-instance \
  -H "Content-Type: application/json" \
  -d '{
    "instance_id": "django__django-12345",
    "tags": ["baseline", "experiment-1"],
    "model_ids": ["gpt-4-turbo", "claude-3.5-sonnet"]
  }'
```

响应包含该实例在不同配置下的所有运行结果，包括生成的补丁、测试结果等详细信息。

### 14. 获取可用的标签和模型

```bash
# 获取所有使用过的标签
curl http://localhost:8000/api/v1/comparisons/tags

# 获取特定数据集的标签
curl "http://localhost:8000/api/v1/comparisons/tags?dataset_id=1"

# 获取使用过的模型
curl http://localhost:8000/api/v1/comparisons/models-in-use

# 获取特定标签下的模型
curl "http://localhost:8000/api/v1/comparisons/models-in-use?tag=baseline"
```

### 15. 任务实例统计

```bash
# 获取总体统计
curl http://localhost:8000/api/v1/task-instances/stats/summary

# 按标签统计
curl "http://localhost:8000/api/v1/task-instances/stats/summary?tag=baseline"

# 按模型统计
curl "http://localhost:8000/api/v1/task-instances/stats/summary?model=gpt-4-turbo"

# 组合过滤
curl "http://localhost:8000/api/v1/task-instances/stats/summary?tag=baseline&model=gpt-4-turbo&dataset_id=1"
```

## 过滤条件详解

创建任务组时，`filter_conditions` 支持以下过滤方式：

### 1. 语言过滤

```json
{
  "filter_conditions": {
    "repo_language": "python"
  }
}
```

### 2. Instance ID 模式匹配

```json
{
  "filter_conditions": {
    "instance_id_pattern": "django*"
  }
}
```

支持通配符 `*`，例如：
- `"django*"` - 匹配以 django 开头的实例
- `"*auth*"` - 匹配包含 auth 的实例

### 3. 索引范围

```json
{
  "filter_conditions": {
    "index_range": {
      "start": 0,
      "end": 100
    }
  }
}
```

### 4. JSONB 字段过滤

```json
{
  "filter_conditions": {
    "jsonb_filters": {
      "repo": "django/django",
      "base_commit": "abc123"
    }
  }
}
```

### 5. 组合过滤

```json
{
  "filter_conditions": {
    "repo_language": "python",
    "instance_id_pattern": "django*",
    "index_range": {
      "start": 0,
      "end": 50
    }
  }
}
```

## WebSocket 实时更新

连接 WebSocket 以接收任务实时更新：

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/my-connection-id');

ws.onopen = () => {
  // 订阅任务更新
  ws.send(JSON.stringify({
    type: 'subscribe',
    task_id: 1
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Task update:', data);
};

// 发送心跳
setInterval(() => {
  ws.send(JSON.stringify({ type: 'ping' }));
}, 30000);
```

## 错误处理

所有 API 错误都返回标准格式：

```json
{
  "detail": "Error message here"
}
```

常见 HTTP 状态码：
- `200` - 成功
- `404` - 资源不存在
- `400` - 请求参数错误
- `500` - 服务器内部错误

## API 文档

启动系统后，访问自动生成的 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
