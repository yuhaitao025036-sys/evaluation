# 脚本接口规范

本文档定义了 DUCC 评估系统的脚本接口标准，所有评估脚本必须遵循此规范。

## 设计理念

- **单任务执行**：每次脚本调用只处理一个实例，系统负责任务调度和并发控制
- **约定优于配置**：通过标准化接口减少配置复杂度
- **完全解耦**：脚本独立于系统，可单独测试和运行
- **灵活扩展**：支持脚本自定义参数，满足不同评估需求

> **重要变更说明**：从 v2.0 开始，脚本不再负责循环处理数据范围，改为由系统调度单个任务。这使得系统可以实现细粒度的并发控制、失败重试和任务优先级管理。

---

## 必需参数（系统自动传递）

脚本**必须**支持以下命令行参数：

### `--instance-id <string>`
- **说明**：要处理的数据集实例 ID
- **类型**：字符串
- **示例**：`django__django-11099` 或 `requests__requests-1234`
- **用途**：脚本根据此 ID 从数据集中加载对应实例并处理
- **重要**：脚本每次只处理一个实例，不再使用索引范围

### `--output-dir <path>`
- **说明**：任务输出目录的完整路径
- **类型**：字符串
- **示例**：`/path/to/evaluation/data/outputs/batch_1/tasks/django__django-11099`
- **用途**：脚本将所有输出写入此目录
- **注意**：系统会为每个任务自动分配独立的输出目录

### `--model <string>`
- **说明**：使用的模型标识符
- **类型**：字符串
- **示例**：`gpt-4-turbo`、`claude-3.5-sonnet`
- **用途**：指定评估使用的 AI 模型

### `--tag <string>`
- **说明**：批次标签
- **类型**：字符串
- **示例**：`baseline`、`experiment_1`
- **用途**：用于区分不同实验配置

---

## 可选参数（用户自定义）

脚本可以定义自己的参数，通过批次创建时的 `execution_config` 传递：

### 推荐的标准可选参数

```bash
--timeout <int>           # 超时时间（秒），默认 1800
--use-tmux                # 启用 tmux 模式（可实时查看执行过程）
--validate                # 启用验证（运行测试）
--no-validate             # 禁用验证
--effort <string>         # 执行力度：low|medium|high
--temperature <float>     # 模型温度参数
```

### 示例：创建批次时传递自定义参数

```bash
curl -X POST http://localhost:8000/api/v1/batches \
  -H "Content-Type: application/json" \
  -d '{
    "batch_name": "baseline_run_1",
    "dataset_id": 1,
    "model": "gpt-4-turbo",
    "tag": "baseline",
    "execution_config": {
      "use_tmux": true,
      "timeout": 1800,
      "temperature": 0.7
    }
  }'
```

系统最终调用（针对每个实例）：
```bash
python script.py \
    --instance-id "django__django-11099" \
    --output-dir /path/to/outputs/batch_1/tasks/django__django-11099 \
    --model gpt-4-turbo \
    --tag baseline \
    --use-tmux --timeout 1800 --temperature 0.7
```

---

## 脚本约定规则

### 1. 可执行性
- 脚本必须是可执行的 Python 文件
- 文件开头包含 shebang：`#!/usr/bin/env python3`
- 设置执行权限：`chmod +x script.py`

### 2. 参数解析
```python
import argparse

parser = argparse.ArgumentParser(description='评估脚本')

# 必需参数
parser.add_argument('--instance-id', required=True, help='实例 ID')
parser.add_argument('--output-dir', required=True, help='输出目录')
parser.add_argument('--model', required=True, help='模型标识符')
parser.add_argument('--tag', required=True, help='批次标签')

# 自定义参数
parser.add_argument('--timeout', type=int, default=1800)
parser.add_argument('--use-tmux', action='store_true')

args = parser.parse_args()
```

### 3. 数据加载
脚本需要自行实现根据 `instance_id` 加载数据的逻辑：
```python
def load_instance_by_id(dataset_path, instance_id):
    """从数据集中加载指定实例"""
    import pandas as pd
    df = pd.read_parquet(dataset_path)
    instance = df[df['instance_id'] == instance_id]
    
    if instance.empty:
        raise ValueError(f"Instance {instance_id} not found")
    
    return instance.iloc[0].to_dict()
```

