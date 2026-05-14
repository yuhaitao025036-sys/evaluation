# 脚本接口 v2.0 变更说明

**更新日期**: 2026-05-14  
**变更类型**: 重大架构变更（Breaking Changes）

## 概述

脚本接口从 v1.0（范围处理模式）升级到 v2.0（单任务执行模式），以支持系统级任务调度和细粒度并发控制。

## 为什么要改？

### v1.0 的问题

在 v1.0 中，脚本负责循环处理数据范围：

```python
# v1.0 模式
for i in range(args.start_index, args.end_index):
    instance = dataset[i]
    process(instance)
```

这导致以下问题：

1. **无法控制并发**：脚本内部循环意味着系统无法控制总并发数
2. **重试困难**：某个实例失败需要重跑整个范围
3. **状态难追踪**：无法实时知道哪些实例正在运行、哪些已完成
4. **资源管理差**：无法动态调整资源分配或暂停/恢复任务
5. **优先级不支持**：无法为重要任务分配更高优先级

### v2.0 的优势

在 v2.0 中，系统调度单个任务：

```python
# v2.0 模式
instance = load_instance_by_id(args.instance_id)
result = process(instance)
```

优势：

1. ✅ **细粒度并发控制**：系统控制全局并发数和批次并发数
2. ✅ **失败重试**：单个任务失败自动重试，不影响其他任务
3. ✅ **实时状态**：每个任务状态独立追踪（pending/queued/running/completed/failed）
4. ✅ **暂停/恢复**：可以暂停批次、优先处理重要任务
5. ✅ **资源优化**：Worker 池动态管理，资源利用率更高
6. ✅ **任务优先级**：支持批次级和任务级优先级

---

## 参数变更详情

### 移除的参数

| 参数 | 说明 | 替代方案 |
|------|------|----------|
| `--dataset-path` | 数据集文件路径 | 脚本内部通过环境变量或配置管理 |
| `--start-index` | 起始索引 | 系统调度，脚本无需知道 |
| `--end-index` | 结束索引 | 系统调度，脚本无需知道 |

### 新增的必需参数

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `--instance-id` | string | 要处理的实例 ID | `django__django-11099` |
| `--model` | string | 模型标识符 | `gpt-4-turbo` |
| `--tag` | string | 批次标签 | `baseline` |

### 保留的参数

| 参数 | 说明 | 无变化 |
|------|------|--------|
| `--output-dir` | 输出目录 | ✅ 保留 |

---

## 代码迁移指南

### 1. 参数解析变更

**旧代码（v1.0）**：
```python
parser.add_argument('--dataset-path', required=True)
parser.add_argument('--output-dir', required=True)
parser.add_argument('--start-index', type=int, default=0)
parser.add_argument('--end-index', type=int)
parser.add_argument('--model', default='gpt-4-turbo')  # 可选
```

**新代码（v2.0）**：
```python
parser.add_argument('--instance-id', required=True)     # ⭐️ 新增
parser.add_argument('--output-dir', required=True)
parser.add_argument('--model', required=True)           # ⭐️ 必需
parser.add_argument('--tag', required=True)             # ⭐️ 新增
```

### 2. 数据加载变更

**旧代码（v1.0）**：
```python
def load_dataset(dataset_path, start_index, end_index):
    import pandas as pd
    df = pd.read_parquet(dataset_path)
    return df.iloc[start_index:end_index].to_dict('records')

instances = load_dataset(args.dataset_path, args.start_index, args.end_index)
```

**新代码（v2.0）**：
```python
# 数据集路径通过环境变量管理
DATASET_BASE_PATH = os.getenv('DUCC_DATASET_PATH', '/path/to/datasets')

def load_instance_by_id(dataset_name, instance_id):
    import pandas as pd
    dataset_path = os.path.join(DATASET_BASE_PATH, f"{dataset_name}.parquet")
    df = pd.read_parquet(dataset_path)
    instance = df[df['instance_id'] == instance_id]
    
    if instance.empty:
        raise ValueError(f"Instance {instance_id} not found")
    
    return instance.iloc[0].to_dict()

# 只加载一个实例
instance = load_instance_by_id('swebench-lite', args.instance_id)
```

### 3. 主逻辑变更

**旧代码（v1.0）**：
```python
def main():
    args = parser.parse_args()
    
    # 加载数据集
    instances = load_dataset(args.dataset_path, args.start_index, args.end_index)
    
    # 循环处理
    results = []
    for instance in instances:
        result = evaluate(instance)
        results.append(result)
    
    # 生成汇总报告
    generate_report(results)
```

**新代码（v2.0）**：
```python
def main():
    args = parser.parse_args()
    
    # 加载单个实例
    instance = load_instance_by_id(args.dataset, args.instance_id)
    
    # 处理单个实例
    result = evaluate(instance, args)
    
    # 保存结果（无需汇总，系统负责聚合）
    save_outputs(result, args.output_dir)
```

### 4. 输出变更

**旧代码（v1.0）**：
```python
# 输出到 tasks/<safe_id>/ 子目录
task_dir = os.path.join(args.output_dir, 'tasks', safe_id)
os.makedirs(task_dir, exist_ok=True)

# 生成汇总报告
with open(os.path.join(args.output_dir, 'report.json'), 'w') as f:
    json.dump(report, f)
```

