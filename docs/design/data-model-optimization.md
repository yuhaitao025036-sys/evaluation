# 数据模型优化设计

## 问题分析

### 当前问题

1. **脚本不应该和数据耦合**
   - 当前 `tasks` 表有 `script_id`，但实际上脚本只是执行工具
   - 关注点应该是**任务执行结果**，而非用什么脚本执行

2. **数据关系复杂**
   - 数据（dataset_instance）→ 任务执行（task_instance）→ 批次（batch）
   - 一个数据可以被执行多次（不同 tag）
   - 一个批次包含多个数据的执行结果

3. **批次定义不清晰**
   - 批次应该是**统计单位**，不是执行单位
   - 当前设计中 `task_groups` 既是执行管理，又承担批次功能

---

## 优化后的数据模型

### 核心理念

**关注点分离**：
- **数据层**：`dataset` + `dataset_instances` - 数据本身（静态）
- **执行层**：`executions` - 一次批量执行任务的记录（类似 task_groups，1→N）
- **结果层**：`execution_results` - 每个数据实例的执行结果（核心！N→1）
- **统计层**：`batches` - 批次聚合统计（实时计算）

**详细说明**：参见 [data-model-layers-explained.md](data-model-layers-explained.md)

---

## 优化后的表结构

### 1. 数据层（保持不变）

```sql
-- 数据集元信息
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
    data JSONB NOT NULL,  -- 包含所有字段
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(dataset_id, instance_id)
);

CREATE INDEX idx_dataset_instances_instance_id ON dataset_instances(instance_id);
CREATE INDEX idx_dataset_instances_data_gin ON dataset_instances USING GIN (data);
```

---

### 2. 执行层（批量执行任务）

```sql
-- 执行记录（一次批量执行任务，处理 N 个数据实例）
-- 类似当前的 task_groups，但简化了
CREATE TABLE executions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    
    -- 执行配置
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE CASCADE,
    model VARCHAR(100) NOT NULL,
    tag VARCHAR(100) NOT NULL,
    
    -- 执行范围（处理哪些数据）
    start_index INTEGER DEFAULT 0,
    end_index INTEGER,
    
    -- 执行参数（脚本路径、参数等，仅用于记录）
    execution_config JSONB,  -- {"script": "...", "args": "...", "timeout": 1800}
    
    -- 执行状态
    status VARCHAR(50) DEFAULT 'created',  -- created, running, completed, failed
    total_instances INTEGER,
    completed_instances INTEGER DEFAULT 0,
    failed_instances INTEGER DEFAULT 0,
    
    -- 时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- 输出目录（用于查找结果文件）
    output_dir VARCHAR(512)
);

CREATE INDEX idx_executions_status ON executions(status);
CREATE INDEX idx_executions_model_tag ON executions(model, tag);
CREATE INDEX idx_executions_dataset ON executions(dataset_id);
```

**关键说明**：
- ✅ 一次 execution = 一次批量任务（处理 start_index 到 end_index 的数据）
- ✅ 一个 execution 会生成多个 execution_results（1:N 关系）
- ❌ 去除 `script_id` - 脚本信息存储在 `execution_config` 中仅供参考
- ✅ 关注执行参数：`model`, `tag`, `dataset_id`

**数量示例**：
```
execution (id=1): start_index=0, end_index=100
    ↓ 生成
100 条 execution_results (每个数据实例一条)
```

---

### 3. 结果层（核心）

