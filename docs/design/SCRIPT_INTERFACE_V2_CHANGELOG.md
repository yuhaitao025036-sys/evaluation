# 脚本接口 v2 当前实现说明

**更新日期**: 2026-05-19

## 核心变化

脚本接口已经从“脚本批量处理数据范围”调整为“DUCC 后端调度单实例任务”。

当前链路：

1. 数据集文件放到 `data/datasets`。
2. 扫描数据目录，只创建 `datasets` 文件元信息。
3. 导入实例，把每行写入 `dataset_instances.data`。
4. 创建批次时选择已导入实例。
5. worker 为每个 `BatchResult` 单独调用脚本。
6. worker 把当前实例写入 `input_instance.json`，并传给脚本。
7. 脚本把 `task_summary.json` 直接写到 `--output-dir`。

## 当前系统参数

worker 当前会调用：

```bash
python script.py \
  --instance-id <instance_id> \
  --instance-data-path <output_dir>/input_instance.json \
  --dataset-id <dataset_id> \
  --dataset-name <dataset_name> \
  --dataset-path <dataset_file_path> \
  --output-dir <task_output_dir> \
  --model <model> \
  --tag <tag> \
  [execution_config 参数]
```

脚本必须接收这些系统参数。其中：

- `--instance-data-path` 是推荐数据入口。
- `--dataset-path` 保留给 SWE-bench 等外部评测器使用。
- `--model` 当前主要是 Ducc Agent 模型，后续可映射到千帆等其他平台。

## 数据加载迁移

旧方式：

```python
df = pd.read_parquet(args.dataset_path)
instances = df.iloc[args.start_index:args.end_index]
```

当前推荐方式：

```python
import json

with open(args.instance_data_path, "r", encoding="utf-8") as f:
    payload = json.load(f)

instance = payload["data"]
```

## 输出迁移

旧文档曾描述：

```text
<output-dir>/tasks/<safe_instance_id>/task_summary.json
```

当前 worker 实际要求：

```text
<output-dir>/task_summary.json
```

因为 worker 传入的 `--output-dir` 已经是单个实例目录。

## 外部 batch 脚本迁移原则

外部脚本如果原来通过 `ids-file`、`parallel`、`run_batch.sh` 自己做批量调度，不能直接注册为 DUCC 脚本。

迁移方式：

1. 复制外部依赖到 `data/scripts/<runtime_dir>`，不移动原始目录。
2. 在 `data/scripts` 根目录新增 Python wrapper。
3. wrapper 接收 DUCC 系统参数。
4. wrapper 每次只处理一个 `--instance-id`。
5. wrapper 调用外部单实例入口。
6. wrapper 归一化输出到 `--output-dir` 根目录。

## SWE-bench Pro 映射

原命令：

```bash
bash run_batch_by_ids.sh \
  --ids-file ./ids/batch2_test_failed_only.txt \
  --model "Claude Sonnet 4.6" \
  --parallel 3 \
  --enable-eval \
  --dockerhub-username jefzda \
  --dataset-path /ssd1/Dejavu/datasets/SWE-bench_Pro/test-python.parquet \
  --scripts-dir ./SWE-bench_Pro-os/run_scripts
```

DUCC 映射：

```text
--ids-file              -> 批次 instance_ids
--model                 -> 批次 model
--parallel              -> 批次 max_concurrency / worker 并发
--enable-eval           -> wrapper 参数 enable-eval
--dockerhub-username    -> wrapper 参数 dockerhub-username
--dataset-path          -> 数据集扫描导入后由 worker 传入
--scripts-dir           -> wrapper 参数 scripts-dir
```

当前 wrapper：

```text
data/scripts/ducc_swebench_pro_wrapper.py
```

外部依赖目录：

```text
data/scripts/swe_bench_integrated_eval/
```

## 验证清单

```bash
python -m py_compile data/scripts/ducc_swebench_pro_wrapper.py
python data/scripts/ducc_swebench_pro_wrapper.py --help
python -m py_compile \
  data/scripts/swe_bench_integrated_eval/test_tmux_cc_experience.py \
  data/scripts/swe_bench_integrated_eval/evaluate_single_instance.py
```

通过 UI 或 API 扫描脚本后，确认根目录 wrapper 被注册，helper 目录中的脚本不作为独立脚本注册。
