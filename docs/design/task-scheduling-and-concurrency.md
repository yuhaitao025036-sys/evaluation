# 任务调度和并发控制设计

## 核心理念

**系统级调度，而非脚本级循环**

```
❌ 旧方式：脚本处理范围
python script.py --start-index 0 --end-index 100
└─ 脚本内部循环 100 次

✅ 新方式：系统调度单任务
for each instance:
    queue.enqueue(run_task, instance_id="django-11099")
└─ Worker 并行执行
```

---

## 架构设计

### 系统组件

```
┌─────────────────┐
│   Web API       │ ← 用户创建批次、添加任务
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Task Scheduler  │ ← 任务调度器（新增）
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Redis Queue    │ ← 任务队列
│  (RQ/Celery)    │
└────────┬────────┘
         │
         ├──────┬──────┬──────┐
         ▼      ▼      ▼      ▼
    ┌────────┐┌────────┐┌────────┐
    │Worker 1││Worker 2││Worker 3│ ← 并发执行
    └────────┘└────────┘└────────┘
         │      │      │
         └──────┴──────┴──────┐
                               ▼
                        ┌─────────────┐
                        │  Database   │
                        └─────────────┘
```

---

## 数据模型更新

### 批次表（添加并发控制字段）

```sql
CREATE TABLE batches (
    id SERIAL PRIMARY KEY,
    batch_name VARCHAR(200) UNIQUE NOT NULL,
    
    -- 批次配置
    dataset_id INTEGER REFERENCES datasets(id),
    model VARCHAR(100) NOT NULL,
    tag VARCHAR(100) NOT NULL,
    
    -- 执行配置
    execution_config JSONB,
    
    -- 并发控制 ⭐️ 新增
    max_concurrency INTEGER DEFAULT 10,        -- 此批次最大并发数
    current_running INTEGER DEFAULT 0,         -- 当前运行中的任务数
    priority INTEGER DEFAULT 0,                -- 优先级（0最高）
    
    -- 批次状态
    status VARCHAR(50) DEFAULT 'created',      -- created, running, paused, completed, failed
    
    -- 任务统计
    total_tasks INTEGER DEFAULT 0,
    pending_tasks INTEGER DEFAULT 0,
    running_tasks INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    failed_tasks INTEGER DEFAULT 0,
    
    -- 时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 输出目录
    output_dir VARCHAR(512)
);

CREATE INDEX idx_batches_status ON batches(status);
CREATE INDEX idx_batches_priority ON batches(priority, status);
```

### 任务结果表（保持不变，但强调 instance 级别）

```sql
CREATE TABLE batch_results (
    id SERIAL PRIMARY KEY,
    
    -- 关联
    batch_id INTEGER REFERENCES batches(id) ON DELETE CASCADE,
    dataset_instance_id INTEGER REFERENCES dataset_instances(id),
    instance_id VARCHAR(255) NOT NULL,  -- ⭐️ 任务粒度：单个 instance
    
    -- 批次信息
    model VARCHAR(100) NOT NULL,
    tag VARCHAR(100) NOT NULL,
    
    -- 任务状态 ⭐️ 关键
    status VARCHAR(50) DEFAULT 'pending',  -- pending, queued, running, completed, failed, retrying
    retry_count INTEGER DEFAULT 0,         -- 重试次数
    max_retries INTEGER DEFAULT 3,         -- 最大重试次数
    
    -- 队列信息
    job_id VARCHAR(255),                   -- RQ/Celery 任务 ID
    worker_id VARCHAR(100),                -- 处理此任务的 Worker ID
    
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
    error_message TEXT,                    -- 失败原因
    
    -- 时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    queued_at TIMESTAMP WITH TIME ZONE,    -- 加入队列时间
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- 唯一约束
    UNIQUE(batch_id, instance_id)
);

CREATE INDEX idx_batch_results_batch ON batch_results(batch_id);
CREATE INDEX idx_batch_results_status ON batch_results(status);
CREATE INDEX idx_batch_results_job_id ON batch_results(job_id);
```

---

## 任务调度流程

### 1. 用户创建批次并添加任务

