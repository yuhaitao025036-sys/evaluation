# 输出目录结构规范

本文档定义了 DUCC 评估系统的输出目录结构标准，确保脚本输出能够被系统正确解析和展示。

## 设计理念

- **标准化结构**：统一的目录组织便于系统解析
- **可追溯性**：保留完整的执行轨迹和日志
- **可扩展性**：支持脚本自定义输出文件
- **人类可读**：目录结构清晰，便于人工检查

---

## 目录结构概览

```
<output-dir>/                    # 任务输出根目录（--output-dir 参数）
├── tasks/                       # 实例任务目录（必需）
│   ├── <safe_instance_id_1>/   # 单个实例的输出
│   │   ├── task_summary.json   # 【必需】任务摘要
│   │   ├── extracted_patch.diff # 【推荐】生成的补丁
│   │   ├── dataset_info.json   # 【推荐】实例元信息
│   │   ├── execution_trace.jsonl # 【推荐】执行轨迹
│   │   ├── validation_detail.json # 【推荐】验证详情
│   │   └── ...                 # 脚本自定义文件
│   ├── <safe_instance_id_2>/
│   │   └── ...
│   └── ...
├── report.json                  # 【推荐】汇总报告
├── all_preds.jsonl              # 【推荐】所有预测结果（单行）
└── ...                          # 脚本自定义输出

注：<safe_instance_id> = instance_id.replace('/', '_').replace(':', '_')
```

---

## 必需输出

### `tasks/<safe_instance_id>/task_summary.json`

**说明**：每个实例的任务摘要，系统会自动扫描此文件以更新任务状态。

**必需字段**：

```json
{
  "instance_id": "django__django-11099",
  "status": "completed",
  "duration_seconds": 123.45,
  "patch_generated": true,
  "model": "gpt-4-turbo",
  "timestamp": "2026-05-14T10:30:00Z"
}
```

#### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `instance_id` | string | ✅ | 实例唯一标识（与数据集中一致） |
| `status` | string | ✅ | 状态：`completed`（成功）或 `failed`（失败） |
| `duration_seconds` | number | ✅ | 执行耗时（秒），精确到小数点后 2 位 |
| `patch_generated` | boolean | ✅ | 是否成功生成补丁 |
| `model` | string | ✅ | 使用的模型标识（如 `gpt-4-turbo`） |
| `timestamp` | string | ✅ | 完成时间（ISO 8601 格式） |
| `validation` | object | ❌ | 验证结果（推荐，见下文） |
| `error` | string | ❌ | 错误信息（仅 `status=failed` 时） |

**完整示例**（包含推荐字段）：

```json
{
  "instance_id": "django__django-11099",
  "status": "completed",
  "duration_seconds": 156.78,
  "patch_generated": true,
  "model": "gpt-4-turbo",
  "timestamp": "2026-05-14T10:30:00Z",
  
  "validation": {
    "success": true,
    "tests_passed": 10,
    "tests_failed": 0,
    "tests_total": 10,
    "error_message": null
  },
  
  "metadata": {
    "agent_version": "1.2.0",
    "max_iterations": 5,
    "actual_iterations": 3,
    "tokens_used": 12500
  }
}
```

**失败示例**：

```json
{
  "instance_id": "matplotlib__matplotlib-24334",
  "status": "failed",
  "duration_seconds": 45.12,
  "patch_generated": false,
  "model": "gpt-4-turbo",
  "timestamp": "2026-05-14T10:35:00Z",
  "error": "Timeout after 1800 seconds"
}
```

---

## 推荐输出

### `tasks/<safe_instance_id>/extracted_patch.diff`

**说明**：生成的代码补丁（unified diff 格式）

**用途**：
- 对比功能（Ground Truth vs 生成）
- 人工审查
- 应用到代码仓库

**示例**：

```diff
diff --git a/django/contrib/auth/views.py b/django/contrib/auth/views.py
--- a/django/contrib/auth/views.py
+++ b/django/contrib/auth/views.py
@@ -45,7 +45,10 @@ class LoginView(FormView):
     def form_valid(self, form):
         """Security check complete. Log the user in."""
-        auth_login(self.request, form.get_user())
+        user = form.get_user()
+        if user is not None:
+            auth_login(self.request, user)
+        else:
+            return self.form_invalid(form)
         return HttpResponseRedirect(self.get_success_url())
```

---

### `tasks/<safe_instance_id>/dataset_info.json`

**说明**：实例的元信息（从数据集复制）

**用途**：
- 无需重新读取数据集即可查看问题描述
- 便于离线分析

**示例**：

```json
{
  "instance_id": "django__django-11099",
  "repo": "django/django",
  "base_commit": "a3f4b7c9d2e1f6a8b0c3d4e5f6a7b8c9d0e1f2a3",
  "problem_statement": "Fix authentication bug in Django sessions...",
  "patch": "diff --git a/django/contrib/auth/views.py...",
  "test_patch": "diff --git a/tests/auth_tests/test_views.py...",
  "repo_language": "Python"
}
```

