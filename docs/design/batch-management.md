# 批次管理规范

## 批次（Batch）的概念

批次是 DUCC 评估系统中用于**数据聚合和统计**的核心单位。

### 核心特点

1. **数据聚合单位**
   - 批次内的所有任务结果会被聚合统计
   - 用于计算整体正确率、成功率等指标
   - 支持绘制批次级别的统计图表

2. **支持动态追加**
   - 同一批次可以多次追加新数据
   - 每次追加的数据会与批次现有数据合并统计
   - 无需一次性跑完所有数据

3. **模型一致性约束**
   - 同一批次内**应该使用相同的模型**
   - 同一批次内**应该使用相同的 tag（标签）**
   - 保证批次内数据的可比性

4. **批次间对比**
   - 不同批次可以对比（如 baseline vs experiment_1）
   - 每个批次有独立的统计指标
   - 支持多维度对比分析

---

## 批次的典型使用场景

### 场景 1：Baseline 批次的渐进式构建

```bash
# 第一次：创建 baseline 批次，跑 100 个实例
curl -X POST http://localhost:8000/api/v1/task-groups \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Baseline Run 1",
    "batch_name": "baseline",
    "dataset_id": 1,
    "script_id": 1,
    "model": "gpt-4-turbo",
    "tag": "baseline",
    "start_index": 0,
    "end_index": 100
  }'

# 第二次：追加到 baseline 批次，再跑 100 个实例
curl -X POST http://localhost:8000/api/v1/task-groups \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Baseline Run 2",
    "batch_name": "baseline",          # 使用相同的 batch_name
    "dataset_id": 1,
    "script_id": 1,
    "model": "gpt-4-turbo",              # 模型必须一致
    "tag": "baseline",                   # tag 必须一致
    "start_index": 100,
    "end_index": 200,
    "append_to_batch": true              # 标记为追加模式
  }'

# 第三次：继续追加
curl -X POST http://localhost:8000/api/v1/task-groups \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Baseline Run 3",
    "batch_name": "baseline",
    "dataset_id": 1,
    "script_id": 1,
    "model": "gpt-4-turbo",
    "tag": "baseline",
    "start_index": 200,
    "end_index": 300,
    "append_to_batch": true
  }'
```

**结果**：
- 批次 "baseline" 包含 300 个实例的结果
- 统计时会自动聚合所有追加的数据
- 可以实时查看批次的整体正确率

---

### 场景 2：对比不同批次

```bash
# 创建 experiment_1 批次
curl -X POST http://localhost:8000/api/v1/task-groups \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Experiment New Prompt Run 1",
    "batch_name": "experiment_new_prompt",
    "dataset_id": 1,
    "script_id": 1,
    "model": "gpt-4-turbo",
    "tag": "experiment_new_prompt",
    "start_index": 0,
    "end_index": 100,
    "script_args": "--use-new-prompt"
  }'

# 对比两个批次
curl -X POST http://localhost:8000/api/v1/comparisons/compare-batches \
  -H "Content-Type: application/json" \
  -d '{
    "batch_names": ["baseline", "experiment_new_prompt"],
    "dataset_id": 1
  }'

# 响应示例
{
  "batches": [
    {
      "batch_name": "baseline",
      "model": "gpt-4-turbo",
      "tag": "baseline",
      "total_instances": 300,
      "success_rate": 0.892,
      "validation_success_rate": 0.875
    },
    {
      "batch_name": "experiment_new_prompt",
      "model": "gpt-4-turbo",
      "tag": "experiment_new_prompt",
      "total_instances": 100,
      "success_rate": 0.915,
      "validation_success_rate": 0.905
    }
  ]
}
```

---

### 场景 3：新建 vs 追加的选择

**何时新建批次：**
- ✅ 更换模型（GPT-4 → Claude）
- ✅ 更换配置（baseline → experiment）
- ✅ 想要独立统计一组新实验
- ✅ 想要对比不同方案

**何时追加到现有批次：**
- ✅ 模型相同、配置相同
- ✅ 想要扩大批次的数据量
- ✅ 之前的运行因为某些原因中断
- ✅ 逐步积累数据，动态监控正确率变化

---

## 批次管理的 API

### 创建新批次

```bash
POST /api/v1/task-groups
{
  "batch_name": "baseline",          # 批次名称（必需）
  "append_to_batch": false,          # 新建批次（默认）
  "model": "gpt-4-turbo",            # 模型（必需）
  "tag": "baseline",                 # 标签（必需）
  ...
}
```

### 追加到现有批次

```bash
POST /api/v1/task-groups
{
  "batch_name": "baseline",          # 使用现有批次名称
  "append_to_batch": true,           # 追加模式
  "model": "gpt-4-turbo",            # 必须与批次现有模型一致
  "tag": "baseline",                 # 必须与批次现有 tag 一致
  ...
}
```

