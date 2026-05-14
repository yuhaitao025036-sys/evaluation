# 简化的数据模型设计（去除执行层）

## 核心思想

基于用户反馈，简化数据模型：
- ❌ 去除 `executions` 表 - 不需要单独的执行层
- ✅ 只保留 `batches` 表 - 批次作为核心组织单位
- ✅ 任务结果直接关联到批次 - 简化关系
- ✅ 任务状态在批次内统一管理 - 便于查看

---

## 简化后的三层架构

```
┌─────────────────┐
│  1. 数据层      │  datasets + dataset_instances
│  (数据本身)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. 批次层      │  batches (核心组织单位)
│  (统计单位)     │
└────────┬────────┘
         │ 1:N
         ▼
┌─────────────────┐
│  3. 结果层      │  batch_results (每个数据的执行结果)
│  (任务结果)     │
└─────────────────┘
```

---

## 优化后的表结构

### 1. 数据层（保持不变）

```sql
-- 数据集
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    total_instances INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 数据实例
CREATE TABLE dataset_instances (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE CASCADE,
    instance_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(dataset_id, instance_id)
);
```

---

### 2. 批次层（核心）

```sql
-- 批次（核心组织单位）
CREATE TABLE batches (
    id SERIAL PRIMARY KEY,
    batch_name VARCHAR(200) UNIQUE NOT NULL,
    
    -- 批次配置
    dataset_id INTEGER REFERENCES datasets(id),
    model VARCHAR(100) NOT NULL,
    tag VARCHAR(100) NOT NULL,
    
    -- 执行配置（记录用什么脚本执行的）
    execution_config JSONB,  -- {"script": "...", "args": "..."}
    
    -- 批次状态
    status VARCHAR(50) DEFAULT 'created',  -- created, running, completed, paused
    
    -- 任务统计
    total_tasks INTEGER DEFAULT 0,
    pending_tasks INTEGER DEFAULT 0,      -- 排队中
    running_tasks INTEGER DEFAULT 0,      -- 运行中
    completed_tasks INTEGER DEFAULT 0,    -- 已完成
    failed_tasks INTEGER DEFAULT 0,       -- 失败
    
    -- 时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 输出目录
    output_dir VARCHAR(512)
);

CREATE INDEX idx_batches_status ON batches(status);
CREATE INDEX idx_batches_dataset ON batches(dataset_id);
CREATE INDEX idx_batches_model_tag ON batches(model, tag);
```

---

### 3. 结果层（任务结果）

```sql
-- 批次任务结果
CREATE TABLE batch_results (
    id SERIAL PRIMARY KEY,
    
    -- 关联
    batch_id INTEGER REFERENCES batches(id) ON DELETE CASCADE,
    dataset_instance_id INTEGER REFERENCES dataset_instances(id),
    instance_id VARCHAR(255) NOT NULL,
    
    -- 批次信息（冗余，便于查询）
    model VARCHAR(100) NOT NULL,
    tag VARCHAR(100) NOT NULL,
    
    -- 任务状态
    status VARCHAR(50) DEFAULT 'pending',  -- pending, running, completed, failed
    
    -- 执行结果
    validation_success BOOLEAN,
    tests_passed INTEGER DEFAULT 0,
    tests_failed INTEGER DEFAULT 0,
    tests_total INTEGER DEFAULT 0,
    
    -- 性能
    duration_seconds FLOAT,
    
    -- 结果详情
    result_summary JSONB,
    patch_path VARCHAR(512),
    
    -- 时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- 唯一约束：同一批次内同一 instance 只能有一个结果
    UNIQUE(batch_id, instance_id)
);

CREATE INDEX idx_batch_results_batch ON batch_results(batch_id);
CREATE INDEX idx_batch_results_instance ON batch_results(instance_id);
CREATE INDEX idx_batch_results_status ON batch_results(status);
CREATE INDEX idx_batch_results_model_tag ON batch_results(model, tag);
```

