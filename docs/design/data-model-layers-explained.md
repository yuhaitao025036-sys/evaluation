# 数据模型层次关系详解

## 问题：执行层是什么？

**简答**：`executions` 表记录的是**一次批量执行任务**（类似当前的 `task_groups`），不是单个数据的执行。

---

## 四层架构详解

### 层次关系

```
┌──────────────────────────────────────────────────────────┐
│ 统计层 (batches)                                          │
│ - 批次定义                                                │
│ - 用于聚合统计正确率                                       │
└───────────────────────┬──────────────────────────────────┘
                        │ N:M (通过 batch_executions)
                        │
┌───────────────────────▼──────────────────────────────────┐
│ 执行层 (executions)                                       │
│ - 一次批量执行任务的记录                                   │
│ - 例如：处理 100 个数据实例                                │
└───────────────────────┬──────────────────────────────────┘
                        │ 1:N
                        │
┌───────────────────────▼──────────────────────────────────┐
│ 结果层 (execution_results)                                │
│ - 每个数据实例的执行结果                                   │
│ - 例如：django__django-11099 在 baseline tag 下的结果     │
└───────────────────────┬──────────────────────────────────┘
                        │ N:1
                        │
┌───────────────────────▼──────────────────────────────────┐
│ 数据层 (dataset_instances)                                │
│ - 数据本身                                                │
│ - 例如：django__django-11099 的问题描述、patch 等         │
└──────────────────────────────────────────────────────────┘
```

---

## 详细说明

### 1️⃣ 数据层 (Dataset Instances)

**是什么**：静态数据，问题定义

**数量**：假设数据集有 731 个实例

**示例**：
```
dataset_instances 表:
├─ id=1, instance_id="django__django-11099", data={...}
├─ id=2, instance_id="django__django-11100", data={...}
├─ id=3, instance_id="matplotlib__matplotlib-24334", data={...}
└─ ... (共 731 条)
```

**特点**：
- ✅ 静态的，不会变化
- ✅ 一次导入，多次使用

---

### 2️⃣ 结果层 (Execution Results) ⭐️ 核心

**是什么**：每个数据实例的执行结果

**关系**：一个数据实例 + 一个 tag = 一个结果

**示例**：
```
execution_results 表:
├─ id=1:  instance_id="django__django-11099", tag="baseline", status="completed" ✓
├─ id=2:  instance_id="django__django-11100", tag="baseline", status="completed" ✓
├─ id=3:  instance_id="django__django-11101", tag="baseline", status="failed" ✗
├─ id=4:  instance_id="django__django-11099", tag="experiment_1", status="completed" ✓
└─ ... 

约束: UNIQUE(instance_id, tag)
```

**特点**：
- ✅ 一个数据可以有多个结果（不同 tag）
- ✅ 同一个数据 + 同一个 tag 只有一个最新结果
- ✅ 这是统计正确率的基础数据

**重要**：这是你关注的核心！

---

### 3️⃣ 执行层 (Executions)

**是什么**：一次批量执行任务的记录（类似 task_groups）

**关系**：一次执行 → 生成多个结果

**示例**：
```
executions 表:
├─ id=1: name="Baseline Run 1", start_index=0, end_index=100
│         → 生成 100 条 execution_results (id=1-100)
│
├─ id=2: name="Baseline Run 2", start_index=100, end_index=200
│         → 生成 100 条 execution_results (id=101-200)
│
└─ id=3: name="Experiment Run 1", start_index=0, end_index=50
          → 生成 50 条 execution_results (id=201-250)
```

**特点**：
- ✅ 记录一次批量执行任务
- ✅ 包含执行范围（start_index, end_index）
- ✅ 包含执行配置（model, tag, 脚本参数等）
- ✅ 一个 execution 生成多个 execution_results

**对比当前系统**：
```
executions 表 ≈ 当前的 task_groups + tasks 表
```

---

### 4️⃣ 统计层 (Batches)

**是什么**：批次定义，用于聚合统计

**关系**：一个批次可以包含多次执行

**示例**：
```
batches 表:
└─ id=1: batch_name="baseline", model="gpt-4-turbo", tag="baseline"

batch_executions 表 (关联表):
├─ batch_id=1, execution_id=1  # Baseline Run 1
├─ batch_id=1, execution_id=2  # Baseline Run 2
└─ batch_id=1, execution_id=5  # Baseline Run 3 (补充的)

查询批次统计:
SELECT COUNT(*) FROM execution_results er
JOIN executions e ON e.id = er.execution_id
JOIN batch_executions be ON be.execution_id = e.id
WHERE be.batch_id = 1;
→ 结果: 300 个实例的聚合统计
```

**特点**：
- ✅ 批次是统计单位
- ✅ 支持动态追加（关联多个 executions）
- ✅ 统计数据实时计算，不存储

---

## 数量关系示例

假设：
- 数据集有 **300 个实例**
- 创建 **3 次执行**
- 归属到 **1 个批次**

### 表记录数量