**系统验证**：
- ✅ 检查 batch_name 是否存在
- ✅ 验证 model 是否与批次现有模型一致
- ✅ 验证 tag 是否与批次现有 tag 一致
- ✅ 防止数据范围重叠（可选）

### 查询批次统计

```bash
GET /api/v1/batches/{batch_name}/statistics

# 响应
{
  "batch_name": "baseline",
  "model": "gpt-4-turbo",
  "tag": "baseline",
  "created_at": "2026-05-14T10:00:00Z",
  "last_updated": "2026-05-14T15:30:00Z",
  
  "task_groups": [
    {"id": 1, "name": "Baseline Run 1", "instances": 100},
    {"id": 3, "name": "Baseline Run 2", "instances": 100},
    {"id": 5, "name": "Baseline Run 3", "instances": 100}
  ],
  
  "aggregated_statistics": {
    "total_instances": 300,
    "completed": 290,
    "failed": 10,
    "success_rate": 0.9667,
    
    "validation": {
      "validated": 290,
      "validation_success": 254,
      "validation_failed": 36,
      "validation_success_rate": 0.8759
    },
    
    "performance": {
      "avg_duration_seconds": 156.78,
      "total_duration_seconds": 45468.0
    }
  }
}
```

### 列出所有批次

```bash
GET /api/v1/batches

# 响应
{
  "batches": [
    {
      "batch_name": "baseline",
      "model": "gpt-4-turbo",
      "tag": "baseline",
      "total_instances": 300,
      "success_rate": 0.8759
    },
    {
      "batch_name": "experiment_new_prompt",
      "model": "gpt-4-turbo",
      "tag": "experiment_new_prompt",
      "total_instances": 150,
      "success_rate": 0.9053
    }
  ]
}
```

---

## 数据库设计建议

### 方案 1：使用 task_groups 表的 batch_name 字段

```sql
-- 在 task_groups 表中添加 batch_name 字段
ALTER TABLE task_groups 
ADD COLUMN batch_name VARCHAR(200),
ADD COLUMN append_to_batch BOOLEAN DEFAULT FALSE;

-- 查询批次统计
SELECT 
    batch_name,
    model,
    tag,
    COUNT(DISTINCT id) as task_group_count,
    SUM(total_instances) as total_instances,
    AVG(success_rate) as avg_success_rate
FROM task_groups
WHERE batch_name = 'baseline'
GROUP BY batch_name, model, tag;
```

### 方案 2：创建独立的 batches 表（推荐）

```sql
-- 创建 batches 表
CREATE TABLE batches (
    id SERIAL PRIMARY KEY,
    batch_name VARCHAR(200) UNIQUE NOT NULL,
    model VARCHAR(100) NOT NULL,
    tag VARCHAR(100) NOT NULL,
    dataset_id INTEGER REFERENCES datasets(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 聚合统计（实时更新）
    total_instances INTEGER DEFAULT 0,
    completed_instances INTEGER DEFAULT 0,
    failed_instances INTEGER DEFAULT 0,
    success_rate DECIMAL(5,4),
    validation_success_rate DECIMAL(5,4),
    
    CONSTRAINT unique_batch_model_tag UNIQUE (batch_name, model, tag)
);

-- task_groups 表关联 batch
ALTER TABLE task_groups 
ADD COLUMN batch_id INTEGER REFERENCES batches(id);

-- 查询批次统计
SELECT 
    b.*,
    COUNT(tg.id) as task_group_count
FROM batches b
LEFT JOIN task_groups tg ON tg.batch_id = b.id
WHERE b.batch_name = 'baseline'
GROUP BY b.id;
```

---

## 批次追加的实现逻辑

### 后端服务逻辑

```python
# backend/app/services/batch_service.py

class BatchService:
    def create_or_append_task_group(self, request: TaskGroupCreate):
        """创建任务组，支持批次追加"""
        
        if request.append_to_batch:
            # 追加模式：查找现有批次
            batch = self.get_batch_by_name(request.batch_name)
            
            if not batch:
                raise ValueError(f"Batch '{request.batch_name}' not found")
            
            # 验证模型和 tag 一致性
            if batch.model != request.model:
                raise ValueError(
                    f"Model mismatch: batch uses '{batch.model}', "
                    f"but request specifies '{request.model}'"
                )
            
            if batch.tag != request.tag:
                raise ValueError(
                    f"Tag mismatch: batch uses '{batch.tag}', "
                    f"but request specifies '{request.tag}'"
                )
            
            # 创建任务组并关联到批次
            task_group = self.create_task_group(request)
            task_group.batch_id = batch.id
            
            # 更新批次统计
            self.update_batch_statistics(batch.id)
            
        else:
            # 新建模式：创建新批次
            batch = self.create_batch(
                batch_name=request.batch_name,
                model=request.model,
                tag=request.tag,
                dataset_id=request.dataset_id
            )
            
            task_group = self.create_task_group(request)
            task_group.batch_id = batch.id
        
        return task_group
    
    def update_batch_statistics(self, batch_id: int):
        """更新批次的聚合统计"""
        
        # 聚合所有关联 task_groups 的统计
        stats = db.query(
            func.sum(TaskGroup.total_instances).label('total'),
            func.sum(TaskGroup.completed_instances).label('completed'),
            func.sum(TaskGroup.failed_instances).label('failed'),
        ).filter(TaskGroup.batch_id == batch_id).first()
        
        # 更新批次表
        batch = db.query(Batch).get(batch_id)
        batch.total_instances = stats.total
        batch.completed_instances = stats.completed
        batch.failed_instances = stats.failed
        batch.success_rate = stats.completed / stats.total if stats.total else 0
        batch.updated_at = datetime.utcnow()
        
        db.commit()
```