---

### `tasks/<safe_instance_id>/execution_trace.jsonl`

**说明**：执行轨迹日志（每行一条记录）

**用途**：
- 追踪 AI Agent 的执行步骤
- 调试失败案例
- 分析时间消耗

**格式**：JSON Lines（每行独立的 JSON 对象）

**示例**：

```jsonl
{"timestamp": "2026-05-14T10:28:30.123Z", "step": 1, "action": "read_file", "target": "django/contrib/auth/views.py", "duration_ms": 45}
{"timestamp": "2026-05-14T10:28:31.456Z", "step": 2, "action": "analyze_code", "duration_ms": 1200}
{"timestamp": "2026-05-14T10:28:35.789Z", "step": 3, "action": "generate_patch", "model": "gpt-4-turbo", "tokens": 3500, "duration_ms": 4100}
{"timestamp": "2026-05-14T10:28:40.012Z", "step": 4, "action": "apply_patch", "success": true, "duration_ms": 230}
{"timestamp": "2026-05-14T10:28:55.678Z", "step": 5, "action": "run_tests", "tests_passed": 10, "tests_failed": 0, "duration_ms": 15600}
```

**推荐字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | string | ISO 8601 时间戳 |
| `step` | number | 步骤序号 |
| `action` | string | 操作类型（如 `read_file`, `run_command`, `llm_call`） |
| `target` | string | 操作目标（文件路径、命令等） |
| `duration_ms` | number | 耗时（毫秒） |
| `success` | boolean | 是否成功 |
| `error` | string | 错误信息（可选） |

---

### `tasks/<safe_instance_id>/validation_detail.json`

**说明**：详细的测试验证结果

**用途**：
- 查看具体哪些测试通过/失败
- 分析失败原因

**示例**：

```json
{
  "instance_id": "django__django-11099",
  "validation_success": true,
  "tests_total": 10,
  "tests_passed": 10,
  "tests_failed": 0,
  "tests_skipped": 0,
  "duration_seconds": 15.6,
  
  "test_results": [
    {
      "test_name": "test_login_with_valid_credentials",
      "status": "passed",
      "duration_seconds": 1.2
    },
    {
      "test_name": "test_login_with_invalid_credentials",
      "status": "passed",
      "duration_seconds": 0.8
    },
    {
      "test_name": "test_session_handling",
      "status": "passed",
      "duration_seconds": 2.3
    }
  ],
  
  "stdout": "...",
  "stderr": ""
}
```

---

### `report.json`（汇总报告）

**说明**：整个批次的汇总统计

**位置**：输出目录根目录

**示例**：

```json
{
  "task_group_id": 1,
  "batch_id": 1,
  "total_instances": 50,
  "completed": 48,
  "failed": 2,
  "success_rate": 0.96,
  
  "validation_summary": {
    "validated": 48,
    "validation_success": 45,
    "validation_failed": 3,
    "validation_success_rate": 0.9375
  },
  
  "performance": {
    "total_duration_seconds": 7823.45,
    "avg_duration_per_instance": 156.47,
    "min_duration": 45.12,
    "max_duration": 892.34
  },
  
  "model": "gpt-4-turbo",
  "tag": "baseline",
  "timestamp": "2026-05-14T12:00:00Z"
}
```

---

### `all_preds.jsonl`（所有预测结果）

**说明**：所有实例的预测结果（单行格式，便于追加）

**位置**：输出目录根目录

**用途**：
- 快速浏览所有结果
- 与其他系统集成（如 SWE-Bench 评估工具）

**示例**：

```jsonl
{"instance_id": "django__django-11099", "model_patch": "diff --git a/django/contrib/auth/views.py...", "model_name_or_path": "gpt-4-turbo"}
{"instance_id": "matplotlib__matplotlib-24334", "model_patch": "diff --git a/lib/matplotlib/axes/_axes.py...", "model_name_or_path": "gpt-4-turbo"}
```

---

## 自定义输出

脚本可以在实例目录下添加自定义文件，例如：

```
tasks/<safe_instance_id>/
├── task_summary.json           # 必需
├── extracted_patch.diff         # 推荐
├── execution_trace.jsonl        # 推荐
├── agent_logs.txt               # 自定义：Agent 日志
├── screenshots/                 # 自定义：截图
│   ├── step1.png
│   └── step2.png
├── intermediate_patches/        # 自定义：中间版本补丁
│   ├── iteration_1.diff
│   ├── iteration_2.diff
│   └── iteration_3.diff
└── debug_info.json              # 自定义：调试信息
```

**注意**：
- 自定义文件不会被系统自动解析
- 可通过文件下载功能获取
- 建议使用有意义的文件名和目录结构

---

## 系统如何处理输出

### 1. 任务完成后扫描

脚本执行完成后，系统会扫描输出目录：

