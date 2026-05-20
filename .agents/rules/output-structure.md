# 输出目录结构规范

本文档定义当前 DUCC worker 能正确解析的任务输出目录结构。

## 核心规则

worker 传给脚本的 `--output-dir` 已经是单个任务的输出目录，例如：

```text
data/outputs/<batch_name>_<batch_id>/tasks/<safe_instance_id>
```

脚本必须把 DUCC 需要解析的文件直接写到这个目录根部：

```text
<output-dir>/task_summary.json
<output-dir>/extracted_patch.diff
<output-dir>/execution_trace.jsonl
<output-dir>/validation_detail.json
```

不要再创建一层 `tasks/<safe_instance_id>/task_summary.json` 作为 DUCC 主输出；那是旧文档/外部工具常见布局，当前 worker 不会从那里解析主结果。

## 标准目录结构

```text
<output-dir>/
├── input_instance.json        # worker 生成，脚本输入
├── task_summary.json          # 必需，worker 解析任务结果
├── extracted_patch.diff       # 推荐，生成补丁
├── execution_trace.jsonl      # 推荐，执行轨迹
├── validation_detail.json     # 推荐，验证详情
├── dataset_info.json          # 推荐，当前实例信息
├── stdout.log                 # 可选
├── stderr.log                 # 可选
└── external_raw/              # 可选，外部工具原始输出
```

## 必需输出：task_summary.json

路径：

```text
<output-dir>/task_summary.json
```

最小成功示例：

```json
{
  "instance_id": "django__django-11099",
  "status": "completed",
  "duration_seconds": 123.45,
  "patch_generated": true,
  "model": "Claude Sonnet 4.6",
  "tag": "baseline",
  "timestamp": "2026-05-19T10:30:00Z"
}
```

包含验证结果示例：

```json
{
  "instance_id": "django__django-11099",
  "status": "completed",
  "duration_seconds": 156.78,
  "patch_generated": true,
  "model": "Claude Sonnet 4.6",
  "tag": "baseline",
  "timestamp": "2026-05-19T10:30:00Z",
  "validation": {
    "success": false,
    "tests_passed": 8,
    "tests_failed": 2,
    "tests_total": 10,
    "error_message": null
  }
}
```

失败示例：

```json
{
  "instance_id": "matplotlib__matplotlib-24334",
  "status": "failed",
  "duration_seconds": 45.12,
  "patch_generated": false,
  "model": "Claude Sonnet 4.6",
  "tag": "baseline",
  "timestamp": "2026-05-19T10:35:00Z",
  "error": "Timeout after 1800 seconds"
}
```

字段说明：

| 字段 | 必需 | 说明 |
|------|------|------|
| `instance_id` | 是 | 实例 ID |
| `status` | 是 | `completed` 或 `failed` |
| `duration_seconds` | 是 | 执行耗时 |
| `patch_generated` | 推荐 | 是否生成补丁 |
| `model` | 推荐 | 批次模型 |
| `tag` | 推荐 | 批次标签 |
| `timestamp` | 推荐 | 完成时间 |
| `validation` | 可选 | 验证结果 |
| `error` / `error_message` | 失败时推荐 | 错误信息 |

## 推荐输出：extracted_patch.diff

路径：

```text
<output-dir>/extracted_patch.diff
```

用途：

- 前端查看生成补丁。
- 与数据集中的 Ground Truth `patch` 做对比。
- 下载或人工复核。

格式应为 unified diff。

## 推荐输出：execution_trace.jsonl

路径：

```text
<output-dir>/execution_trace.jsonl
```

每行一个 JSON 对象：

```jsonl
{"timestamp":"2026-05-19T10:28:30Z","action":"generation_start","model":"Claude Sonnet 4.6"}
{"timestamp":"2026-05-19T10:30:30Z","action":"generation_end","returncode":0}
```

## 推荐输出：validation_detail.json

路径：

```text
<output-dir>/validation_detail.json
```

用于保存比 `task_summary.validation` 更详细的测试或评测结果。SWE-bench 类任务可以放完整 evaluation JSON。

## 推荐输出：dataset_info.json

路径：

```text
<output-dir>/dataset_info.json
```

建议保存当前实例的 `data` 内容，方便离线排查，不需要重新查数据库。

## 外部工具输出

如果接入外部工具，其原始输出可以保留在：

```text
<output-dir>/external_raw/
```

例如：

```text
<output-dir>/external_raw/tasks/<safe_instance_id>/task_summary.json
<output-dir>/external_raw/predictions/<safe_instance_id>.json
<output-dir>/external_raw/all_preds.jsonl
```

但 wrapper 必须把 DUCC 关心的结果复制或转换到 `--output-dir` 根目录。

## worker 解析行为

当前 worker 会读取：

```text
<output-dir>/task_summary.json
<output-dir>/extracted_patch.diff
<output-dir>/execution_trace.jsonl
<output-dir>/validation_detail.json
```

如果 `task_summary.json` 缺失，任务虽然可能脚本退出 0，但系统无法拿到有效摘要。所有脚本都应保证成功或失败时都写出该文件。

## 路径安全

生成任务子目录时，系统会把实例 ID 中的 `/` 和 `:` 替换为 `_`。脚本不要依赖原始实例 ID 直接作为文件夹名；如果需要创建子目录，也应做同样的 safe name 处理。
