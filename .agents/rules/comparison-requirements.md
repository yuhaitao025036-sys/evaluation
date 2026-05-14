# 对比功能使用指南

本文档介绍 DUCC 评估系统的对比功能，帮助你从多个维度分析评估结果。

## 设计理念

- **多维度对比**：支持跨模型、跨标签、三向 diff、执行轨迹等多种对比
- **灵活组合**：可自由选择对比维度和筛选条件
- **可视化展示**：提供直观的 diff 对比界面
- **可追溯性**：保留完整的执行轨迹和日志

---

## 四种对比维度

### 1. 跨模型对比（Cross-Model Comparison）

**场景**：比较不同模型在相同任务上的表现

**示例**：对比 GPT-4 和 Claude 在同一个数据集、相同标签下的结果

```bash
# 创建两个任务组，使用不同模型
curl -X POST http://localhost:8000/api/v1/task-groups \
  -H "Content-Type: application/json" \
  -d '{
    "script_id": 1,
    "dataset_id": 1,
    "model": "gpt-4-turbo",
    "tag": "baseline"
  }'

curl -X POST http://localhost:8000/api/v1/task-groups \
  -H "Content-Type: application/json" \
  -d '{
    "script_id": 1,
    "dataset_id": 1,
    "model": "claude-3.5-sonnet",
    "tag": "baseline"
  }'
```

**对比查询**：

```bash
# 获取两个模型的结果统计
curl 'http://localhost:8000/api/v1/task-instances?dataset_id=1&tag=baseline&group_by=model'

# 响应示例
{
  "groups": [
    {
      "model": "gpt-4-turbo",
      "total": 731,
      "completed": 720,
      "failed": 11,
      "success_rate": 0.985,
      "validation_success_rate": 0.892
    },
    {
      "model": "claude-3.5-sonnet",
      "total": 731,
      "completed": 715,
      "failed": 16,
      "success_rate": 0.978,
      "validation_success_rate": 0.875
    }
  ]
}
```

**对比分析**：

1. **整体成功率对比**
   - GPT-4: 98.5% 完成率，89.2% 验证通过率
   - Claude: 97.8% 完成率，87.5% 验证通过率

2. **实例级别对比**
   ```bash
   # 查询特定实例在两个模型下的结果
   curl 'http://localhost:8000/api/v1/task-instances?instance_id=django__django-11099&tag=baseline'
   ```

3. **补丁对比**（见第 3 节：三向对比）

---

### 2. 跨标签对比（Cross-Label Comparison）

**场景**：比较同一模型在不同配置/实验下的表现

**示例**：对比 baseline 配置 vs 使用新 prompt 的实验配置

```bash
# Baseline 运行
curl -X POST http://localhost:8000/api/v1/task-groups \
  -H "Content-Type: application/json" \
  -d '{
    "script_id": 1,
    "dataset_id": 1,
    "model": "gpt-4-turbo",
    "tag": "baseline",
    "script_args": "--timeout 1800"
  }'

# 实验 1：使用新 prompt
curl -X POST http://localhost:8000/api/v1/task-groups \
  -H "Content-Type: application/json" \
  -d '{
    "script_id": 1,
    "dataset_id": 1,
    "model": "gpt-4-turbo",
    "tag": "experiment_new_prompt",
    "script_args": "--timeout 1800 --use-new-prompt"
  }'

# 实验 2：增加超时时间
curl -X POST http://localhost:8000/api/v1/task-groups \
  -H "Content-Type: application/json" \
  -d '{
    "script_id": 1,
    "dataset_id": 1,
    "model": "gpt-4-turbo",
    "tag": "experiment_longer_timeout",
    "script_args": "--timeout 3600"
  }'
```

**对比查询**：

```bash
# 按标签分组统计
curl 'http://localhost:8000/api/v1/task-instances?dataset_id=1&model=gpt-4-turbo&group_by=tag'

# 响应示例
{
  "groups": [
    {
      "tag": "baseline",
      "total": 731,
      "validation_success_rate": 0.892
    },
    {
      "tag": "experiment_new_prompt",
      "total": 731,
      "validation_success_rate": 0.915
    },
    {
      "tag": "experiment_longer_timeout",
      "total": 731,
      "validation_success_rate": 0.905
    }
  ]
}
```

**对比分析**：

| 标签 | 验证通过率 | 提升 |
|------|-----------|------|
| baseline | 89.2% | - |
| experiment_new_prompt | 91.5% | +2.3% ✅ |
| experiment_longer_timeout | 90.5% | +1.3% |