```python
# 系统扫描逻辑（伪代码）
for instance_id in task_instances:
    safe_id = instance_id.replace('/', '_').replace(':', '_')
    summary_path = f"{output_dir}/tasks/{safe_id}/task_summary.json"
    
    if os.path.exists(summary_path):
        summary = json.load(open(summary_path))
        
        # 更新数据库
        update_task_instance(
            instance_id=summary['instance_id'],
            status=summary['status'],
            duration=summary['duration_seconds'],
            patch_generated=summary['patch_generated'],
            ...
        )
```

### 2. 对比功能数据准备

系统读取以下文件用于对比：

- `tasks/<safe_instance_id>/extracted_patch.diff` - 生成的补丁
- `tasks/<safe_instance_id>/dataset_info.json` - Ground Truth 补丁（`patch` 字段）
- `tasks/<safe_instance_id>/execution_trace.jsonl` - 执行轨迹

### 3. 下载功能

用户可以通过 API 下载整个输出目录或单个文件：

```bash
# 下载整个任务组的输出（ZIP 压缩包）
curl -O http://localhost:8000/api/v1/task-groups/1/download

# 解压后可查看所有文件
unzip task-group-1-outputs.zip
```

---

## 实现示例

### Python 脚本中的输出逻辑

```python
import json
import os
from datetime import datetime
from pathlib import Path

def save_task_output(output_dir, instance_id, result):
    """保存任务输出"""
    # 转换为安全文件名
    safe_id = instance_id.replace('/', '_').replace(':', '_')
    
    # 创建实例目录
    task_dir = Path(output_dir) / 'tasks' / safe_id
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 必需：保存 task_summary.json
    summary = {
        'instance_id': instance_id,
        'status': 'completed' if result.success else 'failed',
        'duration_seconds': round(result.duration, 2),
        'patch_generated': result.patch is not None,
        'model': result.model,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    }
    
    if result.validation:
        summary['validation'] = {
            'success': result.validation.success,
            'tests_passed': result.validation.tests_passed,
            'tests_failed': result.validation.tests_failed,
            'tests_total': result.validation.tests_total,
        }
    
    if not result.success:
        summary['error'] = result.error_message
    
    with open(task_dir / 'task_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    # 2. 推荐：保存生成的补丁
    if result.patch:
        with open(task_dir / 'extracted_patch.diff', 'w') as f:
            f.write(result.patch)
    
    # 3. 推荐：保存数据集信息
    with open(task_dir / 'dataset_info.json', 'w') as f:
        json.dump(result.dataset_info, f, indent=2)
    
    # 4. 推荐：保存执行轨迹
    if result.trace:
        with open(task_dir / 'execution_trace.jsonl', 'w') as f:
            for entry in result.trace:
                f.write(json.dumps(entry) + '\n')
    
    # 5. 推荐：保存验证详情
    if result.validation:
        with open(task_dir / 'validation_detail.json', 'w') as f:
            json.dump(result.validation.to_dict(), f, indent=2)
    
    print(f"✓ Saved outputs to {task_dir}")
```

### 生成汇总报告

```python
def generate_report(output_dir, results, model, tag):
    """生成汇总报告"""
    completed = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    validated = [r for r in completed if r.validation]
    validation_success = [r for r in validated if r.validation.success]
    
    report = {
        'total_instances': len(results),
        'completed': len(completed),
        'failed': len(failed),
        'success_rate': len(completed) / len(results) if results else 0,
        
        'validation_summary': {
            'validated': len(validated),
            'validation_success': len(validation_success),
            'validation_failed': len(validated) - len(validation_success),
            'validation_success_rate': len(validation_success) / len(validated) if validated else 0,
        },
        
        'performance': {
            'total_duration_seconds': sum(r.duration for r in results),
            'avg_duration_per_instance': sum(r.duration for r in results) / len(results) if results else 0,
            'min_duration': min(r.duration for r in results) if results else 0,
            'max_duration': max(r.duration for r in results) if results else 0,
        },
        
        'model': model,
        'tag': tag,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    }
    
    with open(Path(output_dir) / 'report.json', 'w') as f:
        json.dump(report, f, indent=2)
```

---

## 常见问题

### Q: 必须按照这个结构输出吗？
A: `task_summary.json` 是必需的，其他文件是推荐的。不输出推荐文件会导致某些功能不可用（如对比、下载轨迹）。

### Q: 可以添加更多自定义文件吗？
A: 可以，系统不会限制自定义文件，但只会解析标准文件。

### Q: 如何处理大文件（如日志）？
A: 建议使用压缩格式（.gz）或流式写入（.jsonl）。避免在 `task_summary.json` 中嵌入大量数据。

### Q: 如果实例处理失败，还需要输出 task_summary.json 吗？
A: 是的，失败时也要输出，将 `status` 设为 `"failed"` 并填写 `error` 字段。

### Q: 输出目录会被自动清理吗？
A: 不会。输出会永久保留，除非手动删除任务组。

---

## 相关文档

- [脚本接口规范](script-interface.md)
- [数据集格式规范](dataset-format.md)
- [对比功能使用指南](comparison-requirements.md)

---

**版本**: v1.0  
**更新日期**: 2026-05-14