```sql
-- 执行结果（每个数据实例的执行结果）
CREATE TABLE execution_results (
    id SERIAL PRIMARY KEY,
    
    -- 关联
    execution_id INTEGER REFERENCES executions(id) ON DELETE CASCADE,
    dataset_instance_id INTEGER REFERENCES dataset_instances(id),
    instance_id VARCHAR(255) NOT NULL,
    
    -- 执行标识（用于去重和查询）
    model VARCHAR(100) NOT NULL,
    tag VARCHAR(100) NOT NULL,
    
    -- 执行结果
    status VARCHAR(50) NOT NULL,  -- completed, failed
    
    -- 验证结果
    validation_success BOOLEAN,
    tests_passed INTEGER DEFAULT 0,
    tests_failed INTEGER DEFAULT 0,
    tests_total INTEGER DEFAULT 0,
    
    -- 性能
    duration_seconds FLOAT,
    
    -- 结果详情
    result_summary JSONB,  -- task_summary.json 的内容
    patch_path VARCHAR(512),  -- extracted_patch.diff 路径
    
    -- 时间
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- 唯一约束：同一 instance + tag 只能有一个最新结果
    UNIQUE(instance_id, tag)
);

CREATE INDEX idx_execution_results_execution_id ON execution_results(execution_id);
CREATE INDEX idx_execution_results_instance_id ON execution_results(instance_id);
CREATE INDEX idx_execution_results_model_tag ON execution_results(model, tag);
CREATE INDEX idx_execution_results_status ON execution_results(status);
CREATE INDEX idx_execution_results_instance_tag ON execution_results(instance_id, tag);
```

**关键设计**：
- ✅ `UNIQUE(instance_id, tag)` - 同一 instance + tag 只有一个结果
- ✅ 如果重新执行，会更新（或覆盖）之前的结果
- ✅ 所有统计都基于这个表

---

### 4. 统计层（批次）

```sql
-- 批次（用于聚合统计）
CREATE TABLE batches (
    id SERIAL PRIMARY KEY,
    batch_name VARCHAR(200) UNIQUE NOT NULL,
    
    -- 批次配置（必须一致）
    model VARCHAR(100) NOT NULL,
    tag VARCHAR(100) NOT NULL,
    dataset_id INTEGER REFERENCES datasets(id),
    
    -- 描述
    description TEXT,
    
    -- 时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 批次和执行的关联（多对多）
CREATE TABLE batch_executions (
    id SERIAL PRIMARY KEY,
    batch_id INTEGER REFERENCES batches(id) ON DELETE CASCADE,
    execution_id INTEGER REFERENCES executions(id) ON DELETE CASCADE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(batch_id, execution_id)
);

CREATE INDEX idx_batch_executions_batch ON batch_executions(batch_id);
CREATE INDEX idx_batch_executions_execution ON batch_executions(execution_id);
```

**批次统计（实时计算，不存储）**：
```sql
-- 查询批次统计
SELECT 
    b.batch_name,
    b.model,
    b.tag,
    COUNT(DISTINCT er.instance_id) as total_instances,
    SUM(CASE WHEN er.status = 'completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN er.status = 'failed' THEN 1 ELSE 0 END) as failed,
    AVG(CASE WHEN er.status = 'completed' THEN 1.0 ELSE 0.0 END) as success_rate,
    AVG(CASE WHEN er.validation_success THEN 1.0 ELSE 0.0 END) as validation_success_rate
FROM batches b
JOIN batch_executions be ON be.batch_id = b.id
JOIN executions e ON e.id = be.execution_id
JOIN execution_results er ON er.execution_id = e.id
WHERE b.batch_name = 'baseline'
GROUP BY b.id, b.batch_name, b.model, b.tag;
```

---

## 数据关系图

```
┌──────────────┐
│   datasets   │
└──────┬───────┘
       │ 1:N
       ▼
┌──────────────────┐
│dataset_instances │  ← 数据层：数据本身
└──────┬───────────┘
       │
       │ N:M (通过 execution_results)
       │
┌──────▼───────┐         ┌──────────────┐
│  executions  │ 1:N ────│execution_    │  ← 结果层：核心
│              │         │results       │
└──────┬───────┘         └──────────────┘
       │                        ▲
       │ N:M                    │ N:1 (通过 tag)
       │                        │
┌──────▼───────────┐    ┌───────┴──────┐
│batch_executions  │ N:1│   batches    │  ← 统计层：聚合
└──────────────────┘    └──────────────┘
```

---

## 关键关系说明

### 1. 数据 → 执行结果（N:M）

**一个数据可以被执行多次（不同 tag）**：