**结论**：新 prompt 提升效果最明显

---

### 3. 三向对比（Three-Way Comparison）

**场景**：对比 Ground Truth、生成的补丁、原始代码

**前提条件**：
- 数据集包含 `patch` 字段（Ground Truth）
- 脚本输出 `extracted_patch.diff`（生成的补丁）
- 数据集包含 `base_commit` 和 `repo`（可选，用于获取原始代码）

**对比维度**：

```
           ┌─────────────────┐
           │  Original Code  │
           │  (base_commit)  │
           └────────┬────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐       ┌──────────────┐
│ Ground Truth  │       │  Generated   │
│    Patch      │       │    Patch     │
│  (dataset)    │       │  (script)    │
└───────────────┘       └──────────────┘
```

**API 查询**：

```bash
# 获取三向对比数据
curl 'http://localhost:8000/api/v1/task-instances/django__django-11099/comparison?tag=baseline&model=gpt-4-turbo'

# 响应示例
{
  "instance_id": "django__django-11099",
  "repo": "django/django",
  "base_commit": "a3f4b7c9d2e1f6a8b0c3d4e5f6a7b8c9d0e1f2a3",
  
  "ground_truth_patch": "diff --git a/django/contrib/auth/views.py...",
  "generated_patch": "diff --git a/django/contrib/auth/views.py...",
  
  "comparison": {
    "identical": false,
    "similarity": 0.85,
    "files_modified": {
      "ground_truth": ["django/contrib/auth/views.py"],
      "generated": ["django/contrib/auth/views.py"],
      "common": ["django/contrib/auth/views.py"]
    },
    "diff_stats": {
      "ground_truth": {"additions": 5, "deletions": 2},
      "generated": {"additions": 7, "deletions": 2}
    }
  },
  
  "validation": {
    "success": true,
    "tests_passed": 10,
    "tests_failed": 0
  }
}
```

**Web UI 展示**：

系统前端提供三栏对比视图：

```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│   Ground Truth      │   Generated Patch   │   Original Code     │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ -    return old     │ -    return old     │     return old      │
│ +    return new     │ +    return new_v2  │                     │
│                     │ +    logging.info() │                     │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

**对比指标**：

1. **相似度**：基于编辑距离计算补丁相似度（0-1）
2. **文件覆盖**：Ground Truth 修改的文件，生成是否覆盖
3. **验证结果**：生成的补丁是否通过测试
4. **差异分析**：额外的修改、遗漏的修改

---

### 4. 执行轨迹对比（Execution Trace Comparison）

**场景**：比较不同运行的执行过程、时间消耗、操作序列

**前提条件**：
- 脚本输出 `execution_trace.jsonl`

**对比维度**：

1. **时间消耗对比**
2. **操作序列对比**
3. **LLM 调用对比**（tokens、调用次数）
4. **文件操作对比**（读取、修改的文件）

**API 查询**：

```bash
# 获取执行轨迹
curl 'http://localhost:8000/api/v1/task-instances/django__django-11099/trace?tag=baseline&model=gpt-4-turbo'