```bash
POST /api/v1/batches
{
  "batch_name": "baseline",
  "dataset_id": 1,
  "start_index": 0,
  "end_index": 100,
  "model": "gpt-4-turbo",
  "tag": "baseline",
  "max_concurrency": 10,  # 最多 10 个任务并行
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
    max_concurrency=10,
    status="created"
)
db.add(batch)
db.flush()

# 2. 为每个 instance 创建任务记录（不是调用脚本！）
instances = get_dataset_instances(dataset_id=1, start=0, end=100)
for instance in instances:
    BatchResult(
        batch_id=batch.id,
        instance_id=instance.instance_id,
        dataset_instance_id=instance.id,
        model=batch.model,
        tag=batch.tag,
        status="pending",  # 初始状态
        max_retries=3
    )

batch.total_tasks = len(instances)
batch.pending_tasks = len(instances)
db.commit()
```

---

### 2. 启动批次（调度任务）

```bash
POST /api/v1/batches/1/start
```

**系统操作**：
```python
def start_batch(batch_id):
    """启动批次，开始调度任务"""
    batch = db.query(Batch).get(batch_id)
    
    # 1. 检查全局并发限制
    global_running = db.query(func.sum(Batch.current_running)).scalar() or 0
    if global_running >= MAX_GLOBAL_CONCURRENCY:
        raise ValueError(f"Global concurrency limit reached: {global_running}/{MAX_GLOBAL_CONCURRENCY}")
    
    # 2. 更新批次状态
    batch.status = "running"
    batch.started_at = datetime.utcnow()
    db.commit()
    
    # 3. 启动任务调度器
    schedule_tasks(batch_id)
```

**任务调度器**（核心逻辑）：
```python
def schedule_tasks(batch_id):
    """
    任务调度器：持续从 pending 任务中选取任务加入队列
    """
    while True:
        batch = db.query(Batch).get(batch_id)
        
        # 检查批次状态
        if batch.status == "paused":
            print(f"Batch {batch_id} paused, scheduler stopped")
            break
        
        if batch.status == "completed":
            print(f"Batch {batch_id} completed")
            break
        
        # 检查是否还有待处理任务
        if batch.pending_tasks == 0 and batch.running_tasks == 0:
            # 所有任务完成
            batch.status = "completed"
            batch.completed_at = datetime.utcnow()
            db.commit()
            break
        
        # 计算可以调度的任务数
        available_slots = batch.max_concurrency - batch.current_running
        if available_slots <= 0:
            # 并发已满，等待
            time.sleep(1)
            continue
        
        # 获取 pending 任务
        pending_tasks = db.query(BatchResult).filter(
            BatchResult.batch_id == batch_id,
            BatchResult.status == "pending"
        ).order_by(
            BatchResult.id  # FIFO 顺序
        ).limit(available_slots).all()
        
        if not pending_tasks:
            # 没有 pending 任务，但还有 running 任务，等待
            time.sleep(1)
            continue
        
        # 调度任务到队列
        for task in pending_tasks:
            enqueue_task(batch_id, task.id, task.instance_id)
        
        time.sleep(0.5)  # 短暂休眠，避免过于频繁查询
```

---

### 3. 任务入队

```python
def enqueue_task(batch_id, task_id, instance_id):
    """将单个任务加入队列"""
    batch = db.query(Batch).get(batch_id)
    task = db.query(BatchResult).get(task_id)
    
    # 更新状态
    task.status = "queued"
    task.queued_at = datetime.utcnow()
    
    batch.pending_tasks -= 1
    batch.current_running += 1
    
    db.commit()
    
    # 加入 RQ 队列
    job = queue.enqueue(
        execute_single_task,
        batch_id=batch_id,
        task_id=task_id,
        instance_id=instance_id,
        timeout=batch.execution_config.get('timeout', 1800),
        job_id=f"batch_{batch_id}_task_{task_id}"
    )
    
    # 记录 job_id
    task.job_id = job.id
    db.commit()
    
    print(f"Task {task_id} ({instance_id}) enqueued")
```

---

### 4. Worker 执行任务