**关键设计**：
- ✅ `UNIQUE(batch_id, instance_id)` - 同一批次内同一数据只有一个结果
- ✅ `status` 包含 `pending` 状态 - 支持排队中的任务
- ✅ 直接关联到 `batch_id` - 简化关系

---

## 使用流程

### 场景 1: 新建批次 + 添加任务

```bash
POST /api/v1/batches
{
  "batch_name": "baseline",
  "dataset_id": 1,
  "model": "gpt-4-turbo",
  "tag": "baseline",
  
  # 选择要处理的数据
  "start_index": 0,
  "end_index": 100,
  
  # 执行配置
  "execution_config": {
    "script": "data/scripts/swebench_eval.py",
    "args": "--timeout 1800"
  }
}
```

**系统操作**：
```python
# 1. 创建批次
batch = Batch(
    batch_name="baseline",
    dataset_id=1,
    model="gpt-4-turbo",
    tag="baseline",
    status="created",
    total_tasks=100
)

# 2. 为每个数据实例创建任务记录（pending 状态）
instances = get_dataset_instances(dataset_id=1, start=0, end=100)
for instance in instances:
    BatchResult(
        batch_id=batch.id,
        instance_id=instance.instance_id,
        dataset_instance_id=instance.id,
        model=batch.model,
        tag=batch.tag,
        status="pending"  # 初始状态：排队中
    )

# 3. 更新批次统计
batch.pending_tasks = 100
```

**结果**：
```
batches:
└─ id=1, batch_name="baseline", total_tasks=100, pending_tasks=100

batch_results:
├─ id=1: batch_id=1, instance_id="django-11099", status="pending" ⏳
├─ id=2: batch_id=1, instance_id="django-11100", status="pending" ⏳
└─ ... (100 条，都是 pending)
```

---

### 场景 2: 启动批次（并行执行）

```bash
POST /api/v1/batches/1/start
{
  "concurrency": 10  # 并行度
}
```

**系统操作**：
```python
# 1. 更新批次状态
batch.status = "running"
batch.started_at = now()

# 2. 获取 pending 任务
pending_tasks = get_batch_results(batch_id=1, status="pending")

# 3. 分配到 RQ 队列（10 个并行 worker）
for task in pending_tasks[:10]:
    task.status = "running"
    task.started_at = now()
    batch.running_tasks += 1
    batch.pending_tasks -= 1
    
    # 提交到队列
    queue.enqueue(
        execute_task,
        batch_id=batch.id,
        task_id=task.id,
        instance_id=task.instance_id
    )
```

**实时状态**：
```
batches:
└─ id=1, status="running", total=100, pending=90, running=10

batch_results:
├─ id=1: status="running" 🔄
├─ id=2: status="running" 🔄
├─ ...  (10 个 running)
├─ id=11: status="pending" ⏳
└─ ... (90 个 pending)
```

---

### 场景 3: 追加数据到批次

```bash
POST /api/v1/batches/1/add-tasks
{
  "start_index": 100,
  "end_index": 200,
  "on_duplicate": "skip"  # 或 "overwrite"
}
```

**系统操作**：
```python
batch = get_batch(id=1)

# 验证配置一致性
if batch.model != request.model or batch.tag != request.tag:
    raise ValueError("Configuration mismatch")

# 获取要添加的数据
instances = get_dataset_instances(
    dataset_id=batch.dataset_id,
    start=100,
    end=200
)

# 检查重复
for instance in instances:
    existing = get_batch_result(
        batch_id=batch.id,
        instance_id=instance.instance_id
    )
    
    if existing:
        if request.on_duplicate == "skip":
            print(f"Skipping {instance.instance_id} (already exists)")
            continue
        elif request.on_duplicate == "overwrite":
            print(f"Overwriting {instance.instance_id}")
            # 重置状态
            existing.status = "pending"
            existing.started_at = None
            existing.completed_at = None
            existing.result_summary = None
        else:
            # 询问用户
            choice = ask_user(f"Instance {instance.instance_id} exists. Skip or overwrite?")
            if choice == "skip":
                continue
            else:
                # 重置状态
                existing.status = "pending"
    else:
        # 创建新任务
        BatchResult(
            batch_id=batch.id,
            instance_id=instance.instance_id,
            dataset_instance_id=instance.id,
            model=batch.model,
            tag=batch.tag,
            status="pending"
        )
        batch.total_tasks += 1
        batch.pending_tasks += 1
```