# 响应示例（解析 execution_trace.jsonl）
{
  "instance_id": "django__django-11099",
  "model": "gpt-4-turbo",
  "tag": "baseline",
  
  "summary": {
    "total_duration_seconds": 156.78,
    "total_steps": 8,
    "llm_calls": 3,
    "total_tokens": 12500,
    "files_read": 5,
    "files_modified": 1
  },
  
  "timeline": [
    {
      "timestamp": "2026-05-14T10:28:30.123Z",
      "step": 1,
      "action": "read_file",
      "target": "django/contrib/auth/views.py",
      "duration_ms": 45
    },
    {
      "timestamp": "2026-05-14T10:28:31.456Z",
      "step": 2,
      "action": "llm_call",
      "model": "gpt-4-turbo",
      "tokens": 3500,
      "duration_ms": 4100
    },
    {
      "timestamp": "2026-05-14T10:28:35.789Z",
      "step": 3,
      "action": "generate_patch",
      "duration_ms": 230
    }
  ]
}
```

**对比分析示例**：

| 维度 | GPT-4 (baseline) | GPT-4 (experiment) | Claude (baseline) |
|------|------------------|--------------------|--------------------|
| 总耗时 | 156.78s | 142.34s ⬇️ | 178.92s |
| LLM 调用次数 | 3 | 2 ⬇️ | 4 |
| 总 tokens | 12,500 | 9,800 ⬇️ | 15,200 |
| 读取文件数 | 5 | 4 | 6 |
| 修改文件数 | 1 | 1 | 1 |

**可视化展示**：

时间线图（Gantt Chart）：
```
GPT-4 baseline:    [====read===][======llm======][=patch=][===test===]
GPT-4 experiment:  [====read===][====llm====][=patch=][===test===]
Claude baseline:   [====read===][==llm==][=retry=][==llm==][=patch=][===test===]
```

---

## 组合对比示例

### 示例 1：多模型 × 多标签矩阵对比

**场景**：评估 2 个模型 × 3 个配置 = 6 个任务组

| 模型 / 标签 | baseline | experiment_1 | experiment_2 |
|------------|----------|--------------|--------------|
| GPT-4 | 89.2% | 91.5% | 90.5% |
| Claude | 87.5% | 89.8% | 88.2% |

**查询**：

```bash
# 获取矩阵数据
curl 'http://localhost:8000/api/v1/task-instances/matrix?dataset_id=1&models=gpt-4-turbo,claude-3.5-sonnet&tags=baseline,experiment_1,experiment_2'
```

**分析**：
- GPT-4 在 experiment_1 下表现最好（91.5%）
- Claude 整体低于 GPT-4，但 experiment_1 也有提升
- experiment_2 对两个模型都有轻微提升

---

### 示例 2：失败案例分析

**场景**：找出 GPT-4 失败但 Claude 成功的案例

```bash
# 查询失败案例
curl 'http://localhost:8000/api/v1/task-instances?dataset_id=1&tag=baseline&status=failed&model=gpt-4-turbo'

# 响应：instance_ids = ["django__django-11099", "matplotlib__matplotlib-24334", ...]

# 对比 Claude 在这些案例上的表现
curl 'http://localhost:8000/api/v1/task-instances?dataset_id=1&tag=baseline&model=claude-3.5-sonnet&instance_ids=django__django-11099,matplotlib__matplotlib-24334'
```

**分析结果**：
- django__django-11099：GPT-4 失败（超时），Claude 成功
- matplotlib__matplotlib-24334：GPT-4 失败（测试不通过），Claude 也失败

**深入分析**：
1. 下载两个模型的执行轨迹
2. 对比操作序列和时间消耗
3. 对比生成的补丁差异

---

## 数据下载和离线分析

### 下载任务组输出

```bash
# 下载整个任务组的输出（ZIP 压缩包）
curl -O http://localhost:8000/api/v1/task-groups/1/download

# 解压
unzip task-group-1-outputs.zip

# 目录结构
task-group-1-outputs/
├── report.json                          # 汇总报告
├── all_preds.jsonl                      # 所有预测结果
└── tasks/
    ├── django__django-11099/
    │   ├── task_summary.json
    │   ├── extracted_patch.diff
    │   ├── execution_trace.jsonl
    │   └── ...
    └── ...
```

### 离线对比脚本

```python
#!/usr/bin/env python3
"""
离线对比两个任务组的结果
"""
import json
import difflib
from pathlib import Path

def compare_task_groups(dir1, dir2):
    """对比两个任务组目录"""
    # 读取汇总报告
    report1 = json.load(open(Path(dir1) / 'report.json'))
    report2 = json.load(open(Path(dir2) / 'report.json'))
    
    print(f"Group 1: {report1['model']} ({report1['tag']})")
    print(f"  Success Rate: {report1['success_rate']:.2%}")
    print(f"  Validation Success Rate: {report1['validation_summary']['validation_success_rate']:.2%}")
    
    print(f"\nGroup 2: {report2['model']} ({report2['tag']})")
    print(f"  Success Rate: {report2['success_rate']:.2%}")
    print(f"  Validation Success Rate: {report2['validation_summary']['validation_success_rate']:.2%}")
    
    # 实例级别对比
    tasks1 = list(Path(dir1, 'tasks').iterdir())
    tasks2 = list(Path(dir2, 'tasks').iterdir())
    
    common_tasks = set(t.name for t in tasks1) & set(t.name for t in tasks2)
    print(f"\n共同实例数: {len(common_tasks)}")
    
    # 对比补丁
    for task_name in sorted(common_tasks)[:5]:  # 只展示前 5 个
        patch1_path = Path(dir1, 'tasks', task_name, 'extracted_patch.diff')
        patch2_path = Path(dir2, 'tasks', task_name, 'extracted_patch.diff')
        
        if patch1_path.exists() and patch2_path.exists():
            patch1 = patch1_path.read_text().splitlines()
            patch2 = patch2_path.read_text().splitlines()
            
            diff = list(difflib.unified_diff(patch1, patch2, lineterm=''))
            if diff:
                print(f"\n{task_name}: 补丁不同 ({len(diff)} 行差异)")
            else:
                print(f"\n{task_name}: 补丁相同 ✅")

