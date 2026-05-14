# 数据集格式规范

本文档定义了 DUCC 评估系统的数据集格式标准，确保数据集能够被系统正确加载和处理。

## 设计理念

- **灵活的模式**：使用 JSONB 存储，支持任意字段扩展
- **强类型核心**：instance_id 等核心字段强制要求
- **多格式支持**：支持主流数据科学格式
- **向后兼容**：可兼容现有 SWE-Bench 等标准数据集

---

## 支持的文件格式

DUCC 系统支持以下数据集格式：

| 格式 | 文件扩展名 | 推荐使用场景 | 性能 |
|------|-----------|-------------|------|
| Parquet | `.parquet` | 大规模数据集（推荐） | ⭐⭐⭐⭐⭐ |
| CSV | `.csv` | 小规模数据集、Excel 导出 | ⭐⭐⭐ |
| JSON | `.json` | 嵌套结构数据 | ⭐⭐ |
| JSON Lines | `.jsonl` | 流式处理、增量更新 | ⭐⭐⭐⭐ |

**推荐**: 优先使用 **Parquet** 格式（压缩率高、读取快、类型保留）

---

## 必需字段

所有数据集**必须**包含以下字段：

### `instance_id` (string)
- **说明**：实例的唯一标识符
- **类型**：字符串
- **要求**：
  - 在数据集内唯一
  - 不包含特殊字符（建议使用 `a-zA-Z0-9_-`）
  - 长度限制：1-200 字符
- **示例**：
  ```
  "django__django-11099"
  "matplotlib__matplotlib-24334"
  "test_instance_001"
  ```

---

## 推荐字段（用于对比功能）

为了启用[对比功能](comparison-requirements.md)，推荐包含以下字段：

### 对比所需的核心字段

#### `patch` (string)
- **说明**：Ground Truth 补丁（标准答案）
- **类型**：字符串（unified diff 格式）
- **用途**：三向对比（Ground Truth vs 生成 vs 原始代码）
- **示例**：
  ```diff
  diff --git a/file.py b/file.py
  --- a/file.py
  +++ b/file.py
  @@ -10,7 +10,7 @@
  -    return old_code
  +    return new_code
  ```

#### `problem_statement` (string)
- **说明**：问题描述或需求说明
- **类型**：字符串（纯文本或 Markdown）
- **用途**：展示任务背景、问题上下文

#### `repo` (string)
- **说明**：代码仓库标识（GitHub 仓库名）
- **类型**：字符串
- **格式**：`owner/repo`
- **示例**：`django/django`, `python/cpython`

#### `base_commit` (string)
- **说明**：基础提交 SHA（问题出现时的代码版本）
- **类型**：字符串（40 字符 Git SHA）
- **示例**：`a3f4b7c9d2e1f6a8b0c3d4e5f6a7b8c9d0e1f2a3`

#### `test_patch` (string)
- **说明**：测试补丁（用于验证生成的代码）
- **类型**：字符串（unified diff 格式）
- **用途**：自动验证功能

#### `repo_language` (string)
- **说明**：仓库主要编程语言
- **类型**：字符串
- **示例**：`Python`, `Java`, `JavaScript`

---

## 可选字段

根据评估需求，可以添加自定义字段：

```json
{
  "instance_id": "django__django-11099",
  "patch": "...",
  "problem_statement": "...",
  "repo": "django/django",
  "base_commit": "a3f4b7c...",
  
  // 自定义字段示例
  "difficulty": "hard",
  "created_at": "2024-03-15",
  "hints": ["Check the database connection", "Review cache settings"],
  "fail_to_pass": ["test_user_login", "test_session_handling"],
  "pass_to_pass": ["test_basic_auth"],
  "environment_setup_commit": "b4c5d6e...",
  "metadata": {
    "category": "authentication",
    "estimated_time_minutes": 30
  }
}
```

---

## 数据集示例

### Parquet 格式（推荐）

```python
import pandas as pd

data = [
    {
        'instance_id': 'django__django-11099',
        'repo': 'django/django',
        'base_commit': 'a3f4b7c9d2e1f6a8b0c3d4e5f6a7b8c9d0e1f2a3',
        'problem_statement': 'Fix authentication bug in sessions',
        'patch': 'diff --git a/django/contrib/auth/views.py...',
        'test_patch': 'diff --git a/tests/test_auth.py...',
        'repo_language': 'Python',
        'difficulty': 'medium'
    },
    {
        'instance_id': 'matplotlib__matplotlib-24334',
        'repo': 'matplotlib/matplotlib',
        'base_commit': 'b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3',
        'problem_statement': 'Improve plot rendering performance',
        'patch': 'diff --git a/lib/matplotlib/axes/_axes.py...',
        'test_patch': 'diff --git a/lib/matplotlib/tests/test_axes.py...',
        'repo_language': 'Python',
        'difficulty': 'hard'
    }
]

df = pd.DataFrame(data)
df.to_parquet('dataset.parquet', engine='pyarrow', index=False)
```

### JSON Lines 格式

```jsonl
{"instance_id": "django__django-11099", "repo": "django/django", "patch": "...", "problem_statement": "..."}
{"instance_id": "matplotlib__matplotlib-24334", "repo": "matplotlib/matplotlib", "patch": "...", "problem_statement": "..."}
```

### CSV 格式

