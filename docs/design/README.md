# DUCC 评估系统设计文档

本目录包含 DUCC 评估系统的架构设计文档，供开发系统功能时参考。

> **注意**：本目录是**设计文档**（开发用），不是接口规范。  
> 接口规范请查看 [.agents/rules/](../../.agents/rules/)。

---

## 核心设计文档

### 1. **[simplified-data-model.md](simplified-data-model.md)** ⭐️⭐️ 推荐阅读

**内容**：三层数据模型设计（数据层 → 批次层 → 结果层）

**核心要点**：
- 移除执行层（executions 表）
- 以批次（batch）为核心组织单位
- `batch_results` 使用 `UNIQUE(batch_id, instance_id)` 保证数据隔离
- 任务状态：pending → queued → running → completed/failed

**适用场景**：
- 设计数据库表结构
- 理解批次和结果的关系
- 实现数据去重逻辑

**表结构**：
```sql
datasets
  ├── dataset_instances
  
batches (核心)
  ├── batch_results (UNIQUE: batch_id + instance_id)
```

---

### 2. **[task-scheduling-and-concurrency.md](task-scheduling-and-concurrency.md)** ⭐️⭐️ 推荐阅读

**内容**：任务调度系统和并发控制机制

**核心要点**：
- ✅ 系统级调度：脚本只处理单个 instance（不是范围）
- ✅ RQ 队列：任务排队执行，支持优先级
- ✅ 并发控制：全局限制 + 批次限制
- ✅ 失败重试：自动重试，配置 `max_retries`
- ✅ 暂停/恢复：批次级别控制

**任务生命周期**：
```
pending → queued → running → completed
                          ↘ failed → retry
```

**适用场景**：
- 实现任务调度器
- 实现 Worker 执行逻辑
- 设计批次管理 API

---

### 3. **[batch-management.md](batch-management.md)**

**内容**：批次管理机制和使用场景

**核心要点**：
- 批次是结果聚合单位（不是执行单位）
- 支持动态追加数据（多次运行累积结果）
- 同一批次内 model 和 tag 必须一致
- 数据去重策略：skip / overwrite / ask

**适用场景**：
- 设计批次创建 API
- 实现批次追加逻辑
- 设计批次状态管理

**典型工作流**：
```
1. 创建 baseline 批次（100 条数据）
2. 追加 50 条数据到 baseline
3. 创建 experiment_1 批次（相同 150 条数据）
4. 对比 baseline vs experiment_1 结果
```

---

### 4. **[SCRIPT_INTERFACE_V2_CHANGELOG.md](SCRIPT_INTERFACE_V2_CHANGELOG.md)**

**内容**：脚本接口 v1.0 → v2.0 变更说明

**核心变更**：
- ❌ 移除：`--start-index`, `--end-index`, `--dataset-path`
- ✅ 新增：`--instance-id` (必需), `--model` (必需), `--tag` (必需)
- 🔄 脚本从"循环处理"改为"单任务执行"

**适用场景**：
- 迁移旧脚本到 v2.0
- 理解为什么要改接口
- 了解新旧接口差异

---

### 5. **[BACKEND_SUMMARY.md](BACKEND_SUMMARY.md)**

**内容**：后端实现总结

**核心要点**：
- 技术栈和功能清单
- API 端点列表
- 核心模块说明

**适用场景**：
- 了解后端实现现状
- 查看已实现功能列表

---

### 6. **[DEVELOPMENT.md](DEVELOPMENT.md)**

**内容**：开发指南

**核心要点**：
- 开发环境搭建
- 代码规范
- 测试流程

**适用场景**：
- 新开发者入门
- 了解开发流程

---

### 7. **[ARCHITECTURE_CHANGE.md](ARCHITECTURE_CHANGE.md)**

**内容**：架构变更记录

**核心要点**：
- 重大架构调整
- 变更原因和影响

**适用场景**：
- 了解架构演进历史

---

### 8. **[DOCKER_DATA_STORAGE.md](DOCKER_DATA_STORAGE.md)**

