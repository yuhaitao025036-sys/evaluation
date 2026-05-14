# 执行、批次、数据集关系详解

## 核心关系

```
┌──────────────┐
│   Dataset    │  用户选择：要在哪个数据集上执行
└──────┬───────┘
       │
       │ 用户指定 start_index, end_index
       │
       ▼
┌──────────────┐         ┌──────────────┐
│  Execution   │ 可选关联 │    Batch     │
│  (执行)      │◄────────│   (批次)     │
└──────┬───────┘         └──────────────┘
       │                        ▲
       │ 1:N                    │
       │                        │ 用户选择：
       ▼                        │ - 新建批次
┌──────────────┐                │ - 追加到现有批次
│ Execution    │                │ - 不关联批次
│ Results      │                │
└──────────────┘                │
                                │
                    ┌───────────┴──────────┐
                    │  batch_executions    │
                    │  (N:M 关联表)        │
                    └──────────────────────┘
```

---

## 用户的选择权

### 创建执行时，用户可以选择：

#### 1️⃣ 必选项

- ✅ **选择数据集** (`dataset_id`)
  - 在哪个数据集上执行
  
- ✅ **选择数据范围** (`start_index`, `end_index`)
  - 处理数据集的哪一部分
  
- ✅ **执行参数** (`model`, `tag`)
  - 使用什么模型
  - 打什么标签

#### 2️⃣ 可选项

- ❓ **是否关联批次** (`batch_name`)
  - 选项 A: 新建批次
  - 选项 B: 追加到现有批次
  - 选项 C: 不关联批次（临时执行）

---

## 详细场景

### 场景 1: 新建批次 + 第一次执行

```bash
POST /api/v1/executions
{
  "name": "Baseline Run 1",
  
  # 选择数据集和范围
  "dataset_id": 1,              # 选择 SWE-Bench 数据集
  "start_index": 0,
  "end_index": 100,             # 处理前 100 个数据
  
  # 执行参数
  "model": "gpt-4-turbo",
  "tag": "baseline",
  
  # 新建批次
  "batch_name": "baseline",
  "append_to_batch": false      # 或不提供此字段
}
```

**系统行为**：
```
1. 从 dataset (id=1) 中读取 instance[0:100]
2. 创建 batch (batch_name="baseline", model="gpt-4-turbo", tag="baseline")
3. 创建 execution (id=1, dataset_id=1, start_index=0, end_index=100)
4. 关联 batch_executions (batch_id=1, execution_id=1)
5. 执行任务，生成 100 条 execution_results
```

**结果**：
```
batches:
└─ id=1: batch_name="baseline"

executions:
└─ id=1: dataset_id=1, start_index=0, end_index=100

batch_executions:
└─ batch_id=1, execution_id=1

execution_results:
├─ instance_id="...", tag="baseline", execution_id=1
└─ ... (100 条)
```

---

### 场景 2: 追加到批次 + 第二次执行

```bash
POST /api/v1/executions
{
  "name": "Baseline Run 2",
  
  # 可以选择同一数据集的不同范围
  "dataset_id": 1,
  "start_index": 100,
  "end_index": 200,
  
  # 也可以选择不同数据集！
  # "dataset_id": 2,  # 例如另一个数据集的相同类型问题
  
  # 执行参数必须与批次一致
  "model": "gpt-4-turbo",       # 必须与批次的 model 一致
  "tag": "baseline",            # 必须与批次的 tag 一致
  
  # 追加到现有批次
  "batch_name": "baseline",
  "append_to_batch": true
}
```

**系统验证**：
```python
batch = get_batch(batch_name="baseline")
if batch.model != request.model:
    raise Error("Model mismatch")
if batch.tag != request.tag:
    raise Error("Tag mismatch")
```

**系统行为**：
```
1. 从 dataset (id=1) 中读取 instance[100:200]
2. 找到 batch (batch_name="baseline")
3. 验证 model 和 tag 是否一致
4. 创建 execution (id=2, dataset_id=1, start_index=100, end_index=200)
5. 关联 batch_executions (batch_id=1, execution_id=2)
6. 执行任务，生成 100 条 execution_results
```

**结果**：
```
batches:
└─ id=1: batch_name="baseline"

executions:
├─ id=1: dataset_id=1, start_index=0, end_index=100
└─ id=2: dataset_id=1, start_index=100, end_index=200

batch_executions:
├─ batch_id=1, execution_id=1
└─ batch_id=1, execution_id=2

execution_results:
├─ instance_id="...", tag="baseline", execution_id=1  (100 条)
└─ instance_id="...", tag="baseline", execution_id=2  (100 条)
```

---

### 场景 3: 不关联批次（临时执行）