---

### 场景 4: 查看批次状态

```bash
GET /api/v1/batches/1

# 响应
{
  "id": 1,
  "batch_name": "baseline",
  "model": "gpt-4-turbo",
  "tag": "baseline",
  "status": "running",
  
  "statistics": {
    "total_tasks": 200,
    "pending_tasks": 85,      # 排队中
    "running_tasks": 10,      # 运行中
    "completed_tasks": 100,   # 已完成
    "failed_tasks": 5,        # 失败
    
    "success_rate": 0.952,           # 100 / (100 + 5)
    "validation_success_rate": 0.90  # 从 completed 中计算
  },
  
  "progress": {
    "percentage": 52.5,  # (100 + 5) / 200
    "estimated_remaining_seconds": 1250
  }
}
```

---

### 场景 5: 查看任务详情

```bash
GET /api/v1/batches/1/tasks?status=pending&limit=10

# 响应：排队中的任务
{
  "batch_id": 1,
  "tasks": [
    {
      "id": 106,
      "instance_id": "django__django-11205",
      "status": "pending",
      "created_at": "2026-05-14T16:00:00Z"
    },
    ...
  ]
}
```

```bash
GET /api/v1/batches/1/tasks?status=running&limit=10

# 响应：运行中的任务
{
  "batch_id": 1,
  "tasks": [
    {
      "id": 1,
      "instance_id": "django__django-11099",
      "status": "running",
      "started_at": "2026-05-14T16:05:00Z",
      "duration_seconds": 125.5
    },
    ...
  ]
}
```

---

## 数据去重策略

### 添加任务时的去重检查

```python
def add_tasks_to_batch(batch_id, instances, on_duplicate="ask"):
    """
    添加任务到批次
    
    Args:
        batch_id: 批次 ID
        instances: 要添加的数据实例列表
        on_duplicate: 重复处理策略
            - "skip": 跳过已存在的
            - "overwrite": 覆盖已存在的（重置状态）
            - "ask": 询问用户（默认）
    """
    batch = get_batch(batch_id)
    results = []
    
    for instance in instances:
        # 检查是否已存在
        existing = db.query(BatchResult).filter(
            BatchResult.batch_id == batch_id,
            BatchResult.instance_id == instance.instance_id
        ).first()
        
        if existing:
            # 已存在，根据策略处理
            if on_duplicate == "skip":
                results.append({
                    "instance_id": instance.instance_id,
                    "action": "skipped",
                    "reason": "already exists"
                })
                continue
            
            elif on_duplicate == "overwrite":
                # 重置为 pending 状态
                existing.status = "pending"
                existing.started_at = None
                existing.completed_at = None
                existing.result_summary = None
                existing.validation_success = None
                
                # 更新批次统计
                if existing.status == "completed":
                    batch.completed_tasks -= 1
                elif existing.status == "failed":
                    batch.failed_tasks -= 1
                
                batch.pending_tasks += 1
                
                results.append({
                    "instance_id": instance.instance_id,
                    "action": "overwritten",
                    "previous_status": existing.status
                })
            
            elif on_duplicate == "ask":
                # 返回给前端，让用户选择
                results.append({
                    "instance_id": instance.instance_id,
                    "action": "needs_confirmation",
                    "existing_status": existing.status,
                    "existing_result": existing.result_summary
                })
        
        else:
            # 不存在，创建新任务
            new_task = BatchResult(
                batch_id=batch_id,
                instance_id=instance.instance_id,
                dataset_instance_id=instance.id,
                model=batch.model,
                tag=batch.tag,
                status="pending"
            )
            db.add(new_task)
            
            batch.total_tasks += 1
            batch.pending_tasks += 1
            
            results.append({
                "instance_id": instance.instance_id,
                "action": "added"
            })
    
    db.commit()
    return results
```