# 使用
compare_task_groups(
    'task-group-1-outputs',
    'task-group-2-outputs'
)
```

---

## Web UI 对比功能

系统前端提供以下对比界面：

### 1. 仪表板（Dashboard）

- 任务组列表
- 成功率对比条形图
- 验证通过率趋势图

### 2. 实例对比页面

- 选择两个任务组
- 并排展示补丁 diff
- 执行轨迹时间线对比

### 3. 批量分析页面

- 失败案例聚合分析
- 按错误类型分组
- 导出报告

---

## 数据库查询示例

对于高级用户，可以直接查询数据库：

### 查询 1：跨模型成功率对比

```sql
SELECT 
    model,
    tag,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
    AVG(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as success_rate,
    AVG(CASE WHEN (result_data->'validation'->>'success')::boolean THEN 1 ELSE 0 END) as validation_success_rate
FROM task_instances
WHERE dataset_id = 1
GROUP BY model, tag
ORDER BY model, tag;
```

### 查询 2：找出 GPT-4 成功但 Claude 失败的案例

```sql
SELECT 
    gpt.instance_id,
    gpt.status as gpt_status,
    claude.status as claude_status,
    gpt.result_data->'validation'->>'success' as gpt_validated,
    claude.result_data->'validation'->>'success' as claude_validated
FROM task_instances gpt
JOIN task_instances claude 
    ON gpt.instance_id = claude.instance_id 
    AND gpt.dataset_id = claude.dataset_id
    AND gpt.tag = claude.tag
WHERE 
    gpt.dataset_id = 1 
    AND gpt.tag = 'baseline'
    AND gpt.model = 'gpt-4-turbo'
    AND claude.model = 'claude-3.5-sonnet'
    AND gpt.status = 'completed'
    AND claude.status = 'failed';
```

### 查询 3：执行时间对比

```sql
SELECT 
    model,
    tag,
    AVG(duration_seconds) as avg_duration,
    MIN(duration_seconds) as min_duration,
    MAX(duration_seconds) as max_duration,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_seconds) as median_duration
FROM task_instances
WHERE dataset_id = 1 AND status = 'completed'
GROUP BY model, tag;
```

---

## 最佳实践

### 1. 使用一致的标签命名

```bash
# 好的命名
baseline
experiment_new_prompt_v1
experiment_longer_timeout_3600s
ablation_no_context

# 不好的命名
test1
try_again
final_final_v2
```

### 2. 记录实验配置

在创建任务组时，在 `description` 中记录配置：

```bash
curl -X POST http://localhost:8000/api/v1/task-groups \
  -H "Content-Type: application/json" \
  -d '{
    "script_id": 1,
    "dataset_id": 1,
    "model": "gpt-4-turbo",
    "tag": "experiment_new_prompt",
    "description": "测试新 prompt：增加了代码上下文 + 示例，预期提升复杂问题的解决率",
    "script_args": "--use-new-prompt"
  }'
```

### 3. 定期下载备份

```bash
# 定期备份所有任务组
for id in $(seq 1 10); do
    curl -O "http://localhost:8000/api/v1/task-groups/$id/download"
done
```

### 4. 使用版本化数据集

```bash
# 数据集命名包含版本
SWE-Bench-v1.0-test-python
SWE-Bench-v1.1-test-python-filtered
```

---

## 常见问题

### Q: 如何对比超过两个任务组？
A: 使用矩阵查询 API 或下载所有输出进行离线分析。

### Q: 对比功能需要特殊配置吗？
A: 不需要，只要脚本按规范输出即可。推荐输出 `extracted_patch.diff` 和 `execution_trace.jsonl`。

### Q: 三向对比的 "原始代码" 如何获取？
A: 系统会根据 `repo` 和 `base_commit` 字段自动克隆仓库（未来功能）。目前仅对比两个补丁。

### Q: 如何对比执行轨迹？
A: 下载 `execution_trace.jsonl` 文件，使用自定义脚本分析。系统未来会提供内置的轨迹对比工具。

---

## 相关文档

- [脚本接口规范](script-interface.md)
- [数据集格式规范](dataset-format.md)
- [输出目录结构规范](output-structure.md)

---

**版本**: v1.0  
**更新日期**: 2026-05-14