```bash
POST /api/v1/executions
{
  "name": "Quick Test",
  
  # 选择数据集
  "dataset_id": 1,
  "start_index": 0,
  "end_index": 5,       # 只测试 5 个数据
  
  # 执行参数
  "model": "gpt-4-turbo",
  "tag": "test_run",
  
  # 不提供 batch_name - 不关联批次
}
```

**系统行为**：
```
1. 从 dataset (id=1) 中读取 instance[0:5]
2. 创建 execution (id=3, dataset_id=1, start_index=0, end_index=5)
3. 不创建/关联 batch
4. 执行任务，生成 5 条 execution_results
```

**结果**：
```
executions:
└─ id=3: dataset_id=1, start_index=0, end_index=5

execution_results:
├─ instance_id="...", tag="test_run", execution_id=3
└─ ... (5 条)

# 这些结果不属于任何批次
# 但可以后续通过 API 关联到批次（如果需要）
```

---

## 高级场景：跨数据集的批次

**问题**：一个批次可以包含来自不同数据集的执行吗？

**理论上可以，但不推荐**：

```bash
# Execution 1: 在 Python 数据集上执行
POST /api/v1/executions
{
  "dataset_id": 1,  # SWE-Bench-Python
  "batch_name": "baseline",
  "model": "gpt-4-turbo",
  "tag": "baseline"
}

# Execution 2: 在 Java 数据集上执行
POST /api/v1/executions
{
  "dataset_id": 2,  # SWE-Bench-Java
  "batch_name": "baseline",  # 同一批次名
  "model": "gpt-4-turbo",
  "tag": "baseline",
  "append_to_batch": true
}
```

**系统允许**，但**统计时要注意**：
```sql
SELECT 
    b.batch_name,
    e.dataset_id,
    COUNT(DISTINCT er.instance_id) as instances
FROM batches b
JOIN batch_executions be ON be.batch_id = b.id
JOIN executions e ON e.id = be.execution_id
JOIN execution_results er ON er.execution_id = e.id
WHERE b.batch_name = 'baseline'
GROUP BY b.batch_name, e.dataset_id;

# 结果:
# baseline, dataset_id=1, 100 instances
# baseline, dataset_id=2, 50 instances
```

**推荐做法**：
- ✅ 一个批次只包含同一数据集的执行
- ✅ 不同数据集使用不同批次名
  ```
  baseline_python
  baseline_java
  ```

---

## 数据库设计调整

基于你的理解，让我调整一下 `batches` 表的设计：

### 原设计（限制单一数据集）

```sql
CREATE TABLE batches (
    id SERIAL PRIMARY KEY,
    batch_name VARCHAR(200) UNIQUE NOT NULL,
    model VARCHAR(100) NOT NULL,
    tag VARCHAR(100) NOT NULL,
    dataset_id INTEGER REFERENCES datasets(id),  -- 限制数据集
    ...
);
```

### 优化设计（灵活支持）

```sql
CREATE TABLE batches (
    id SERIAL PRIMARY KEY,
    batch_name VARCHAR(200) UNIQUE NOT NULL,
    model VARCHAR(100) NOT NULL,
    tag VARCHAR(100) NOT NULL,
    -- 不限制 dataset_id，允许跨数据集（如果需要）
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**验证逻辑移到应用层**：
```python
def append_to_batch(batch_name, execution):
    batch = get_batch(batch_name)
    
    # 验证模型和 tag
    if batch.model != execution.model:
        raise ValueError("Model mismatch")
    if batch.tag != execution.tag:
        raise ValueError("Tag mismatch")
    
    # 可选：验证数据集是否一致（推荐但不强制）
    existing_datasets = get_batch_datasets(batch.id)
    if existing_datasets and execution.dataset_id not in existing_datasets:
        print(f"Warning: Adding different dataset to batch")
    
    # 关联执行到批次
    add_batch_execution(batch.id, execution.id)
```

---

## 总结

### ✅ 执行层的准确定义

**执行 (execution) 是**：
- 用户发起的一次批量任务
- 包含：数据集选择 + 数据范围选择 + 执行参数
- 可以选择关联到批次，也可以不关联

### ✅ 用户的选择

创建执行时：
1. **必选**：选择数据集 (`dataset_id`)
2. **必选**：选择数据范围 (`start_index`, `end_index`)
3. **必选**：执行参数 (`model`, `tag`)
4. **可选**：关联批次 (`batch_name`, `append_to_batch`)

### ✅ 批次的作用

批次是**统计单位**，不是执行单位：
- 一个批次可以包含多次执行
- 执行可以来自同一数据集的不同范围
- 执行也可以来自不同数据集（灵活但不推荐）
- 批次约束：model 和 tag 必须一致

### ✅ 灵活性

```
用户 → 选择数据集 → 选择范围 → 创建执行
                                    ↓
                            可选：关联到批次
```

这样设计既灵活又清晰！🎯

---

**版本**: v1.0  
**更新日期**: 2026-05-14