### 前端交互流程

```
用户添加任务 (100-200)
    ↓
系统检查重复
    ↓
发现 10 个已存在
    ↓
┌─────────────────────────────────────┐
│  发现重复任务                        │
│                                     │
│  以下 10 个任务已存在:              │
│  ☑ django__django-11150 (已完成)   │
│  ☑ django__django-11151 (失败)     │
│  ☑ django__django-11152 (运行中)   │
│  ...                                │
│                                     │
│  如何处理?                          │
│  ○ 全部跳过                         │
│  ○ 全部覆盖 (重新运行)              │
│  ○ 让我逐个选择                     │
│                                     │
│  [取消]  [确定]                     │
└─────────────────────────────────────┘
```

---

## 对比不同批次

### 跨批次对比

```bash
GET /api/v1/comparisons?batch_names=baseline,experiment_1

# 响应
{
  "batches": [
    {
      "batch_name": "baseline",
      "model": "gpt-4-turbo",
      "tag": "baseline",
      "total_tasks": 300,
      "completed": 285,
      "success_rate": 0.95,
      "validation_success_rate": 0.87
    },
    {
      "batch_name": "experiment_1",
      "model": "gpt-4-turbo",
      "tag": "experiment_1",
      "total_tasks": 200,
      "completed": 195,
      "success_rate": 0.975,
      "validation_success_rate": 0.92
    }
  ],
  
  "common_instances": 200,
  "comparison": {
    "both_success": 175,
    "baseline_only_success": 10,
    "experiment_only_success": 15,
    "both_failed": 0
  }
}
```

---

## 核心优势

### ✅ 1. 简化的数据关系

```
旧设计 (4 层):
数据 → 执行 → 结果 → 批次

新设计 (3 层):
数据 → 批次 → 结果
```

### ✅ 2. 统一的任务管理

```
所有任务状态在批次内查看:
- pending: 排队中
- running: 运行中
- completed: 已完成
- failed: 失败
```

### ✅ 3. 灵活的去重策略

```python
add_tasks(on_duplicate="skip")      # 跳过
add_tasks(on_duplicate="overwrite") # 覆盖
add_tasks(on_duplicate="ask")       # 询问
```

### ✅ 4. 并行执行友好

```
批次状态实时更新:
total=200, pending=85, running=10, completed=100, failed=5
```

---

## 迁移对比

| 特性 | 旧设计 | 新设计 |
|------|--------|--------|
| 层次数量 | 4 层 | 3 层 ✅ |
| 核心组织单位 | execution | batch ✅ |
| 任务状态查看 | 分散在多个 execution | 统一在 batch ✅ |
| 追加数据 | 创建新 execution | 直接添加到 batch ✅ |
| 去重处理 | 基于 tag | 基于 batch_id ✅ |
| 并行支持 | 需要额外管理 | 内置 pending 状态 ✅ |

---

## 总结

### 核心改进

1. **✅ 去除执行层**：不需要 `executions` 表
2. **✅ 批次为核心**：所有操作围绕批次展开
3. **✅ 任务状态清晰**：pending → running → completed/failed
4. **✅ 去重策略明确**：skip/overwrite/ask 三种模式
5. **✅ 并行执行友好**：内置排队机制

### 用户视角

```
创建批次 → 添加任务 → 启动批次 → 查看进度 → 追加任务 → 查看结果
           ↑_______↓     (自动处理重复)
```

**简单！清晰！高效！** 🎉

---

**版本**: v2.0  
**更新日期**: 2026-05-14  
**重大变更**: 去除执行层，简化为批次 + 结果两层架构