```csv
instance_id,repo,base_commit,problem_statement,patch,test_patch,repo_language
django__django-11099,django/django,a3f4b7c...,Fix authentication bug,...,...,Python
matplotlib__matplotlib-24334,matplotlib/matplotlib,b4c5d6e...,Improve plot rendering,...,...,Python
```

**注意**：CSV 格式不适合存储多行文本（如 patch），建议用于简单数据集或使用转义。

---

## 数据集加载验证

### 上传前自检

```python
import pandas as pd

def validate_dataset(file_path):
    """验证数据集是否符合规范"""
    # 加载数据集
    if file_path.endswith('.parquet'):
        df = pd.read_parquet(file_path)
    elif file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith('.jsonl'):
        df = pd.read_json(file_path, lines=True)
    else:
        raise ValueError("Unsupported format")
    
    # 检查必需字段
    if 'instance_id' not in df.columns:
        raise ValueError("Missing required field: instance_id")
    
    # 检查唯一性
    if df['instance_id'].duplicated().any():
        duplicates = df[df['instance_id'].duplicated()]['instance_id'].tolist()
        raise ValueError(f"Duplicate instance_ids found: {duplicates}")
    
    # 检查推荐字段
    recommended = ['patch', 'problem_statement', 'repo', 'base_commit', 'test_patch']
    missing = [f for f in recommended if f not in df.columns]
    if missing:
        print(f"⚠️  Missing recommended fields: {missing}")
        print("   Comparison features may be limited")
    
    print(f"✓ Dataset validation passed")
    print(f"  - Total instances: {len(df)}")
    print(f"  - Fields: {list(df.columns)}")
    
    return True

# 使用示例
validate_dataset('/path/to/dataset.parquet')
```

### 系统加载时的处理

系统上传数据集时会执行以下操作：

1. **格式检测**：根据文件扩展名识别格式
2. **字段提取**：读取所有列名作为 `fields` 存储到数据库
3. **JSONB 存储**：将每行数据转换为 JSON 存储到 `data` 字段
4. **验证**：检查 `instance_id` 存在且唯一

---

## 数据集管理

### 上传数据集

```bash
# 使用 API 上传
curl -X POST http://localhost:8000/api/v1/datasets/upload \
  -F "file=@dataset.parquet" \
  -F "name=SWE-Bench-Test-Python" \
  -F "description=Python subset for testing"
```

### 查看数据集信息

```bash
# 列出所有数据集
curl http://localhost:8000/api/v1/datasets

# 查看单个数据集详情
curl http://localhost:8000/api/v1/datasets/1

# 响应示例
{
  "id": 1,
  "name": "SWE-Bench-Test-Python",
  "file_path": "/path/to/dataset.parquet",
  "total_count": 731,
  "fields": [
    "instance_id",
    "repo",
    "base_commit",
    "patch",
    "problem_statement",
    "test_patch",
    "repo_language"
  ],
  "created_at": "2026-05-14T10:00:00Z"
}
```

---

## 兼容性说明

### SWE-Bench 数据集

DUCC 系统完全兼容 [SWE-Bench](https://github.com/princeton-nlp/SWE-bench) 数据集格式：

```python
# 下载 SWE-Bench 数据集
from datasets import load_dataset

dataset = load_dataset("princeton-nlp/SWE-bench", split="test")
df = dataset.to_pandas()

# 直接保存为 Parquet 供 DUCC 使用
df.to_parquet('swe-bench-test.parquet', index=False)
```

SWE-Bench 包含的字段：
- ✅ `instance_id` - 必需
- ✅ `patch` - 推荐
- ✅ `problem_statement` - 推荐
- ✅ `repo` - 推荐
- ✅ `base_commit` - 推荐
- ✅ `test_patch` - 推荐
- ✅ 其他字段（`hints_text`, `fail_to_pass` 等）- 保留在 JSONB 中

---

## 常见问题

### Q: 数据集最大支持多少条记录？
A: 无硬性限制。系统支持批量处理（默认 50 条/批），大数据集会自动拆分。

### Q: 如何处理包含中文的数据集？
A: 使用 UTF-8 编码保存文件即可，系统完全支持 Unicode。

### Q: CSV 格式如何处理多行文本？
A: CSV 标准支持引号包裹的多行文本，但建议使用 Parquet 或 JSONL 格式。

### Q: 可以动态添加字段吗？
A: 可以。JSONB 存储支持灵活的字段结构，不同数据集可以有不同字段。

### Q: 如何处理大文件（>1GB）？
A: 建议使用 Parquet 格式（压缩高效）或将数据集拆分成多个文件分别上传。

---

## 最佳实践

1. **使用 Parquet 格式**：性能最佳，类型安全
2. **保留 Ground Truth**：`patch` 字段对对比功能至关重要
3. **语义化命名**：`instance_id` 使用有意义的名称（如 `repo__issue-number`）
4. **版本管理**：数据集名称包含版本号（如 `SWE-Bench-v1.2-test`）
5. **文档说明**：在 `description` 中说明数据集来源、用途、特殊字段含义

---

## 相关文档

- [脚本接口规范](script-interface.md)
- [输出目录结构规范](output-structure.md)
- [对比功能使用指南](comparison-requirements.md)

---

**版本**: v1.0  
**更新日期**: 2026-05-14