```python
def execute_single_task(batch_id, task_id, instance_id):
    """
    Worker 执行单个任务
    
    关键：脚本只处理一个 instance
    """
    import subprocess
    
    # 1. 更新状态为 running
    task = db.query(BatchResult).get(task_id)
    task.status = "running"
    task.started_at = datetime.utcnow()
    task.worker_id = get_current_worker_id()
    
    batch = db.query(Batch).get(batch_id)
    batch.running_tasks += 1
    
    db.commit()
    
    try:
        # 2. 获取数据实例
        instance = db.query(DatasetInstance).filter(
            DatasetInstance.instance_id == instance_id
        ).first()
        
        # 3. 准备输出目录
        safe_id = instance_id.replace('/', '_').replace(':', '_')
        task_output_dir = os.path.join(batch.output_dir, 'tasks', safe_id)
        os.makedirs(task_output_dir, exist_ok=True)
        
        # 4. 构建命令 ⭐️ 关键：只传递 instance_id
        script_path = batch.execution_config['script']
        script_args = batch.execution_config.get('args', '')
        
        cmd = [
            'python', script_path,
            '--instance-id', instance_id,           # ⭐️ 单个任务
            '--output-dir', task_output_dir,
            '--model', batch.model,
            '--tag', batch.tag
        ]
        
        # 添加自定义参数
        if script_args:
            cmd.extend(shlex.split(script_args))
        
        # 5. 执行脚本
        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=batch.execution_config.get('timeout', 1800)
        )
        duration = time.time() - start_time
        
        # 6. 解析结果
        summary_path = os.path.join(task_output_dir, 'task_summary.json')
        if os.path.exists(summary_path):
            with open(summary_path, 'r') as f:
                summary = json.load(f)
            
            # 更新任务状态
            task.status = "completed"
            task.validation_success = summary.get('validation', {}).get('success')
            task.tests_passed = summary.get('validation', {}).get('tests_passed', 0)
            task.tests_failed = summary.get('validation', {}).get('tests_failed', 0)
            task.tests_total = summary.get('validation', {}).get('tests_total', 0)
            task.result_summary = summary
            task.patch_path = os.path.join(task_output_dir, 'extracted_patch.diff')
        else:
            # 脚本没有输出 summary，视为失败
            task.status = "failed"
            task.error_message = f"Script did not produce task_summary.json\nStdout: {result.stdout}\nStderr: {result.stderr}"
        
        task.duration_seconds = duration
        task.completed_at = datetime.utcnow()
        
        # 更新批次统计
        batch.running_tasks -= 1
        batch.current_running -= 1
        if task.status == "completed":
            batch.completed_tasks += 1
        else:
            batch.failed_tasks += 1
        
        db.commit()
        
        print(f"Task {task_id} ({instance_id}) completed: {task.status}")
    
    except subprocess.TimeoutExpired:
        # 超时
        handle_task_failure(batch_id, task_id, "Timeout", retry=True)
    
    except Exception as e:
        # 其他错误
        handle_task_failure(batch_id, task_id, str(e), retry=True)
```

---

### 5. 任务失败处理和重试

```python
def handle_task_failure(batch_id, task_id, error_message, retry=True):
    """处理任务失败"""
    task = db.query(BatchResult).get(task_id)
    batch = db.query(Batch).get(batch_id)
    
    # 更新运行计数
    batch.running_tasks -= 1
    batch.current_running -= 1
    
    # 检查是否需要重试
    if retry and task.retry_count < task.max_retries:
        # 重试
        task.retry_count += 1
        task.status = "pending"  # 重新加入待处理队列
        task.error_message = f"Attempt {task.retry_count}: {error_message}"
        
        batch.pending_tasks += 1
        
        print(f"Task {task_id} failed, will retry ({task.retry_count}/{task.max_retries})")
    else:
        # 不重试或已达最大重试次数
        task.status = "failed"
        task.error_message = error_message
        task.completed_at = datetime.utcnow()
        
        batch.failed_tasks += 1
        
        print(f"Task {task_id} permanently failed: {error_message}")
    
    db.commit()
```

---

## 脚本接口更新

### 旧接口（范围处理）

```python
# ❌ 旧方式：脚本接收范围
parser.add_argument('--start-index', type=int, required=True)
parser.add_argument('--end-index', type=int, required=True)

# 脚本内部循环
for i in range(args.start_index, args.end_index):
    instance = dataset[i]
    process(instance)
```

### 新接口（单任务处理）⭐️

```python
# ✅ 新方式：脚本只处理单个 instance
parser.add_argument('--instance-id', required=True, help='单个数据实例的 ID')
parser.add_argument('--output-dir', required=True, help='输出目录')
parser.add_argument('--model', required=True)
parser.add_argument('--tag', required=True)

# 脚本只处理一个任务
instance_id = args.instance_id
instance = load_instance_by_id(instance_id)  # 通过 ID 加载数据
result = process(instance)

# 输出结果
save_task_summary(args.output_dir, result)
```

**示例脚本**：
```python
#!/usr/bin/env python3
"""
单任务评估脚本（新接口）
"""
import argparse
import json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance-id', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    
    # 1. 加载数据（通过 instance_id）
    # 注意：数据可以从数据库、API 或本地文件加载
    instance = load_instance_from_db(args.instance_id)
    
    # 2. 执行评估
    result = evaluate(instance, args.model)
    
    # 3. 输出结果
    summary = {
        'instance_id': args.instance_id,
        'status': 'completed',
        'model': args.model,
        'tag': args.tag,
        'validation': result.validation
    }
    
    with open(f'{args.output_dir}/task_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✓ Completed: {args.instance_id}")

if __name__ == '__main__':
    main()
```

