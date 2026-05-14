# DUCC 评估系统规范

本目录包含 DUCC 评估系统的接口规范。所有评估脚本和数据集必须遵循这些规范。

> **注意**：本目录只包含**规范文档**（添加脚本/数据集时需要遵守的约束）。  
> 系统设计文档请查看 [docs/design/](../../docs/design/)。

---

## 规范文件

### 1. **[script-interface.md](script-interface.md)** - 脚本接口规范 **v2.0** ⚡️ 

**适用于**：所有评估脚本

**约束内容**：
- ✅ 必需参数：`--instance-id`, `--output-dir`, `--model`, `--tag`
- ✅ 脚本只处理单个实例（不循环）
- ✅ 必须返回退出码：成功 0，失败非 0
- ✅ 必须输出 `task_summary.json`

**违反后果**：脚本无法被系统调用

**重大变更（v2.0）**：
- ✅ 使用 `--instance-id`（单任务执行）
- ❌ 移除 `--start-index` 和 `--end-index`（范围处理）
- 📖 迁移指南：[docs/design/SCRIPT_INTERFACE_V2_CHANGELOG.md](../../docs/design/SCRIPT_INTERFACE_V2_CHANGELOG.md)

---

### 2. **[dataset-format.md](dataset-format.md)** - 数据集格式规范

**适用于**：所有数据集文件

**约束内容**：
- ✅ 必需字段：`instance_id`（唯一标识符）
- 📝 推荐字段：`problem_statement`, `repo`, `base_commit`, `patch`, `test_patch`, `repo_language`
- ✅ 支持格式：Parquet（推荐）、CSV、JSON、JSONL

**违反后果**：数据集无法被系统加载或对比功能不可用

---

### 3. **[output-structure.md](output-structure.md)** - 输出目录结构规范

**适用于**：所有评估脚本的输出

**约束内容**：
- ✅ 必需文件：`task_summary.json`（包含 `instance_id`, `status`, `duration_seconds` 等字段）
- 📝 推荐文件：`extracted_patch.diff`, `execution_trace.jsonl`, `validation_detail.json`
- ✅ 输出位置：直接写入 `--output-dir`（系统已分配实例目录）

**违反后果**：系统无法解析结果或功能受限

---

### 4. **[comparison-requirements.md](comparison-requirements.md)** - 对比功能要求

**适用于**：需要使用对比功能的脚本和数据集

**约束内容**：
- 📝 数据集需包含：Ground Truth patch
- 📝 脚本需输出：`extracted_patch.diff`, `execution_trace.jsonl`
- 📝 支持 4 个对比维度：跨模型、跨标签、三方对比、执行轨迹

**违反后果**：对比功能不可用（不影响基础评估）

---

## 使用场景

### 场景 1：添加新的评估脚本

**必须遵守**：
1. ✅ [script-interface.md](script-interface.md) - 使用 v2.0 接口（单任务模式）
2. ✅ [output-structure.md](output-structure.md) - 输出 `task_summary.json`

**推荐遵守**：
- 📝 [comparison-requirements.md](comparison-requirements.md) - 输出推荐文件以启用对比功能

**参考模板**：
- [/data/scripts/example_script.py](../../data/scripts/example_script.py) - 完整示例
- [/data/scripts/ducc_swebench_adapter.py](../../data/scripts/ducc_swebench_adapter.py) - 适配器示例

---

### 场景 2：添加新的数据集

**必须遵守**：
1. ✅ [dataset-format.md](dataset-format.md) - 包含 `instance_id` 字段
2. ✅ 使用 Parquet 格式（推荐）或其他支持格式

**推荐遵守**：
- 📝 包含推荐字段（`problem_statement`, `patch` 等）
- 📝 添加 Ground Truth patch 以支持对比功能

---

### 场景 3：使用对比功能

**必须满足**：
1. ✅ 数据集遵循 [dataset-format.md](dataset-format.md)
2. ✅ 脚本输出遵循 [output-structure.md](output-structure.md)
3. ✅ 参考 [comparison-requirements.md](comparison-requirements.md) 确保输出完整

---

## 规范验证

在提交代码前，使用以下命令验证：

```bash
# 1. 验证脚本接口（v2.0）
python data/scripts/your_script.py --help
# 应该看到: --instance-id, --model, --tag (必需)
# 不应该看到: --start-index, --end-index (已移除)

# 2. 测试脚本单任务执行
python data/scripts/your_script.py \
    --instance-id "test-instance-1" \
    --output-dir /tmp/test_output \
    --model gpt-4-turbo \
    --tag test

# 3. 验证输出结构
ls /tmp/test_output/task_summary.json
cat /tmp/test_output/task_summary.json | jq '.instance_id, .status, .duration_seconds'

# 4. 验证数据集格式
python -c "
import pandas as pd
df = pd.read_parquet('data/datasets/your_dataset.parquet')
assert 'instance_id' in df.columns, 'Missing instance_id'
assert df['instance_id'].is_unique, 'instance_id not unique'
print(f'✓ Dataset valid: {len(df)} instances')
"
```

---

## 相关文档

### 开发文档
- **[docs/design/](../../docs/design/)** - 系统设计文档（数据模型、任务调度等）
- **[docs/user-guide/](../../docs/user-guide/)** - 使用文档（API 使用、批次操作等）

### 示例代码
- **[data/scripts/](../../data/scripts/)** - 脚本模板和示例

### 项目文档
- **[README.md](../../README.md)** - 项目整体说明

---

## 规范更新流程

规范文件的更新需要：

1. ✅ 更新规范文件内容
2. ✅ 更新本 README 的说明
3. ✅ 更新根目录 README.md 的链接
4. ✅ 通知所有开发者
5. ✅ 提供迁移指南（如有重大变更）

---

**重要提示**：

这些规范不是建议，而是系统正常运行的**必要条件**。违反规范会导致：
- ❌ 脚本无法被系统调用
- ❌ 数据集无法被系统加载
- ❌ 结果无法被系统解析
- ❌ 对比功能不可用

如有疑问，请查看 [docs/design/](../../docs/design/) 了解系统设计原理。