```
datasets: 1 条
└─ id=1, name="SWE-Bench-Test"

dataset_instances: 300 条
├─ instance_id="django__django-11099"
├─ instance_id="django__django-11100"
└─ ... (共 300 条)

executions: 3 条
├─ id=1: start_index=0, end_index=100    (处理 100 个数据)
├─ id=2: start_index=100, end_index=200  (处理 100 个数据)
└─ id=3: start_index=200, end_index=300  (处理 100 个数据)

execution_results: 300 条
├─ instance_id="django__django-11099", tag="baseline", execution_id=1
├─ instance_id="django__django-11100", tag="baseline", execution_id=1
├─ ... (100 条来自 execution_id=1)
├─ ... (100 条来自 execution_id=2)
└─ ... (100 条来自 execution_id=3)

batches: 1 条
└─ id=1, batch_name="baseline"

batch_executions: 3 条
├─ batch_id=1, execution_id=1
├─ batch_id=1, execution_id=2
└─ batch_id=1, execution_id=3
```

---

## 关键关系

### 关系 1: execution → execution_results (1:N)

**一次执行 → 多个结果**

```python
# 创建执行
execution = Execution(
    name="Baseline Run 1",
    start_index=0,
    end_index=100,
    model="gpt-4-turbo",
    tag="baseline"
)

# 执行完成后，生成 100 条结果
for i in range(0, 100):
    instance = dataset_instances[i]
    
    result = ExecutionResult(
        execution_id=execution.id,  # 关联到这次执行
        instance_id=instance.instance_id,
        tag=execution.tag,
        status="completed",
        validation_success=True,
        ...
    )
```

### 关系 2: batch → executions (N:M)

**一个批次 → 多次执行**

```python
# 创建批次
batch = Batch(
    batch_name="baseline",
    model="gpt-4-turbo",
    tag="baseline"
)

# 第一次执行
execution1 = Execution(start_index=0, end_index=100, ...)
batch_executions.add(batch_id=batch.id, execution_id=execution1.id)

# 追加：第二次执行
execution2 = Execution(start_index=100, end_index=200, ...)
batch_executions.add(batch_id=batch.id, execution_id=execution2.id)

# 批次统计（聚合两次执行的结果）
stats = query("""
    SELECT COUNT(*) as total
    FROM execution_results er
    JOIN executions e ON e.id = er.execution_id
    JOIN batch_executions be ON be.execution_id = e.id
    WHERE be.batch_id = ?
""", batch.id)
# → total = 200
```

---

## 你的关注点映射

根据你的需求：

> "理论上任务我关注的是任务的成功和失败，以及批次最后统计的正确率"

**映射到表**：

1. **任务的成功和失败**
   ```sql
   -- 查看每个数据实例的结果
   SELECT instance_id, status, validation_success
   FROM execution_results
   WHERE tag = 'baseline';
   ```

2. **批次的正确率统计**
   ```sql
   -- 查看批次整体正确率
   SELECT 
       COUNT(*) as total,
       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
       AVG(CASE WHEN validation_success THEN 1.0 ELSE 0.0 END) as success_rate
   FROM execution_results er
   JOIN executions e ON e.id = er.execution_id
   JOIN batch_executions be ON be.execution_id = e.id
   JOIN batches b ON b.id = be.batch_id
   WHERE b.batch_name = 'baseline';
   ```

**不需要关注**：
- ❌ 哪次 execution 产生的结果（只是中间过程）
- ❌ 用什么脚本执行的（存储在 execution_config 中供参考）

---

## API 使用示例

### 创建执行（用户视角）

```bash
POST /api/v1/executions
{
  "name": "Baseline Run 1",
  "batch_name": "baseline",
  
  "dataset_id": 1,
  "model": "gpt-4-turbo",
  "tag": "baseline",
  "start_index": 0,
  "end_index": 100
}

# 系统创建:
# 1. batch (如果不存在)
# 2. execution (记录这次执行)
# 3. 启动任务处理 100 个数据
# 4. 逐个写入 execution_results
# 5. 关联 batch_executions
```

### 查询批次正确率（用户视角）

```bash
GET /api/v1/batches/baseline/statistics

# 响应
{
  "batch_name": "baseline",
  "model": "gpt-4-turbo",
  "tag": "baseline",
  
  "statistics": {
    "total_instances": 100,    # 从 execution_results 聚合
    "completed": 92,            # 从 execution_results 聚合
    "failed": 8,                # 从 execution_results 聚合
    "success_rate": 0.92,
    "validation_success_rate": 0.87
  },
  
  "executions": [
    {"id": 1, "name": "Baseline Run 1", "instances": 100}
  ]
}
```

**注意**：用户不需要关心 `executions` 的细节，只关心最终统计结果。

---

## 总结

### ✅ 执行层 (executions) 的定义

**执行层是**：一次批量执行任务的记录（1 → N）

**不是**：单个数据的执行结果（那是 execution_results）

### ✅ 四层关系

```
1 个批次 (batches)
   ↓ 包含
N 个执行 (executions)  ← "执行层"，类似当前的 task_groups
   ↓ 每个生成
N 个结果 (execution_results)  ← 你关注的核心！每个数据的成功/失败
   ↓ 每个对应
1 个数据 (dataset_instances)
```

### ✅ 对应当前系统

```
executions          ≈ task_groups + tasks (合并简化)
execution_results   ≈ task_instances (改名，加约束)
batches            ≈ 新增（当前系统没有明确的批次表）
```

---

**版本**: v1.1  
**更新日期**: 2026-05-14  
**说明**: 补充 executions 层次关系详解
