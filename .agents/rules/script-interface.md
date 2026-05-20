# 脚本接口规范

本文档定义当前 DUCC 评估系统的脚本接口。所有被系统扫描和执行的评估脚本都必须遵循这个单实例接口。

## 设计原则

- **单实例执行**：worker 每次只调用脚本处理一个 `dataset_instances` 实例。
- **系统负责调度**：批次拆分、并发、重试和状态流转由 DUCC 后端负责，脚本不要再做批量调度。
- **显式输入**：worker 会把当前实例写成 JSON，并通过 `--instance-data-path` 传给脚本。
- **标准输出**：脚本必须把 `task_summary.json` 直接写到 `--output-dir` 根目录。
- **可扩展参数**：脚本自定义参数通过 `argparse.add_argument` 暴露，扫描后在批次创建页展示。

## 脚本位置与扫描

默认脚本目录：

```text
data/scripts
```

脚本扫描接口只扫描该目录下的直接 `.py` 文件，不递归扫描子目录。因此：

- 可运行入口脚本应放在 `data/scripts/*.py`。
- 依赖文件夹可以放在 `data/scripts/<helper_dir>/`，不会被注册成独立脚本。

扫描接口：

```http
POST /api/v1/scripts/scan
```

## 系统自动传入参数

脚本必须能接收以下参数：

```bash
--instance-id <string>
--instance-data-path <path>
--dataset-id <int>
--dataset-name <string>
--dataset-path <path>
--output-dir <path>
--model <string>
--tag <string>
```

说明：

| 参数 | 说明 |
|------|------|
| `--instance-id` | 当前实例 ID |
| `--instance-data-path` | worker 生成的当前实例 JSON 文件 |
| `--dataset-id` | 数据集数据库 ID |
| `--dataset-name` | 数据集名称 |
| `--dataset-path` | 原始数据集文件路径，供外部评测器使用 |
| `--output-dir` | 当前任务输出目录，已是单实例目录 |
| `--model` | 批次选择的模型，当前主要来自 Ducc Agent，后续可映射到千帆等平台模型 |
| `--tag` | 批次标签，用于区分实验 |

这些系统参数会被 `backend/app/utils/script_argument_parser.py` 过滤，不会展示为用户可配置参数。

## 推荐参数解析模板

```python
import argparse

parser = argparse.ArgumentParser(description="DUCC evaluation script")

parser.add_argument("--instance-id", required=True)
parser.add_argument("--instance-data-path")
parser.add_argument("--dataset-id")
parser.add_argument("--dataset-name")
parser.add_argument("--dataset-path")
parser.add_argument("--output-dir", required=True)
parser.add_argument("--model", required=True)
parser.add_argument("--tag", required=True)

# 用户可配置参数
parser.add_argument("--timeout", type=int, default=1800)
parser.add_argument("--enable-eval", action="store_true")

args = parser.parse_args()
```

## 数据加载规范

推荐优先读取 `--instance-data-path`：

```python
import json

with open(args.instance_data_path, "r", encoding="utf-8") as f:
    payload = json.load(f)

instance = payload["data"]
```

`input_instance.json` 结构：

```json
{
  "dataset_id": 1,
  "dataset_name": "swe_bench_pro_test_python",
  "dataset_file_path": "/path/to/dataset.parquet",
  "dataset_instance_id": 123,
  "instance_id": "django__django-11099",
  "data": {
    "instance_id": "django__django-11099",
    "problem_statement": "..."
  }
}
```

如果接入外部评测器确实需要全量数据集文件，可以使用 `--dataset-path`，但不要在普通脚本中自行扫描整个数据集来决定处理范围。

## 自定义参数

脚本可以定义自己的参数，例如：

```python
parser.add_argument("--timeout", type=int, default=1800, help="执行超时时间")
parser.add_argument("--use-tmux", action="store_true", help="启用 tmux 模式")
parser.add_argument("--dockerhub-username", help="Docker Hub 用户名")
```

系统扫描脚本后会提取这些参数并在批次创建页展示。批次创建时填写的值会通过 `execution_config` 传给脚本。

## 输出规范

worker 传入的 `--output-dir` 已经是当前任务目录。脚本必须直接写：

