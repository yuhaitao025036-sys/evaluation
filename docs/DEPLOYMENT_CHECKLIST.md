# DUCC 评估系统部署前检查清单

**检查日期**: 2026-05-14  
**系统版本**: v2.0 (简化数据模型 + 系统级调度)

---

## ✅ 数据库层检查

### Schema 完整性
- ✅ datasets 表（数据集）
- ✅ dataset_instances 表（数据集实例，JSONB）
- ✅ scripts 表（评估脚本）
- ✅ batches 表（批次 - 核心）
- ✅ batch_results 表（任务结果 - 核心）
- ✅ comparisons 表（对比配置）
- ✅ schema_version 表（版本记录）

### 索引优化
- ✅ 主键索引（自动）
- ✅ 外键索引
- ✅ 业务查询索引（status, model, tag）
- ✅ JSONB GIN 索引（data字段）
- ✅ 组合索引（batch_id + status - 调度器优化）

### 触发器
- ✅ `update_batch_stats()` - 自动更新批次统计
- ✅ `trigger_update_batch_stats` - batch_results 状态变更时触发

### 约束
- ✅ `UNIQUE(dataset_id, instance_id)` - 数据集实例唯一
- ✅ `UNIQUE(batch_id, instance_id)` - 批次内实例唯一（核心数据隔离）
- ✅ `UNIQUE(dataset_id, model, tag)` - 批次组合唯一

---

## ✅ 后端层检查

### 1. Models (ORM)
**文件**: `backend/app/models.py`

- ✅ Dataset 模型
- ✅ DatasetInstance 模型
- ✅ Script 模型
- ✅ Batch 模型（核心）
- ✅ BatchResult 模型（核心）
- ✅ Comparison 模型
- ✅ 关系定义（relationship）
- ✅ 索引定义（Index）

### 2. Schemas (数据验证)
**文件**: `backend/app/schemas.py`

请求 Schemas:
- ✅ BatchCreate（创建批次）
- ✅ BatchUpdate（更新批次）
- ✅ BatchStartRequest（启动批次）
- ✅ BatchPauseRequest（暂停批次）
- ✅ BatchRetryRequest（重试任务）
- ✅ BatchAddTasksRequest（追加任务）

响应 Schemas:
- ✅ BatchResponse（批次信息）
- ✅ BatchStats（批次统计）
- ✅ BatchResultResponse（任务结果）
- ✅ DatasetResponse（数据集）
- ✅ ScriptResponse（脚本）
- ✅ MessageResponse（通用响应）
- ✅ ErrorResponse（错误响应）

### 3. Services (业务逻辑)

#### batch_service.py
- ✅ `create_batch()` - 创建批次并生成任务
- ✅ `add_tasks_to_batch()` - 追加任务
- ✅ `update_batch()` - 更新配置
- ✅ `get_batch()` - 获取批次
- ✅ `get_batch_by_name()` - 按名称获取
- ✅ `list_batches()` - 列出批次
- ✅ `delete_batch()` - 删除批次
- ✅ `get_batch_stats()` - 获取统计
- ✅ `get_batch_tasks()` - 获取任务列表
- ✅ `get_batch_task()` - 获取单个任务
- ✅ `_query_instances()` - 查询数据集实例（支持多种过滤）
- ✅ `_generate_output_dir()` - 生成输出目录

#### scheduler_service.py
- ✅ `start_batch()` - 启动批次
- ✅ `pause_batch()` - 暂停批次
- ✅ `resume_batch()` - 恢复批次
- ✅ `retry_failed_tasks()` - 重试失败任务
- ✅ `_schedule_pending_tasks()` - 调度任务到队列
- ✅ `_enqueue_task()` - 加入 RQ 队列
- ✅ `_cancel_queued_tasks()` - 取消队列任务
- ✅ `on_task_completed()` - 任务完成回调

### 4. Worker
**文件**: `backend/app/workers/task_worker.py`