**内容**：Docker 数据存储设计

**核心要点**：
- 数据持久化方案
- Volume 管理

**适用场景**：
- 配置 Docker 存储
- 了解数据管理方式

---

### 9. **[FRONTEND.md](FRONTEND.md)**

**内容**：前端设计规划

**核心要点**：
- 前端技术栈
- UI 组件设计
- 页面结构

**适用场景**：
- 开发前端功能

---

## 已废弃设计（仅供参考）

### ~~[data-model-layers-explained.md](data-model-layers-explained.md)~~

**状态**：已废弃，被 `simplified-data-model.md` 取代

**内容**：四层数据模型（数据 → 执行 → 结果 → 批次）

**废弃原因**：
- 执行层（executions 表）概念混淆
- 增加了不必要的复杂度
- 无法清晰表达批次的核心作用

**保留原因**：参考设计演进过程

---

### ~~[execution-batch-dataset-relationship.md](execution-batch-dataset-relationship.md)~~

**状态**：已废弃，关系已简化

**内容**：执行、批次、数据集三者关系说明

**废弃原因**：移除执行层后，关系已简化为 batch ↔ dataset

---

### ~~[data-model-optimization.md](data-model-optimization.md)~~

**状态**：已废弃，优化方案已整合

**内容**：数据模型优化建议

**废弃原因**：优化建议已整合到 `simplified-data-model.md`

---

## 设计原则

### 1. 简单优于复杂
- ✅ 移除不必要的抽象层（执行层）
- ✅ 以批次为核心，而非执行
- ✅ 清晰的数据关系

### 2. 系统控制调度
- ✅ 脚本只处理单个任务
- ✅ 系统负责并发控制、重试、优先级
- ✅ 细粒度状态追踪

### 3. 数据隔离
- ✅ 批次间完全独立（`UNIQUE(batch_id, instance_id)`）
- ✅ 同一 instance 可出现在多个批次
- ✅ 支持并发创建批次

### 4. 渐进式追加
- ✅ 批次支持动态追加数据
- ✅ 实时监控正确率
- ✅ 支持去重策略

---

## 阅读顺序建议

### 新手入门
1. 📖 [simplified-data-model.md](simplified-data-model.md) - 理解数据结构
2. 📖 [batch-management.md](batch-management.md) - 理解批次概念
3. 📖 [task-scheduling-and-concurrency.md](task-scheduling-and-concurrency.md) - 理解任务调度

### 开发脚本
1. 📖 [SCRIPT_INTERFACE_V2_CHANGELOG.md](SCRIPT_INTERFACE_V2_CHANGELOG.md) - 了解接口变更
2. 📖 [.agents/rules/script-interface.md](../../.agents/rules/script-interface.md) - 查看接口规范
3. 📖 [data/scripts/example_script.py](../../data/scripts/example_script.py) - 参考示例代码

### 开发系统功能
1. 📖 [simplified-data-model.md](simplified-data-model.md) - 设计数据库
2. 📖 [task-scheduling-and-concurrency.md](task-scheduling-and-concurrency.md) - 实现调度器
3. 📖 [batch-management.md](batch-management.md) - 实现批次管理

---

## 相关文档

### 接口规范
- **[.agents/rules/](../../.agents/rules/)** - 脚本和数据集接口规范

### 使用文档
- **[docs/user-guide/](../user-guide/)** - API 使用、批次操作指南

### 示例代码
- **[data/scripts/](../../data/scripts/)** - 脚本模板和示例

### 项目文档
- **[README.md](../../README.md)** - 项目整体说明

---

## 文档维护

设计文档的更新：

1. ✅ 保持设计文档与实现同步
2. ✅ 废弃的设计标注 `~~废弃~~` 但保留
3. ✅ 重大设计变更需要说明原因
4. ✅ 提供迁移路径（如有破坏性变更）

---

**重要提示**：

这些是**设计文档**，描述系统**如何工作**，供开发时参考。

如果你是添加脚本/数据集，请查看 [.agents/rules/](../../.agents/rules/)（接口规范）。