**注意**：数据集路径可以通过环境变量或配置文件传递，不再作为命令行参数。

### 4. 输出要求
- **所有输出必须写入** `--output-dir` 指定的目录
- **不要硬编码输出路径**
- 遵循[输出目录结构规范](output-structure.md)
- **必须输出** `task_summary.json` 文件（系统用于解析结果）

### 5. 错误处理
- 脚本执行成功时返回退出码 `0`
- 脚本执行失败时返回非零退出码
```python
import sys

try:
    # 执行评估
    result = evaluate(args)
    sys.exit(0)  # 成功
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)  # 失败
```

### 6. 进度报告
脚本应输出状态信息到 stdout，便于监控：
```python
print(f"Loading instance {instance_id}...")
print(f"Running model {model}...")
print(f"✓ Instance {instance_id} completed")
```

---

## 完整示例脚本模板

```python
#!/usr/bin/env python3
"""
评估脚本模板 - 单任务执行模式

遵循 DUCC 评估系统脚本接口规范 v2.0
"""
import argparse
import json
import os
import sys
from pathlib import Path

# 数据集路径配置（可通过环境变量或配置文件管理）
DATASET_BASE_PATH = os.getenv('DUCC_DATASET_PATH', '/path/to/datasets')

def load_instance_by_id(dataset_name, instance_id):
    """从数据集中加载指定实例"""
    import pandas as pd
    
    dataset_path = os.path.join(DATASET_BASE_PATH, f"{dataset_name}.parquet")
    df = pd.read_parquet(dataset_path)
    
    instance = df[df['instance_id'] == instance_id]
    if instance.empty:
        raise ValueError(f"Instance {instance_id} not found in {dataset_name}")
    
    return instance.iloc[0].to_dict()

def evaluate_instance(instance, args):
    """评估单个实例
    
    Args:
        instance: 数据集实例（字典格式）
        args: 命令行参数
        
    Returns:
        评估结果（字典格式）
    """
    instance_id = instance['instance_id']
    
    print(f"Evaluating instance: {instance_id}")
    print(f"Model: {args.model}")
    print(f"Tag: {args.tag}")
    
    # ========================================
    # 在这里实现你的评估逻辑
    # ========================================
    
    # 示例：调用 AI 模型生成补丁
    # patch = generate_patch(instance, args.model)
    # success = validate_patch(patch, instance)
    
    # 模拟评估结果
    result = {
        'instance_id': instance_id,
        'model': args.model,
        'tag': args.tag,
        'status': 'completed',
        'duration_seconds': 123.45,
        'patch_generated': True,
        'validation': {
            'success': True,
            'tests_passed': 10,
            'tests_failed': 0,
            'tests_total': 10
        }
    }
    
    return result

def save_outputs(result, output_dir):
    """保存评估输出
    
    必须保存的文件：
    - task_summary.json: 评估结果摘要（系统解析）
    
    推荐保存的文件：
    - extracted_patch.diff: 生成的补丁文件
    - execution_trace.jsonl: 执行过程记录
    - validation_detail.json: 详细的验证结果
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 必需：保存任务摘要
    summary_path = os.path.join(output_dir, 'task_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    # 2. 推荐：保存生成的补丁
    if result.get('patch_generated'):
        patch_path = os.path.join(output_dir, 'extracted_patch.diff')
        with open(patch_path, 'w') as f:
            f.write("# Patch content here\n")
    
    # 3. 推荐：保存验证详情
    validation_path = os.path.join(output_dir, 'validation_detail.json')
    with open(validation_path, 'w') as f:
        json.dump(result['validation'], f, indent=2)
    
    print(f"✓ Outputs saved to {output_dir}")

def main():
    parser = argparse.ArgumentParser(description='DUCC 评估脚本')
    
    # 必需参数（系统传递）
    parser.add_argument('--instance-id', required=True, help='实例 ID')
    parser.add_argument('--output-dir', required=True, help='输出目录')
    parser.add_argument('--model', required=True, help='模型标识符')
    parser.add_argument('--tag', required=True, help='批次标签')
    
    # 自定义参数
    parser.add_argument('--dataset', default='swebench-lite', help='数据集名称')
    parser.add_argument('--timeout', type=int, default=1800, help='超时时间（秒）')
    parser.add_argument('--use-tmux', action='store_true', help='使用 tmux 模式')
    
    args = parser.parse_args()
    
    try:
        print(f"=" * 60)
        print(f"DUCC Evaluation Script")
        print(f"Instance: {args.instance_id}")
        print(f"Model: {args.model}")
        print(f"Tag: {args.tag}")
        print(f"=" * 60)
        
        # 1. 加载数据集实例
        print(f"\n[1/3] Loading instance...")
        instance = load_instance_by_id(args.dataset, args.instance_id)
        print(f"✓ Instance loaded")
        
        # 2. 执行评估
        print(f"\n[2/3] Running evaluation...")
        result = evaluate_instance(instance, args)
        print(f"✓ Evaluation completed")
        
        # 3. 保存输出
        print(f"\n[3/3] Saving outputs...")
        save_outputs(result, args.output_dir)
        
        print(f"\n{'=' * 60}")
        print(f"✓ SUCCESS")
        print(f"Status: {result['status']}")
        print(f"Validation: {result['validation']['success']}")
        print(f"{'=' * 60}\n")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n{'=' * 60}")
        print(f"✗ FAILED")
        print(f"Error: {e}")
        print(f"{'=' * 60}\n")
        
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
```

