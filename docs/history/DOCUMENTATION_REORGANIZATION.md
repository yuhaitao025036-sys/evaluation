# 文档目录重组说明

**日期**: 2026-05-14  
**原因**: 规范文档和设计文档混在一起，不利于区分使用场景

---

## 重组内容

### 1. 目录结构调整

**调整前**：
```
.agents/rules/  （混杂了规范和设计）
  - script-interface.md
  - dataset-format.md
  - output-structure.md
  - comparison-requirements.md
  - simplified-data-model.md           ← 设计文档
  - task-scheduling-and-concurrency.md ← 设计文档
  - batch-management.md                ← 设计文档
  - ...
```

**调整后**：
```
.agents/rules/  （只保留规范）
  - script-interface.md
  - dataset-format.md
  - output-structure.md
  - comparison-requirements.md
  - README.md

docs/
  ├── design/  （设计文档）
  │   ├── simplified-data-model.md
  │   ├── task-scheduling-and-concurrency.md
  │   ├── batch-management.md
  │   ├── SCRIPT_INTERFACE_V2_CHANGELOG.md
  │   ├── execution-batch-dataset-relationship.md
  │   ├── data-model-layers-explained.md
  │   ├── data-model-optimization.md
  │   └── README.md
  │
  └── user-guide/  （使用文档，待添加）
      └── README.md
```

---

## 文档分类

### 规范类 (`.agents/rules/`)

**目标用户**: 添加脚本/数据集的开发者  
**用途**: 强制约束，必须遵守

**文件**:
1. `script-interface.md` - 脚本接口规范 v2.0
2. `dataset-format.md` - 数据集格式规范
3. `output-structure.md` - 输出结构规范
4. `comparison-requirements.md` - 对比功能要求

**特点**:
- ✅ 定义"必须"和"推荐"的约束
- ✅ 违反规范会导致系统无法工作
- ✅ 提供验证命令和示例

---

### 设计类 (`docs/design/`)

**目标用户**: 开发系统功能的工程师  
**用途**: 架构设计，供开发参考

**文件**:
1. `simplified-data-model.md` - 数据模型设计（三层架构）
2. `task-scheduling-and-concurrency.md` - 任务调度系统设计
3. `batch-management.md` - 批次管理机制设计
4. `SCRIPT_INTERFACE_V2_CHANGELOG.md` - 接口变更说明
5. `execution-batch-dataset-relationship.md` - 关系说明（已废弃）
6. `data-model-layers-explained.md` - 四层模型（已废弃）
7. `data-model-optimization.md` - 优化建议（已废弃）

**特点**:
- 📐 描述系统如何工作
- 📐 包含表结构、API 设计、状态机等
- 📐 废弃文档保留以供参考设计演进

---

### 使用类 (`docs/user-guide/`)

**目标用户**: 系统使用者  
**用途**: 操作指南（待添加）

**计划文件**:
- `quick-start.md` - 快速开始
- `api-reference.md` - API 文档
- `batch-operations.md` - 批次操作指南
- `comparison-guide.md` - 对比功能使用

---

## 移动的文件列表

从 `.agents/rules/` → `docs/design/`:

1. ✅ `simplified-data-model.md`
2. ✅ `task-scheduling-and-concurrency.md`
3. ✅ `batch-management.md`
4. ✅ `execution-batch-dataset-relationship.md`
5. ✅ `data-model-layers-explained.md`
6. ✅ `data-model-optimization.md`
7. ✅ `SCRIPT_INTERFACE_V2_CHANGELOG.md`

---

## 更新的文件

### 1. `.agents/rules/README.md`
- ✅ 移除设计文档相关内容
- ✅ 只保留规范说明
- ✅ 添加指向设计文档的链接

### 2. `docs/design/README.md`
- ✅ 新建设计文档索引
- ✅ 说明每个设计文档的用途
- ✅ 提供阅读顺序建议
- ✅ 标注废弃文档

