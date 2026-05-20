# 数据集格式规范

本文档定义当前 DUCC 评估系统的数据集接入、扫描、导入和脚本消费规范。

## 设计原则

- **文件先落盘**：数据集文件先放到后端可访问的数据目录，不走浏览器上传。
- **扫描与导入分离**：扫描只登记文件元信息，导入实例才写入可调度的数据行。
- **实例是调度单位**：批次创建和 worker 执行都基于 `dataset_instances` 中的单个实例。
- **脚本优先消费实例 JSON**：worker 会把当前实例写成 `input_instance.json` 并传给脚本。

## 支持的文件格式

| 格式 | 扩展名 | 推荐场景 |
|------|--------|----------|
| Parquet | `.parquet` | 大规模评测数据，推荐 |
| CSV | `.csv` | 简单表格数据 |
| JSON | `.json` | JSON 数组数据 |
| JSON Lines | `.jsonl` | 每行一条 JSON 的数据 |

SWE-Bench / SWE-bench Pro 这类包含多行 patch、测试列表和长文本的数据集，优先使用 Parquet 或 JSONL。

## 数据集接入流程

### 1. 放入数据目录

将数据集文件放到后端配置的 `DATASETS_DIR`，默认是：

```text
data/datasets
```

示例：

```text
data/datasets/swe_bench_pro_test_python.parquet
```

### 2. 扫描数据目录

通过数据管理页点击“扫描数据目录”，或调用：

```http
POST /api/v1/datasets/scan
```

扫描只创建或更新 `datasets` 元信息：

- `name`
- `file_name`
- `file_path`
- `format`
- `file_size`
- `total_instances`
- `imported_instances = 0`

如果数据库中已经存在相同 `file_path` 的数据集，扫描会跳过，不重复插入。

### 3. 导入实例

扫描后还不能直接跑批次，必须导入实例：

```http
POST /api/v1/datasets/{dataset_id}/import
```

可选范围导入：

```http
POST /api/v1/datasets/{dataset_id}/import?start_index=0&end_index=100
```

导入会把每一行写入 `dataset_instances`：

- `dataset_id`：所属数据集
- `instance_id`：实例唯一 ID
- `repo_language`：从 `repo_language` 或 `language` 字段提取
- `data`：完整原始行，JSONB 存储

`(dataset_id, instance_id)` 有唯一约束，重复导入不会重复插入同一实例。

### 4. 创建批次

批次创建只从 `dataset_instances` 选择实例。未导入实例的数据集不能创建可执行批次。

支持的实例选择方式：

- 全部已导入实例
- 按 `start_index` / `end_index` 范围
- 按 `instance_ids` 精确列表
- 后端支持部分 JSON 条件过滤

## 必需字段

### `instance_id`

```json
{
  "instance_id": "django__django-11099"
}
```

要求：

- 在同一个数据集内唯一。
- 使用稳定、可读的字符串。
- 建议只包含字母、数字、下划线、短横线和双下划线。

当前导入实现如果缺失 `instance_id` 会回退为 `instance_{idx}`，但正式评测数据必须显式提供 `instance_id`，否则无法稳定通过 ID 追加、筛选和复现实验。

## 推荐字段

SWE-Bench / SWE-bench Pro 推荐包含：

```json
{
  "instance_id": "django__django-11099",
  "repo": "django/django",
  "base_commit": "a3f4b7c9d2e1f6a8b0c3d4e5f6a7b8c9d0e1f2a3",
  "problem_statement": "Fix authentication bug in sessions",
  "patch": "diff --git ...",
  "test_patch": "diff --git ...",
  "fail_to_pass": ["tests.test_x"],
  "pass_to_pass": ["tests.test_y"],
  "repo_language": "Python"
}
```

字段用途：

- `problem_statement`：展示任务背景，也是 agent 输入的重要内容。
- `patch`：Ground Truth 补丁，用于对比。
- `test_patch`：测试补丁，用于验证。
- `fail_to_pass` / `pass_to_pass`：SWE-bench 类评测器需要的测试集合。
- `repo` / `base_commit`：定位代码仓库和基准版本。
- `repo_language` / `language`：用于语言筛选和统计。

其他自定义字段会完整保存在 `dataset_instances.data` 中。

## 脚本如何获取数据

worker 执行每个任务前，会在任务输出目录生成：

```text
<input-output-dir>/input_instance.json
```

结构：

```json
{
  "dataset_id": 1,
  "dataset_name": "swe_bench_pro_test_python",
  "dataset_file_path": "/path/to/data/datasets/swe_bench_pro_test_python.parquet",
  "dataset_instance_id": 123,
  "instance_id": "django__django-11099",
  "data": {
    "instance_id": "django__django-11099",
    "problem_statement": "..."
  }
}
```

脚本会收到：

```bash
--instance-data-path <output-dir>/input_instance.json
--dataset-id 1
--dataset-name swe_bench_pro_test_python
--dataset-path /path/to/data/datasets/swe_bench_pro_test_python.parquet
```

推荐脚本优先读取 `--instance-data-path` 的 `data` 字段。只有外部评测器需要全量原始文件时，才使用 `--dataset-path`。

## SWE-bench Pro 接入建议

对于用户已有数据：

```text
/ssd1/Dejavu/datasets/SWE-bench_Pro/test-python.parquet
```

建议复制到：

```text
data/datasets/swe_bench_pro_test_python.parquet
```

然后按标准流程扫描、导入实例、创建批次。旧命令中的 `--ids-file` 应转换为 DUCC 批次的 `instance_ids`，不要再由脚本内部批量读取。

## 当前 API

```http
GET  /api/v1/datasets
GET  /api/v1/datasets/{dataset_id}
POST /api/v1/datasets/scan
POST /api/v1/datasets/{dataset_id}/import
GET  /api/v1/datasets/{dataset_id}/instances
```

当前不提供浏览器上传、在线编辑实例或删除实例接口。

## 最佳实践

1. 使用 Parquet 保存大规模评测数据。
2. 保证 `instance_id` 稳定且唯一。
3. 扫描后必须导入实例再创建批次。
4. 用 `instance_ids` 精确复现实验样本。
5. 脚本从 `--instance-data-path` 读取当前实例，避免自己重新扫描数据集。
6. 外部评测工具如果必须使用全量数据集，则通过 `--dataset-path` 获取。