---

## 测试脚本

在集成到系统之前，可以单独测试脚本：

```bash
# 测试单个实例
python my_script.py \
    --instance-id "django__django-11099" \
    --output-dir ./test_output \
    --model gpt-4-turbo \
    --tag baseline

# 检查输出
ls -R ./test_output/
cat ./test_output/task_summary.json
cat ./test_output/extracted_patch.diff
```

---

## 常见问题

### Q: 脚本如何知道数据集路径？
A: 有几种方式：
1. 通过环境变量设置基础路径：`export DUCC_DATASET_PATH=/path/to/datasets`
2. 在脚本内部配置文件中指定
3. 作为可选参数 `--dataset` 传递数据集名称，脚本组装完整路径

### Q: 为什么改用单任务执行而不是范围处理？
A: 单任务执行使系统可以：
- 实现细粒度并发控制（控制总并发数、批次并发数）
- 支持任务级别的失败重试
- 提供实时的任务状态更新
- 支持任务优先级调度
- 更好的资源管理和监控

### Q: 脚本可以访问网络吗？
A: 可以，脚本独立运行，没有网络限制。

### Q: 如何调试脚本？
A: 
1. 使用单个实例 ID 测试：`--instance-id "test-instance-1"`
2. 查看 stdout/stderr 输出
3. 检查输出目录的 `task_summary.json` 内容
4. 使用 `--use-tmux` 实时查看执行过程

### Q: 脚本执行失败会自动重试吗？
A: 是的，系统会根据批次配置的 `max_retries` 自动重试失败的任务。脚本本身无需处理重试逻辑。

---

## 从旧接口迁移

如果你有使用旧接口（v1.0）的脚本，需要进行以下修改：

### 参数变更

| 旧参数 | 新参数 | 说明 |
|--------|--------|------|
| `--dataset-path` | 移除 | 脚本内部管理数据集路径 |
| `--start-index` | 移除 | 不再循环处理 |
| `--end-index` | 移除 | 不再循环处理 |
| - | `--instance-id` | **新增**：指定要处理的实例 |
| - | `--model` | **新增**：模型标识符 |
| - | `--tag` | **新增**：批次标签 |

### 代码结构变更

**旧代码（v1.0）**：
```python
# 脚本负责循环
instances = load_dataset(args.dataset_path, args.start_index, args.end_index)
for instance in instances:
    result = evaluate(instance)
```

**新代码（v2.0）**：
```python
# 脚本只处理单个实例
instance = load_instance_by_id(args.instance_id)
result = evaluate(instance)
```

---

## 相关文档

- [数据集格式规范](dataset-format.md)
- [输出目录结构规范](output-structure.md)
- [对比功能使用指南](comparison-requirements.md)
- [任务调度与并发控制](task-scheduling-and-concurrency.md)
- [示例脚本](../../data/scripts/example_script.py)

---

**版本**: v2.0  
**更新日期**: 2026-05-14  
**重要变更**: 从范围处理模式改为单任务执行模式