- ✅ `execute_single_task(task_id)` - RQ Worker 入口
- ✅ 加载任务信息（task, batch, script, instance）
- ✅ 更新状态为 running
- ✅ 调用脚本（`--instance-id`, `--model`, `--tag`）
- ✅ 解析 task_summary.json
- ✅ 更新任务状态和结果
- ✅ 自动重试逻辑（retry_count < max_retries）
- ✅ 通知调度器继续调度

### 5. API Routes
**文件**: `backend/app/api/v1/batches.py`

核心端点:
- ✅ `POST /api/v1/batches` - 创建批次
- ✅ `GET /api/v1/batches/{id}` - 获取批次
- ✅ `GET /api/v1/batches` - 列出批次
- ✅ `PATCH /api/v1/batches/{id}` - 更新批次
- ✅ `DELETE /api/v1/batches/{id}` - 删除批次

操作端点:
- ✅ `POST /api/v1/batches/{id}/start` - 启动批次
- ✅ `POST /api/v1/batches/{id}/pause` - 暂停批次
- ✅ `POST /api/v1/batches/{id}/resume` - 恢复批次
- ✅ `POST /api/v1/batches/{id}/retry` - 重试失败任务
- ✅ `POST /api/v1/batches/{id}/tasks` - 追加任务

查询端点:
- ✅ `GET /api/v1/batches/{id}/stats` - 获取统计
- ✅ `GET /api/v1/batches/{id}/tasks` - 获取任务列表
- ✅ `GET /api/v1/batches/{id}/tasks/{iid}` - 获取单个任务

---

## ⚠️ 需要补充的部分

### 1. 缺少的 API 端点（需要保留）

#### datasets API
**文件**: `backend/app/api/v1/datasets.py` (应该已存在)
- ⚠️ `GET /api/v1/datasets` - 列出数据集
- ⚠️ `POST /api/v1/datasets/scan` - 扫描数据集目录
- ⚠️ `GET /api/v1/datasets/{id}` - 获取数据集详情
- ⚠️ `GET /api/v1/datasets/{id}/instances` - 获取数据集实例

#### scripts API
**文件**: `backend/app/api/v1/scripts.py` (应该已存在)
- ⚠️ `GET /api/v1/scripts` - 列出脚本
- ⚠️ `POST /api/v1/scripts/scan` - 扫描脚本目录
- ⚠️ `GET /api/v1/scripts/{id}` - 获取脚本详情

### 2. 主应用入口
**文件**: `backend/app/main.py`

需要检查:
- ⚠️ 是否引入了新的 batches 路由？
- ⚠️ 数据库连接配置是否正确？
- ⚠️ CORS 配置是否完整？

### 3. 数据库配置
**文件**: `backend/app/database.py`

需要检查:
- ⚠️ 数据库连接字符串
- ⚠️ SessionLocal 配置
- ⚠️ get_db() 依赖注入

### 4. 配置文件
**文件**: `backend/app/config.py`

需要检查:
- ⚠️ DATABASE_URL
- ⚠️ REDIS_HOST / REDIS_PORT
- ⚠️ DUCC_OUTPUT_BASE_DIR
- ⚠️ DUCC_DATASET_PATH

---

## 🔍 逻辑完整性检查

### 批次创建流程
```
用户请求 → BatchCreate schema 验证
         ↓
   BatchService.create_batch()
         ↓
   1. 检查批次是否存在（追加模式）
   2. 查询数据集实例（instance_ids / 范围 / 过滤）
   3. 创建 Batch 记录
   4. 为每个实例创建 BatchResult（status=pending）
   5. 检查去重（skip / overwrite）
         ↓
   返回：batch + 统计信息
```

✅ 逻辑完整

### 批次启动流程
```
POST /api/v1/batches/{id}/start
         ↓
   SchedulerService.start_batch()
         ↓
   1. 检查批次状态
   2. 更新批次状态为 running
   3. 调用 _schedule_pending_tasks()
         ↓
   _schedule_pending_tasks()
         ↓
   1. 计算可用槽位（max_concurrency - current_running）
   2. 查询 pending 任务（限制数量）
   3. 对每个任务调用 _enqueue_task()
         ↓
   _enqueue_task()
         ↓
   1. 加入 RQ 队列
   2. 更新任务状态为 queued
   3. 保存 job_id
```