**新代码（v2.0）**：
```python
# 直接输出到 output_dir（系统已分配实例目录）
os.makedirs(args.output_dir, exist_ok=True)

# 只保存单个任务结果，无需汇总报告
with open(os.path.join(args.output_dir, 'task_summary.json'), 'w') as f:
    json.dump(summary, f)
```

---

## 完整迁移示例

### 迁移前（v1.0）

```python
#!/usr/bin/env python3
import argparse
import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset-path', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--start-index', type=int, default=0)
    parser.add_argument('--end-index', type=int)
    parser.add_argument('--model', default='gpt-4-turbo')
    args = parser.parse_args()
    
    # 加载数据集
    df = pd.read_parquet(args.dataset_path)
    instances = df.iloc[args.start_index:args.end_index].to_dict('records')
    
    # 循环处理
    for instance in instances:
        instance_id = instance['instance_id']
        result = evaluate(instance, args.model)
        save_result(result, args.output_dir, instance_id)
    
    print(f"Processed {len(instances)} instances")

if __name__ == '__main__':
    main()
```

### 迁移后（v2.0）

```python
#!/usr/bin/env python3
import argparse
import os
import pandas as pd

DATASET_BASE_PATH = os.getenv('DUCC_DATASET_PATH', '/path/to/datasets')

def load_instance_by_id(dataset_name, instance_id):
    dataset_path = os.path.join(DATASET_BASE_PATH, f"{dataset_name}.parquet")
    df = pd.read_parquet(dataset_path)
    instance = df[df['instance_id'] == instance_id]
    
    if instance.empty:
        raise ValueError(f"Instance {instance_id} not found")
    
    return instance.iloc[0].to_dict()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance-id', required=True)      # ⭐️ 改
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--model', required=True)            # ⭐️ 改
    parser.add_argument('--tag', required=True)              # ⭐️ 新增
    parser.add_argument('--dataset', default='swebench-lite')  # 可选
    args = parser.parse_args()
    
    # 加载单个实例
    instance = load_instance_by_id(args.dataset, args.instance_id)
    
    # 处理单个实例
    result = evaluate(instance, args.model)
    result['model'] = args.model
    result['tag'] = args.tag
    
    # 保存结果
    save_result(result, args.output_dir)
    
    print(f"Processed instance: {args.instance_id}")

if __name__ == '__main__':
    main()
```

---

## 常见问题

### Q1: 我的脚本需要处理 100 个实例，现在怎么调用？

**A**: 不需要自己循环调用。系统会自动为每个实例创建一个任务并调用你的脚本：

```bash
# v1.0（旧方式 - 一次调用处理 100 个）
python script.py --dataset-path data.parquet --start-index 0 --end-index 100

# v2.0（新方式 - 系统调用 100 次，每次处理 1 个）
# 系统自动执行：
python script.py --instance-id "instance-1" --model gpt-4 --tag baseline
python script.py --instance-id "instance-2" --model gpt-4 --tag baseline
...
python script.py --instance-id "instance-100" --model gpt-4 --tag baseline
```

### Q2: 如何控制并发数？

**A**: 在批次配置中设置 `max_concurrency`：

```bash
curl -X POST http://localhost:8000/api/v1/batches \
  -H "Content-Type: application/json" \
  -d '{
    "batch_name": "baseline_run_1",
    "dataset_id": 1,
    "model": "gpt-4-turbo",
    "tag": "baseline",
    "max_concurrency": 10
  }'
```

系统会确保最多同时运行 10 个任务。

### Q3: 数据集路径怎么传递？

**A**: 三种方式：

1. **环境变量（推荐）**：
   ```bash
   export DUCC_DATASET_PATH=/path/to/datasets
   ```

2. **配置文件**：
   ```python
   # config.py
   DATASET_BASE_PATH = '/path/to/datasets'
   ```

3. **可选参数**：
   ```python
   parser.add_argument('--dataset', default='swebench-lite')
   # 脚本内部组装：f"{DATASET_BASE_PATH}/{args.dataset}.parquet"
   ```

### Q4: 失败重试怎么配置？

**A**: 在批次创建时设置 `max_retries`：

```bash
curl -X POST http://localhost:8000/api/v1/batches \
  -H "Content-Type: application/json" \
  -d '{
    "batch_name": "baseline_run_1",
    "max_retries": 3
  }'
```

脚本无需处理重试逻辑，系统自动重试失败的任务。

### Q5: 我的旧脚本还能用吗？

**A**: 不能直接使用。需要按照本文档迁移：

1. 修改参数解析（移除 index 参数，添加 instance-id）
2. 移除循环逻辑
3. 修改数据加载为按 ID 查询
4. 修改输出路径（不再需要 tasks 子目录）

参考 `/data/scripts/example_script.py` 的 v2.0 模板。

---

## 相关文档

- **[script-interface.md](script-interface.md)** - v2.0 完整接口规范
- **[task-scheduling-and-concurrency.md](task-scheduling-and-concurrency.md)** - 任务调度机制说明
- **[simplified-data-model.md](simplified-data-model.md)** - 数据模型设计
- **[/data/scripts/example_script.py](../../data/scripts/example_script.py)** - v2.0 示例脚本

---

**重要提醒**：所有新脚本必须遵循 v2.0 规范。旧脚本需要尽快迁移，未来版本将不再兼容 v1.0 接口。