```
django__django-11099 (数据)
├─ execution_result (tag=baseline, model=gpt-4)
├─ execution_result (tag=experiment_1, model=gpt-4)
└─ execution_result (tag=experiment_2, model=claude)
```

**实现**：`execution_results` 表通过 `UNIQUE(instance_id, tag)` 保证唯一性

### 2. 执行 → 批次（N:M）

**一次执行可以属于多个批次**（不推荐，但技术上可行）：
**一个批次可以包含多次执行**（推荐，渐进式追加）：

```
baseline 批次
├─ execution_1 (0-100)
├─ execution_2 (100-200)
└─ execution_3 (200-300)
```

**实现**：通过 `batch_executions` 关联表

### 3. 批次 → 结果（通过 execution）

**批次的统计通过 SQL 实时计算**：

```sql
-- baseline 批次的所有结果
SELECT er.*
FROM execution_results er
JOIN executions e ON e.id = er.execution_id
JOIN batch_executions be ON be.execution_id = e.id
JOIN batches b ON b.id = be.batch_id
WHERE b.batch_name = 'baseline';
```

---

## 核心优势

### ✅ 1. 脚本解耦

```python
# 创建执行时，脚本只是配置的一部分
execution = Execution(
    model='gpt-4-turbo',
    tag='baseline',
    execution_config={
        'script': '/path/to/script.py',
        'args': '--timeout 1800',
        'executor': 'python3'
    }
)
```

**关注点**：`model` + `tag` + 执行结果，而非用什么脚本

### ✅ 2. 数据关系清晰

```
数据（dataset_instance）
    ↓
执行结果（execution_result）  ← 核心！
    ↓
批次统计（batch）
```

- 数据是静态的
- 执行结果是动态的（可以重新执行）
- 批次是聚合的（实时计算）

### ✅ 3. 支持灵活的批次管理

```bash
# 场景 1：新建批次
POST /api/v1/executions
{
  "batch_name": "baseline",
  "model": "gpt-4-turbo",
  "tag": "baseline",
  "start_index": 0,
  "end_index": 100
}

# 场景 2：追加到批次
POST /api/v1/executions
{
  "batch_name": "baseline",
  "append_to_batch": true,
  "model": "gpt-4-turbo",
  "tag": "baseline",
  "start_index": 100,
  "end_index": 200
}

# 场景 3：重新执行（覆盖结果）
POST /api/v1/executions
{
  "batch_name": "baseline",
  "model": "gpt-4-turbo",
  "tag": "baseline",
  "start_index": 0,
  "end_index": 50,
  "overwrite": true  # 覆盖已有的 execution_results
}
```

### ✅ 4. 避免数据重复

**UNIQUE 约束**：`execution_results(instance_id, tag)`

```sql
-- 如果重新执行同一个 instance + tag
INSERT INTO execution_results (instance_id, tag, ...)
VALUES ('django__django-11099', 'baseline', ...)
ON CONFLICT (instance_id, tag)
DO UPDATE SET
    status = EXCLUDED.status,
    validation_success = EXCLUDED.validation_success,
    completed_at = EXCLUDED.completed_at,
    execution_id = EXCLUDED.execution_id;  -- 更新为最新执行
```

---

## API 设计建议

### 创建执行（替代创建任务组）

```bash
POST /api/v1/executions
{
  "name": "Baseline Run 1",
  "batch_name": "baseline",  # 可选，指定批次
  "append_to_batch": false,
  
  "dataset_id": 1,
  "model": "gpt-4-turbo",
  "tag": "baseline",
  
  "start_index": 0,
  "end_index": 100,
  
  "execution_config": {
    "script": "data/scripts/swebench_eval.py",
    "args": "--timeout 1800 --use-tmux",
    "executor": "python3"
  }
}
```

### 查询批次统计

```bash
GET /api/v1/batches/baseline/statistics

# 响应
{
  "batch_name": "baseline",
  "model": "gpt-4-turbo",
  "tag": "baseline",
  
  "executions": [
    {"id": 1, "name": "Baseline Run 1", "instances": 100},
    {"id": 3, "name": "Baseline Run 2", "instances": 100}
  ],
  
  "statistics": {
    "total_instances": 200,
    "completed": 185,
    "failed": 15,
    "success_rate": 0.925,
    "validation_success_rate": 0.870
  }
}
```