---

## 前端 UI 设计建议

### 创建任务组时的批次选择

```
┌─────────────────────────────────────────────┐
│  创建任务组                                 │
├─────────────────────────────────────────────┤
│                                             │
│  批次管理：                                 │
│  ○ 新建批次                                 │
│     批次名称: [baseline_____________]       │
│                                             │
│  ● 追加到现有批次                           │
│     选择批次: [baseline ▼]                  │
│                                             │
│     批次信息:                               │
│     - 模型: gpt-4-turbo                     │
│     - 标签: baseline                        │
│     - 已有实例: 300                         │
│     - 成功率: 87.59%                        │
│                                             │
│  ⚠️  追加模式下，模型和标签必须与批次一致   │
│                                             │
│  模型: [gpt-4-turbo ▼]                      │
│  标签: [baseline_______________]            │
│                                             │
│  [取消]  [创建任务组]                       │
└─────────────────────────────────────────────┘
```

### 批次统计页面

```
┌─────────────────────────────────────────────────────────┐
│  批次列表                                    [刷新] [对比]│
├─────────────────────────────────────────────────────────┤
│                                                         │
│  baseline (gpt-4-turbo)                      87.59% ✓  │
│  ├─ 总实例: 300 | 成功: 263 | 失败: 37               │
│  ├─ 任务组 1: Baseline Run 1 (100 实例)              │
│  ├─ 任务组 2: Baseline Run 2 (100 实例)              │
│  └─ 任务组 3: Baseline Run 3 (100 实例)              │
│      [查看详情] [追加数据] [导出结果]                 │
│                                                         │
│  experiment_new_prompt (gpt-4-turbo)         90.53% ✓  │
│  ├─ 总实例: 150 | 成功: 136 | 失败: 14               │
│  ├─ 任务组 4: Experiment Run 1 (100 实例)            │
│  └─ 任务组 5: Experiment Run 2 (50 实例)             │
│      [查看详情] [追加数据] [导出结果]                 │
│                                                         │
│  experiment_longer_timeout (gpt-4-turbo)     89.23% ✓  │
│  └─ 总实例: 65 | 成功: 58 | 失败: 7                  │
│      [查看详情] [追加数据] [导出结果]                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 批次追加的最佳实践

### ✅ 推荐做法

1. **清晰的批次命名**
   ```
   baseline
   baseline_v2
   experiment_new_prompt
   experiment_longer_timeout
   ablation_no_context
   ```

2. **保持模型和 tag 一致**
   - 同一批次内使用相同的模型
   - 同一批次内使用相同的 tag
   - 便于统计和对比

3. **记录追加历史**
   - 在任务组名称中标注批次序号
   - 例如：`Baseline Run 1`, `Baseline Run 2`

4. **渐进式数据积累**
   - 先跑少量数据验证脚本正确性
   - 确认无误后追加更多数据
   - 实时监控批次的整体正确率

### ❌ 避免的做法

1. **混合不同模型**
   ```bash
   # 不推荐：批次内模型不一致
   batch_name: "baseline"
   Run 1: model="gpt-4-turbo"
   Run 2: model="claude-3.5-sonnet"  # 应该新建批次
   ```

2. **数据范围重叠**
   ```bash
   # 可能导致重复统计
   Run 1: start_index=0, end_index=100
   Run 2: start_index=50, end_index=150  # 50-100 重叠
   ```

3. **批次名称重复使用**
   ```bash
   # 不推荐：删除旧批次后重用名称
   # 可能导致统计混乱
   ```

---

## 相关规则

- [脚本接口规范](script-interface.md)
- [数据集格式规范](dataset-format.md)
- [输出目录结构规范](output-structure.md)
- [对比功能要求](comparison-requirements.md)

---

**版本**: v1.0  
**更新日期**: 2026-05-14