✅ 逻辑完整

### 任务执行流程
```
RQ Worker 获取任务
         ↓
   execute_single_task(task_id)
         ↓
   1. 加载任务信息（task, batch, script, instance）
   2. 更新状态为 running
   3. 构建命令：python script.py --instance-id "xxx" --model "xxx" --tag "xxx"
   4. 执行脚本
   5. 解析 task_summary.json
   6. 更新任务状态（completed / failed）
   7. 检查重试（retry_count < max_retries）
   8. 调用 scheduler.on_task_completed()
         ↓
   on_task_completed()
         ↓
   1. 调用 _schedule_pending_tasks() 调度下一个任务
   2. 检查批次是否完成（pending=0 && running=0）
   3. 如果完成，更新批次状态为 completed
```

✅ 逻辑完整

### 并发控制
```
批次配置：max_concurrency = 10

调度时:
available_slots = max_concurrency - current_running
                = 10 - 0 = 10（首次调度）

查询 pending 任务：LIMIT available_slots
加入队列：10 个任务

触发器自动更新:
running_tasks = 10
current_running = 10

下次调度:
available_slots = 10 - 10 = 0（不调度）

任务完成后:
running_tasks = 9
current_running = 9
available_slots = 10 - 9 = 1（调度 1 个）
```

✅ 逻辑正确

---

## ❌ 发现的问题

### 问题 1: 触发器更新 current_running
触发器计算 `current_running` 使用 `COUNT(*)`:
```sql
current_running = (SELECT COUNT(*) FROM batch_results 
                   WHERE batch_id = NEW.batch_id AND status = 'running')
```

但这会导致：
- queued 任务不计入 current_running
- 实际 Worker 可能超过 max_concurrency

**建议修复**: `current_running` 应该包含 queued + running
```sql
current_running = (SELECT COUNT(*) FROM batch_results 
                   WHERE batch_id = NEW.batch_id 
                   AND status IN ('queued', 'running'))
```

### 问题 2: 批次唯一约束过于严格
```sql
CONSTRAINT uq_batch_dataset_model_tag UNIQUE(dataset_id, model, tag)
```

这意味着：
- 同一数据集 + 模型 + tag 只能有一个批次
- 无法创建多个 baseline 批次

**建议**: 移除此约束，改为 `batch_name` 唯一即可

### 问题 3: 缺少 dataset_id 字段传递
BatchCreate 需要从 instance 查询 dataset:
```python
# batch_service.py 需要加载 dataset
dataset_instance = db.query(DatasetInstance).filter(...).first()
# 但没有传递 dataset 到 Script
```

**影响**: 不影响功能，但脚本可能需要 dataset 信息

### 问题 4: 输出目录冲突
两个批次可能生成相同的输出目录：
```python
def _generate_output_dir(self, batch_name: str) -> str:
    safe_batch_name = batch_name.replace('/', '_').replace(':', '_')
    return os.path.join(base_dir, safe_batch_name)
```

**建议**: 加上批次 ID：
```python
return os.path.join(base_dir, f"{safe_batch_name}_{batch_id}")
```

---

## 🔧 需要立即修复

### 修复 1: 更新 SQL 触发器
### 修复 2: 移除批次唯一约束
### 修复 3: 输出目录加上 batch_id

要我帮你修复这些问题吗？

---

## ✅ 确认无误的部分

1. ✅ 数据模型设计正确（3层架构）
2. ✅ API 接口设计完整
3. ✅ 任务调度逻辑正确
4. ✅ Worker 执行流程正确
5. ✅ 状态机设计合理
6. ✅ 重试机制完整
7. ✅ 数据隔离机制正确（UNIQUE batch_id + instance_id）

---

## 📋 部署前清单

- [ ] 修复上述 4 个问题
- [ ] 检查 main.py 引入 batches 路由
- [ ] 检查 config.py 环境变量
- [ ] 创建 database.py（如果不存在）
- [ ] 确认 datasets 和 scripts API 存在
- [ ] 准备示例脚本（v2.0 接口）
- [ ] 测试完整流程

要我帮你逐个检查和修复吗？