```text
<output-dir>/task_summary.json
```

推荐同时写：

```text
<output-dir>/extracted_patch.diff
<output-dir>/execution_trace.jsonl
<output-dir>/validation_detail.json
<output-dir>/dataset_info.json
```

不要把必需文件写到额外的 `tasks/<instance_id>/` 子目录。外部工具自己的原始输出可以放到：

```text
<output-dir>/external_raw/
```

但脚本或 wrapper 必须把 DUCC 需要解析的文件归一化到 `--output-dir` 根目录。

## `task_summary.json` 最小结构

```json
{
  "instance_id": "django__django-11099",
  "model": "Claude Sonnet 4.6",
  "tag": "baseline",
  "status": "completed",
  "duration_seconds": 123.45,
  "patch_generated": true,
  "timestamp": "2026-05-19T10:30:00Z",
  "validation": {
    "success": true,
    "tests_passed": 10,
    "tests_failed": 0,
    "tests_total": 10,
    "error_message": null
  }
}
```

失败时：

```json
{
  "instance_id": "django__django-11099",
  "model": "Claude Sonnet 4.6",
  "tag": "baseline",
  "status": "failed",
  "duration_seconds": 60.0,
  "patch_generated": false,
  "timestamp": "2026-05-19T10:30:00Z",
  "error": "clear error message"
}
```

脚本退出码规则：

- 基础设施或脚本执行失败：非 0。
- 正常生成结果但评测未通过：建议退出 0，并在 `validation.success=false` 中表达未通过。
- 如果 wrapper 调用外部评测器，不能只用外部评测器退出码判断 DUCC 任务失败；应解析评测结果。

## 外部评测器 wrapper 规范

如果接入已有工程（例如 SWE-bench Pro），不要直接把外部 batch shell 注册成 DUCC 脚本。正确方式：

1. 把外部运行依赖复制到 `data/scripts/<external_runtime>/`，不要移动原始目录。
2. 在 `data/scripts` 根目录新增一个 DUCC wrapper `.py`。
3. wrapper 每次只处理当前 `--instance-id`。
4. wrapper 调用外部单实例脚本。
5. wrapper 把外部输出复制/转换为 DUCC 输出规范。

SWE-bench Pro 示例入口：

```text
data/scripts/ducc_swebench_pro_wrapper.py
```

旧命令映射：

```text
run_batch_by_ids.sh --ids-file       -> DUCC 批次 instance_ids
run_batch_by_ids.sh --parallel       -> DUCC 批次/worker 并发
run_batch_by_ids.sh --model          -> DUCC 批次 model
run_batch_by_ids.sh --enable-eval    -> wrapper 参数 --enable-eval
run_batch_by_ids.sh --dataset-path   -> DUCC dataset 扫描导入后由 worker 传 --dataset-path
run_batch_by_ids.sh --scripts-dir    -> wrapper 参数 --scripts-dir
```

## 单独测试脚本

```bash
python data/scripts/example_script.py \
  --instance-id "django__django-11099" \
  --instance-data-path ./test_output/input_instance.json \
  --dataset-id 1 \
  --dataset-name swe_bench_pro_test_python \
  --dataset-path ./data/datasets/swe_bench_pro_test_python.parquet \
  --output-dir ./test_output \
  --model "Claude Sonnet 4.6" \
  --tag smoke
```

检查：

```bash
python -m json.tool ./test_output/task_summary.json
ls ./test_output
```

## 迁移旧脚本

旧脚本需要做这些修改：

1. 移除 `--start-index` / `--end-index` / `--ids-file` 等批量处理入口。
2. 增加并接收所有系统参数。
3. 从 `--instance-data-path` 读取当前实例。
4. 每次只处理一个实例。
5. 把 `task_summary.json` 直接写到 `--output-dir`。
6. 把并发控制交给 DUCC，不要在脚本里再启动自己的批量并发。

## 相关文件

- `backend/app/workers/task_worker.py`
- `backend/app/utils/script_argument_parser.py`
- `data/scripts/example_script.py`
- `data/scripts/ducc_swebench_pro_wrapper.py`
- `.agents/rules/dataset-format.md`
- `.agents/rules/output-structure.md`