### 查询单个数据的执行历史

```bash
GET /api/v1/results?instance_id=django__django-11099

# 响应
{
  "instance_id": "django__django-11099",
  "results": [
    {
      "tag": "baseline",
      "model": "gpt-4-turbo",
      "status": "completed",
      "validation_success": true,
      "execution_id": 1,
      "completed_at": "2026-05-14T10:30:00Z"
    },
    {
      "tag": "experiment_1",
      "model": "gpt-4-turbo",
      "status": "completed",
      "validation_success": true,
      "execution_id": 5,
      "completed_at": "2026-05-14T15:20:00Z"
    }
  ]
}
```

---

## 迁移建议

### 从现有表迁移到新表

```sql
-- 1. 创建新表
-- (使用上面的 CREATE TABLE 语句)

-- 2. 迁移 task_groups → executions
INSERT INTO executions (name, dataset_id, model, tag, start_index, end_index, status, total_instances, created_at, output_dir, execution_config)
SELECT 
    name,
    dataset_id,
    'gpt-4-turbo',  -- 需要从实际数据中提取
    tag,
    start_index,
    end_index,
    status,
    total_instances,
    created_at,
    NULL,  -- output_dir
    jsonb_build_object('script_id', script_id, 'args', script_args)
FROM task_groups;

-- 3. 迁移 task_instances → execution_results
INSERT INTO execution_results (
    execution_id,
    dataset_instance_id,
    instance_id,
    model,
    tag,
    status,
    validation_success,
    tests_passed,
    tests_failed,
    duration_seconds,
    started_at,
    completed_at,
    result_summary
)
SELECT 
    t.id,  -- 映射到新的 execution_id
    ti.dataset_instance_id,
    ti.instance_id,
    'gpt-4-turbo',  -- 需要从 task 中获取
    ti.tag,
    ti.status,
    ti.validation_success,
    ti.test_passed,
    ti.test_failed,
    ti.duration_seconds,
    ti.started_at,
    ti.completed_at,
    ti.summary
FROM task_instances ti
JOIN tasks t ON t.id = ti.task_id;

-- 4. 创建批次（如果需要）
INSERT INTO batches (batch_name, model, tag, dataset_id)
SELECT DISTINCT
    tag as batch_name,  -- 或者使用其他命名规则
    'gpt-4-turbo',
    tag,
    dataset_id
FROM task_groups;

-- 5. 关联批次和执行
INSERT INTO batch_executions (batch_id, execution_id)
SELECT b.id, e.id
FROM batches b
JOIN executions e ON e.tag = b.tag AND e.dataset_id = b.dataset_id;
```

---

## 总结

### 核心改进

1. **✅ 脚本解耦**：脚本信息存储在 `execution_config` 中，不作为关键字段
2. **✅ 关系清晰**：数据 → 执行结果 → 批次，每层职责单一
3. **✅ 避免重复**：`UNIQUE(instance_id, tag)` 保证数据唯一性
4. **✅ 灵活追加**：批次通过 `batch_executions` 关联多次执行
5. **✅ 实时统计**：批次统计通过 SQL 实时计算，无需维护冗余字段

### 关注点

**你关注的**：
- ✅ 任务的成功/失败 → `execution_results.status`
- ✅ 批次的正确率 → 实时计算自 `execution_results`

**不关注的**：
- ❌ 用什么脚本 → 存储在 `execution_config` 仅供参考
- ❌ 脚本如何执行 → 系统内部实现细节

### 下一步

1. **实现新的数据库 schema**
2. **更新 API 接口**（`/api/v1/executions` 替代 `/api/v1/task-groups`）
3. **更新规则文档**（反映新的数据模型）
4. **提供迁移脚本**（从旧表迁移到新表）

---

**版本**: v1.0  
**更新日期**: 2026-05-14