---

## 并发控制配置

### 系统配置

```python
# backend/app/config.py

# 全局并发限制
MAX_GLOBAL_CONCURRENCY = 20      # 系统最多 20 个任务并行
MAX_CONCURRENT_BATCHES = 5       # 最多 5 个批次同时运行

# RQ Worker 配置
RQ_WORKER_COUNT = 10             # Worker 数量
RQ_QUEUE_NAME = "default"

# 任务配置
DEFAULT_MAX_CONCURRENCY = 10     # 批次默认并发
DEFAULT_MAX_RETRIES = 3          # 默认重试次数
DEFAULT_TASK_TIMEOUT = 1800      # 默认超时 30 分钟
```

### 启动 Workers

```bash
# start_workers.sh
#!/bin/bash

# 启动 10 个 RQ workers
for i in {1..10}; do
    rq worker default --name worker_$i &
done

echo "Started 10 workers"
```

---

## API 设计

### 启动批次（带并发控制）

```bash
POST /api/v1/batches/1/start
{
  "max_concurrency": 5  # 可选，覆盖批次默认值
}

# 响应
{
  "batch_id": 1,
  "status": "running",
  "max_concurrency": 5,
  "current_running": 0,
  "pending_tasks": 100
}
```

### 暂停批次

```bash
POST /api/v1/batches/1/pause

# 系统行为：
# 1. 更新 batch.status = "paused"
# 2. 调度器停止调度新任务
# 3. 已运行的任务继续执行完成
```

### 恢复批次

```bash
POST /api/v1/batches/1/resume

# 系统行为：
# 1. 更新 batch.status = "running"
# 2. 重新启动调度器
```

### 查看实时状态

```bash
GET /api/v1/batches/1

# 响应
{
  "id": 1,
  "batch_name": "baseline",
  "status": "running",
  "max_concurrency": 10,
  "current_running": 10,
  
  "statistics": {
    "total_tasks": 100,
    "pending_tasks": 35,
    "running_tasks": 10,
    "completed_tasks": 50,
    "failed_tasks": 5,
    
    "progress_percentage": 55.0,
    "success_rate": 0.909,  # 50 / (50 + 5)
    "estimated_remaining_seconds": 1750
  }
}
```

### 重试失败任务

```bash
POST /api/v1/batches/1/retry-failed

# 系统行为：
# 1. 找到所有 status="failed" 的任务
# 2. 重置 status="pending"
# 3. retry_count = 0
# 4. 调度器会自动调度这些任务
```

---

## 优势总结

### ✅ 系统级调度

| 特性 | 旧方式（范围） | 新方式（单任务） |
|------|--------------|----------------|
| 并发控制 | ❌ 脚本内部 | ✅ 系统级别 |
| 任务粒度 | ❌ 批量 | ✅ 单个 |
| 状态更新 | ❌ 批量完成后 | ✅ 实时 |
| 失败重试 | ❌ 重跑整个范围 | ✅ 只重试失败的 |
| 暂停/恢复 | ❌ 不支持 | ✅ 支持 |
| 优先级 | ❌ 不支持 | ✅ 支持 |

### ✅ 灵活性

```python
# 可以单独重试某个任务
POST /api/v1/batches/1/tasks/42/retry

# 可以调整并发度
POST /api/v1/batches/1/update-concurrency
{"max_concurrency": 15}

# 可以取消某个任务
POST /api/v1/batches/1/tasks/42/cancel
```

---

## 总结

### 核心改进

1. **✅ 系统控制并发**：不依赖脚本实现
2. **✅ 单任务调度**：脚本只处理一个 instance
3. **✅ 实时状态更新**：每个任务独立状态
4. **✅ 灵活的失败处理**：自动重试、单独重试
5. **✅ 完整的生命周期管理**：暂停、恢复、取消

### 脚本迁移

**旧脚本改造指南**：
```python
# 原来的循环逻辑
for i in range(start_index, end_index):
    instance = dataset[i]
    process(instance)

# 改为：
instance_id = args.instance_id
instance = load_by_id(instance_id)
process(instance)
```

这个设计更加清晰、可控、灵活！🎉

---

**版本**: v2.1  
**更新日期**: 2026-05-14  
**重大变更**: 从范围处理改为单任务调度，系统级并发控制