### 3. `docs/user-guide/README.md`
- ✅ 新建使用文档占位
- ✅ 列出计划添加的文档

### 4. `README.md` (根目录)
- ✅ 更新文档导航
- ✅ 区分规范、设计、使用三类文档
- ✅ 更新项目结构说明
- ✅ 更新脚本编写示例（v2.0 接口）

---

## 使用场景指引

### 场景 1: 我要添加一个新的评估脚本

**看这些文档**:
1. [.agents/rules/script-interface.md](.agents/rules/script-interface.md) - 必须遵守的接口规范
2. [data/scripts/example_script.py](data/scripts/example_script.py) - 参考模板
3. [docs/design/SCRIPT_INTERFACE_V2_CHANGELOG.md](docs/design/SCRIPT_INTERFACE_V2_CHANGELOG.md) - 如果有旧脚本需要迁移

**不需要看**: 数据模型设计、任务调度设计（系统已实现）

---

### 场景 2: 我要添加一个新的数据集

**看这些文档**:
1. [.agents/rules/dataset-format.md](.agents/rules/dataset-format.md) - 必须遵守的格式规范
2. [.agents/rules/comparison-requirements.md](.agents/rules/comparison-requirements.md) - 如果需要对比功能

**不需要看**: 数据模型设计、批次管理（系统已实现）

---

### 场景 3: 我要开发系统功能（如实现任务调度器）

**看这些文档**:
1. [docs/design/simplified-data-model.md](docs/design/simplified-data-model.md) - 理解数据结构
2. [docs/design/task-scheduling-and-concurrency.md](docs/design/task-scheduling-and-concurrency.md) - 任务调度设计
3. [docs/design/batch-management.md](docs/design/batch-management.md) - 批次管理机制

**参考规范**: [.agents/rules/](.agents/rules/) 确保实现符合接口约定

---

### 场景 4: 我是普通用户，想使用系统

**看这些文档**:
1. [README.md](README.md) - 快速开始
2. [docs/user-guide/](docs/user-guide/) - 使用指南（待添加）

**不需要看**: 规范文档、设计文档

---

## 验证重组结果

```bash
# 1. 检查 .agents/rules/ 只有规范文件
ls .agents/rules/
# 应该看到: script-interface.md, dataset-format.md, output-structure.md, comparison-requirements.md, README.md

# 2. 检查 docs/design/ 有设计文档
ls docs/design/
# 应该看到: simplified-data-model.md, task-scheduling-and-concurrency.md, batch-management.md, ...

# 3. 检查 docs/user-guide/ 已创建
ls docs/user-guide/
# 应该看到: README.md

# 4. 验证链接有效性
grep -r "\.agents/rules/" README.md
grep -r "docs/design/" README.md
```

---

## 影响

### 对现有代码的影响
- ✅ **无影响**: 这只是文档重组，不影响代码逻辑

### 对文档链接的影响
- ✅ **已更新**: README.md 中的所有链接已更新
- ✅ **已更新**: .agents/rules/README.md 已重写
- ✅ **已新建**: docs/design/README.md 和 docs/user-guide/README.md

### 对开发流程的影响
- ✅ **更清晰**: 规范和设计明确分离
- ✅ **更易查找**: 根据角色快速定位需要的文档
- ✅ **更易维护**: 各类文档职责明确

---

## 后续计划

1. ✅ 完成文档重组（已完成）
2. 📝 添加使用文档到 `docs/user-guide/`
   - quick-start.md
   - api-reference.md
   - batch-operations.md
3. 📝 整理现有的旧文档（docs/ 根目录下的零散文档）
4. 📝 为设计文档添加架构图

---

**总结**: 这次重组将规范（Rule）、设计（Design）、使用（User Guide）三类文档清晰分离，使得不同角色的用户可以快速找到需要的文档，提高了文档的可用性和可维护性。
