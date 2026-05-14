# DUCC 评估系统文档中心

本目录包含 DUCC 评估系统的所有文档，按功能和受众分类。

---

## 📁 目录结构

```
docs/
├── design/          # 系统设计文档（开发者用）
├── user-guide/      # 使用指南（用户用）
├── setup/           # 环境配置文档
└── history/         # 历史记录
```

---

## 🎯 快速导航

### 我是新用户，想使用系统

👉 **[user-guide/](user-guide/)** - 使用指南

推荐阅读：
1. [INSTALLATION.md](user-guide/INSTALLATION.md) - 安装系统
2. [API_TESTING.md](user-guide/API_TESTING.md) - 学习 API 使用

---

### 我要添加脚本或数据集

👉 **[.agents/rules/](../.agents/rules/)** - 接口规范（必读）

推荐阅读：
1. [script-interface.md](../.agents/rules/script-interface.md) - 脚本接口规范 v2.0
2. [dataset-format.md](../.agents/rules/dataset-format.md) - 数据集格式规范
3. [data/scripts/example_script.py](../data/scripts/example_script.py) - 示例脚本

---

### 我要开发系统功能

👉 **[design/](design/)** - 系统设计文档

推荐阅读：
1. [simplified-data-model.md](design/simplified-data-model.md) - 数据模型设计
2. [task-scheduling-and-concurrency.md](design/task-scheduling-and-concurrency.md) - 任务调度设计
3. [BACKEND_SUMMARY.md](design/BACKEND_SUMMARY.md) - 后端实现总结

---

### 我要配置系统环境

👉 **[setup/](setup/)** - 环境配置文档

推荐阅读：
1. [DATABASE_PASSWORD.md](setup/DATABASE_PASSWORD.md) - 数据库密码配置
2. [CONDA_SETUP.md](setup/CONDA_SETUP.md) - Conda 环境配置

---

## 📚 详细分类

### [design/](design/) - 系统设计文档

**受众**：开发系统功能的工程师

**内容**：
- 数据模型设计
- 任务调度系统设计
- 批次管理机制
- 架构变更记录
- 后端实现总结
- 前端设计规划

📖 [查看完整列表](design/README.md)

---

### [user-guide/](user-guide/) - 使用指南

**受众**：系统使用者、运维人员

**内容**：
- 安装部署指南
- API 使用示例
- 批次操作指南
- 备份和恢复

📖 [查看完整列表](user-guide/README.md)

---

### [setup/](setup/) - 环境配置文档

**受众**：系统管理员、部署人员

**内容**：
- 数据库密码配置
- Conda 环境配置
- 环境迁移指南

📖 [查看完整列表](setup/README.md)

---

### [history/](history/) - 历史记录

**受众**：了解项目演进的开发者

**内容**：
- 重命名记录
- 文档重组记录
- 架构变更历史

📖 [查看完整列表](history/README.md)

---

## 🔗 其他重要文档

### 接口规范（开发必读）
- **[.agents/rules/](../.agents/rules/)** - 脚本和数据集接口规范

### 示例代码
- **[data/scripts/](../data/scripts/)** - 脚本模板和示例

### 项目根目录
- **[README.md](../README.md)** - 项目整体说明

---

## 📊 文档统计

| 类型 | 数量 | 位置 |
|------|------|------|
| 系统设计 | 13 个 | `design/` |
| 使用指南 | 4 个 | `user-guide/` |
| 环境配置 | 3 个 | `setup/` |
| 历史记录 | 2 个 | `history/` |
| 接口规范 | 5 个 | `.agents/rules/` |
| **总计** | **27 个** | |

---

## 💡 文档维护

### 添加新文档
1. 确定文档类型（设计/使用/配置/历史）
2. 放到对应目录
3. 更新该目录的 README.md
4. 更新本文件的统计信息

### 更新现有文档
1. 修改文档内容
2. 如有重大变更，在文档开头注明变更日期
3. 如需要，更新相关链接

### 废弃文档
1. 在文档标题添加 `~~废弃~~` 标记
2. 在文档开头说明废弃原因和替代文档
3. 不要删除，保留以供参考演进历史

---

**最后更新**: 2026-05-14  
**文档版本**: v2.0（文档重组后）
