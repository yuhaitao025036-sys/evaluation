# DUCC 批次系统重新设计方案

**日期**: 2026-05-14  
**版本**: v2.0  
**目标**: 统一前后端概念，简化用户操作流程

---

## 一、核心概念变更

### 旧概念 (v1.0)
```
TaskGroup (任务组)
  ├── Task (执行批次)
  │   └── TaskInstance (任务实例) - 单个数据的执行结果
  └── 混乱的层级关系
```

### 新概念 (v2.0)
```
Batch (批次) - 一次评测的完整单位
  └── BatchResult (批次结果) - 单个数据实例的执行结果
```

**关键变化**：
- ❌ 删除：TaskGroup, Task, TaskInstance 三层概念
- ✅ 保留：Batch, BatchResult 两层概念
- ✅ 前端统一叫"批次"而不是"任务"

---

## 二、用户操作流程设计

### 2.1 批次列表页面

**页面**: `/batches`

**显示内容**：
```
┌─────────────────────────────────────────────────────────────┐
│  批次管理                                    [+ 创建批次]     │
├─────────────────────────────────────────────────────────────┤
│  筛选：                                                       │
│  [状态: 全部 ▼] [模型: 全部 ▼] [标签: 全部 ▼] [搜索: ___]   │
├─────────────────────────────────────────────────────────────┤
│  批次名称            数据集    模型         标签    状态      │
│  ─────────────────────────────────────────────────────────  │
│  baseline-swebench  SWEBench  gpt-4-turbo baseline 已完成   │
│    📊 100/100 完成   ✓ 95 成功   ✗ 5 失败                    │
│    [查看详情] [追加任务] [重试失败] [导出结果]                │
│  ─────────────────────────────────────────────────────────  │
│  experiment-1       SWEBench  claude-3.5  exp-1   运行中    │
│    📊 45/100 完成    ✓ 40 成功   ⏳ 10 运行中   📋 45 待执行  │
│    [查看详情] [暂停] [追加任务]                               │
│  ─────────────────────────────────────────────────────────  │
└─────────────────────────────────────────────────────────────┘
```

**操作按钮**：
- **创建批次** - 跳转到批次创建页面
- **查看详情** - 跳转到批次详情页面
- **追加任务** - 向现有批次追加更多数据实例
- **暂停/恢复** - 控制批次执行
- **重试失败** - 重试失败的任务
- **导出结果** - 导出批次结果

---

### 2.2 创建批次页面

**页面**: `/batches/create`

**流程设计**：

#### Step 1: 选择创建模式
```
┌─────────────────────────────────────────────────────────────┐
│  创建批次                                                     │
├─────────────────────────────────────────────────────────────┤
│  请选择创建模式：                                             │
│                                                               │
│  ┌──────────────────────┐  ┌──────────────────────┐         │
│  │  🆕 创建新批次        │  │  ➕ 追加到现有批次   │         │
│  │                      │  │                      │         │
│  │  创建一个全新的评测   │  │  向已有批次添加更多   │         │
│  │  批次，包含独立的配置 │  │  数据实例进行评测     │         │
│  │                      │  │                      │         │
│  │      [选择]          │  │      [选择]          │         │
│  └──────────────────────┘  └──────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

#### Step 2a: 创建新批次
```
┌─────────────────────────────────────────────────────────────┐
│  创建新批次                                                   │
├─────────────────────────────────────────────────────────────┤
│  基本信息                                                     │
│  ├─ 批次名称: [________________] *必填                       │
│  └─ 描述:     [________________]                             │
│                                                               │
│  评测配置                                                     │
│  ├─ 数据集:   [SWEBench ▼] *必填                             │
│  ├─ 脚本:     [ducc_swebench_adapter.py ▼] *必填             │
│  ├─ 模型:     [gpt-4-turbo ▼] *必填                          │
│  ├─ 标签:     [baseline] *必填（用于对比实验）                │
│  └─ 最大并发: [10] (1-100)                                   │
│                                                               │
│  选择数据实例                                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ⚪ 全部实例 (2294 个)                                  │  │
│  │ ⚪ 指定范围: 从 [0] 到 [100]                           │  │
│  │ ⚪ 指定 ID: [django__django-11099, ...] 多个ID用逗号分隔│  │
│  │ ⚪ 高级筛选:                                            │  │
│  │    └─ repo_language = [Python ▼]                      │  │
│  │    └─ [+ 添加筛选条件]                                 │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  脚本参数（可选）                                             │
│  └─ execution_config: { "timeout": 3600, "use_tmux": true } │
│                                                               │
│                                    [取消]  [创建并启动批次]  │
└─────────────────────────────────────────────────────────────┘
```

#### Step 2b: 追加到现有批次
```
┌─────────────────────────────────────────────────────────────┐
│  追加任务到现有批次                                           │
├─────────────────────────────────────────────────────────────┤
│  选择目标批次                                                 │
│  ├─ 批次: [baseline-swebench ▼] *必填                        │
│  │                                                            │
│  │  当前批次信息：                                            │
│  │  - 数据集: SWEBench                                       │
│  │  - 模型: gpt-4-turbo                                      │
│  │  - 标签: baseline                                         │
│  │  - 已有实例: 100 个                                       │
│  │  - 状态: 已完成                                           │
│  │                                                            │
│  └─ ⚠️ 注意：追加的实例将使用该批次的配置（模型、标签、脚本） │
│                                                               │
│  选择要追加的数据实例                                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ⚪ 指定范围: 从 [100] 到 [200]                         │  │
│  │ ⚪ 指定 ID: [django__django-12345, ...]                │  │
│  │ ⚪ 高级筛选:                                            │  │
│  │    └─ repo_language = [Python ▼]                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  重复处理策略                                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ⚪ 跳过已存在的实例（默认）                             │  │
│  │ ⚪ 覆盖已存在的实例（重新执行）                         │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│                                    [取消]  [追加并启动]      │
└─────────────────────────────────────────────────────────────┘
```

---

### 2.3 批次详情页面

**页面**: `/batches/:id`

```
┌─────────────────────────────────────────────────────────────┐
│  批次详情: baseline-swebench                                  │
│                                                               │
│  [▶️ 启动] [⏸ 暂停] [🔄 重试失败] [➕ 追加任务] [📥 导出]    │
├─────────────────────────────────────────────────────────────┤
│  📊 执行统计                                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  总任务: 100        待执行: 0        运行中: 0        │   │
│  │  已完成: 95         失败: 5          成功率: 95%      │   │
│  │  验证通过: 90       验证通过率: 94.7%                  │   │
│  │  平均耗时: 120.5s   总耗时: 3h 20m                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ⚙️ 批次配置                                                  │
│  ├─ 数据集: SWEBench                                         │
│  ├─ 脚本: ducc_swebench_adapter.py                           │
│  ├─ 模型: gpt-4-turbo                                        │
│  ├─ 标签: baseline                                           │
│  ├─ 最大并发: 10                                             │
│  ├─ 重试次数: 3                                              │
│  └─ 创建时间: 2026-05-14 10:00:00                            │
│                                                               │
│  📋 任务列表                                                  │
│  筛选: [状态: 全部 ▼] [搜索实例ID: _____] [仅显示失败]       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Instance ID            状态    验证  耗时    操作     │   │
│  │ ───────────────────────────────────────────────────  │   │
│  │ django__django-11099  ✅ 完成  ✓通过  120s  [详情]   │   │
│  │ django__django-11100  ✅ 完成  ✓通过  115s  [详情]   │   │
│  │ django__django-11101  ❌ 失败  -     10s   [重试]    │   │
│  │ requests__requests-123 ⏳ 运行  -     45s   [查看]    │   │
│  │ flask__flask-456      📋 待执行 -     -     -        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                           [1] [2] [3] ... [10]│
└─────────────────────────────────────────────────────────────┘
```

---

### 2.4 任务详情弹窗

点击"详情"按钮弹出：

```
┌─────────────────────────────────────────────────────────────┐
│  任务详情: django__django-11099                        [✕]   │
├─────────────────────────────────────────────────────────────┤
│  📊 执行信息                                                  │
│  ├─ 状态: ✅ 已完成                                          │
│  ├─ 验证结果: ✓ 通过                                         │
│  ├─ 测试结果: 5/5 通过                                       │
│  ├─ 耗时: 120.5 秒                                           │
│  ├─ 开始时间: 2026-05-14 10:05:00                            │
│  ├─ 完成时间: 2026-05-14 10:07:00                            │
│  └─ Worker: worker-1                                         │
│                                                               │
│  📁 输出文件                                                  │
│  ├─ 📄 task_summary.json        [查看] [下载]               │
│  ├─ 📄 extracted_patch.diff     [查看] [下载]               │
│  ├─ 📄 execution_trace.jsonl    [查看] [下载]               │
│  └─ 📄 validation_detail.json   [查看] [下载]               │
│                                                               │
│  🔍 实例数据                                                  │
│  {                                                            │
│    "instance_id": "django__django-11099",                    │
│    "repo": "django/django",                                  │
│    "version": "3.0",                                         │
│    "problem_statement": "...",                               │
│    ...                                                       │
│  }                                                            │
│                                                               │
│                                              [关闭] [重新执行]│
└─────────────────────────────────────────────────────────────┘
```

---

## 三、前端类型定义 (TypeScript)

```typescript
// frontend/src/types/index.ts

export interface Batch {
  id: number
  batch_name: string
  dataset_id: number
  script_id: number
  model: string
  tag: string
  
  // 批次状态
  status: 'created' | 'running' | 'paused' | 'completed' | 'failed'
  
  // 并发控制
  max_concurrency: number
  current_running: number
  priority: number
  
  // 任务统计
  total_tasks: number
  pending_tasks: number
  queued_tasks: number
  running_tasks: number
  completed_tasks: number
  failed_tasks: number
  
  // 时间戳
  created_at: string
  started_at: string | null
  paused_at: string | null
  completed_at: string | null
  updated_at: string
  
  // 输出目录
  output_dir: string
  
  // 关联对象
  dataset?: Dataset
  script?: Script
  
  // 执行配置
  execution_config?: Record<string, any>
  created_by?: string
}

export interface BatchResult {
  id: number
  batch_id: number
  dataset_instance_id: number
  instance_id: string
  
  // 任务配置
  model: string
  tag: string
  
  // 任务状态
  status: 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'retrying'
  
  // 重试机制
  retry_count: number
  max_retries: number
  
  // 队列信息
  job_id: string | null
  worker_id: string | null
  
  // 执行结果
  validation_success: boolean | null
  tests_passed: number
  tests_failed: number
  tests_total: number
  duration_seconds: number | null
  result_summary: Record<string, any> | null
  
  // 输出文件
  patch_path: string | null
  output_dir: string
  
  // 错误信息
  error_message: string | null
  
  // 时间戳
  created_at: string
  queued_at: string | null
  started_at: string | null
  completed_at: string | null
}

export interface BatchStats {
  batch_id: number
  batch_name: string
  status: string
  total_tasks: number
  pending_tasks: number
  queued_tasks: number
  running_tasks: number
  completed_tasks: number
  failed_tasks: number
  success_rate: number
  validation_success_rate: number | null
  avg_duration: number | null
  total_duration: number | null
}

export interface BatchCreateRequest {
  batch_name: string
  dataset_id: number
  script_id: number
  model: string
  tag: string
  
  // 实例选择（三选一）
  instance_ids?: string[]           // 指定 ID 列表
  start_index?: number              // 范围开始
  end_index?: number                // 范围结束
  filter_conditions?: Record<string, any>  // JSONB 筛选
  
  // 追加模式
  append_to_existing?: boolean      // 是否追加到已有批次
  overwrite_existing?: boolean      // 重复实例是否覆盖
  
  // 配置
  max_concurrency?: number          // 最大并发（1-100）
  max_retries?: number              // 最大重试次数（0-10）
  priority?: number                 // 优先级
  execution_config?: Record<string, any>  // 脚本自定义参数
  created_by?: string
}

export interface BatchAddTasksRequest {
  instance_ids?: string[]
  start_index?: number
  end_index?: number
  filter_conditions?: Record<string, any>
  overwrite_existing?: boolean
}
```

---

## 四、前端 API 层

```typescript
// frontend/src/api/batches.ts

import { client } from './client'
import type {
  Batch,
  BatchResult,
  BatchStats,
  BatchCreateRequest,
  BatchAddTasksRequest,
  PaginatedResponse
} from '@/types'

export const batchesApi = {
  // 批次 CRUD
  async create(data: BatchCreateRequest): Promise<{ batch_id: number; batch_name: string; stats: any }> {
    const res = await client.post('/api/v1/batches', data)
    return res.data.data
  },

  async get(id: number): Promise<Batch> {
    const res = await client.get(`/api/v1/batches/${id}`)
    return res.data
  },

  async list(params: {
    skip?: number
    limit?: number
    status?: string
    model?: string
    tag?: string
  }): Promise<Batch[]> {
    const res = await client.get('/api/v1/batches', { params })
    return res.data
  },

  async update(id: number, data: Partial<Batch>): Promise<Batch> {
    const res = await client.patch(`/api/v1/batches/${id}`, data)
    return res.data
  },

  async delete(id: number): Promise<void> {
    await client.delete(`/api/v1/batches/${id}`)
  },

  // 批次控制
  async start(id: number, force?: boolean): Promise<any> {
    const res = await client.post(`/api/v1/batches/${id}/start`, { force })
    return res.data.data
  },

  async pause(id: number, wait_for_running?: boolean): Promise<any> {
    const res = await client.post(`/api/v1/batches/${id}/pause`, { wait_for_running })
    return res.data.data
  },

  async resume(id: number): Promise<any> {
    const res = await client.post(`/api/v1/batches/${id}/resume`)
    return res.data.data
  },

  async retry(id: number, instance_ids?: string[], reset_retry_count?: boolean): Promise<any> {
    const res = await client.post(`/api/v1/batches/${id}/retry`, {
      instance_ids,
      reset_retry_count
    })
    return res.data.data
  },

  // 任务管理
  async addTasks(id: number, data: BatchAddTasksRequest): Promise<any> {
    const res = await client.post(`/api/v1/batches/${id}/tasks`, data)
    return res.data.data
  },

  async getTasks(id: number, params: {
    status?: string
    skip?: number
    limit?: number
  }): Promise<BatchResult[]> {
    const res = await client.get(`/api/v1/batches/${id}/tasks`, { params })
    return res.data
  },

  async getTask(id: number, instance_id: string): Promise<BatchResult> {
    const res = await client.get(`/api/v1/batches/${id}/tasks/${instance_id}`)
    return res.data
  },

  // 统计
  async getStats(id: number): Promise<BatchStats> {
    const res = await client.get(`/api/v1/batches/${id}/stats`)
    return res.data
  }
}
```

---

## 五、路由配置

```typescript
// frontend/src/App.tsx

import { Routes, Route } from 'react-router-dom'
import BatchList from '@/pages/BatchList'
import BatchCreate from '@/pages/BatchCreate'
import BatchDetail from '@/pages/BatchDetail'

function App() {
  return (
    <Routes>
      {/* 批次相关 */}
      <Route path="/batches" element={<BatchList />} />
      <Route path="/batches/create" element={<BatchCreate />} />
      <Route path="/batches/:id" element={<BatchDetail />} />
      
      {/* 数据管理 */}
      <Route path="/data" element={<DataManagement />} />
      
      {/* 对比分析 */}
      <Route path="/comparison" element={<Comparison />} />
    </Routes>
  )
}
```

---

## 六、实施步骤

### Phase 1: 类型和 API 层（不影响现有功能）
1. ✅ 创建新类型定义 `Batch`, `BatchResult`
2. ✅ 创建 `batches.ts` API 文件
3. ✅ 保留旧的 `taskGroups.ts` API（兼容）

### Phase 2: 新建批次页面
1. 创建 `pages/BatchList/index.tsx`
2. 创建 `pages/BatchCreate/index.tsx`
   - 子组件：`CreateModeSelector.tsx` (选择创建模式)
   - 子组件：`NewBatchForm.tsx` (新建批次表单)
   - 子组件：`AppendBatchForm.tsx` (追加任务表单)
   - 子组件：`InstanceSelector.tsx` (实例选择器)
3. 创建 `pages/BatchDetail/index.tsx`
   - 子组件：`BatchStatsCard.tsx` (统计卡片)
   - 子组件：`BatchConfigCard.tsx` (配置卡片)
   - 子组件：`TaskList.tsx` (任务列表)
   - 子组件：`TaskDetailModal.tsx` (任务详情弹窗)

### Phase 3: 更新导航和路由
1. 更新 `Layout` 组件导航菜单
2. 更新路由配置
3. 设置默认路由为 `/batches`

### Phase 4: 迁移和清理
1. 标记旧页面为 deprecated
2. 添加跳转提示
3. 确认无依赖后删除旧代码

---

## 七、关键差异对比

| 维度 | 旧系统 (TaskGroup) | 新系统 (Batch) |
|------|-------------------|----------------|
| **概念层级** | 3 层（TaskGroup → Task → TaskInstance） | 2 层（Batch → BatchResult） |
| **前端名称** | "任务" | "批次" |
| **创建流程** | 单一流程，无追加选项 | 两种模式：新建 / 追加 |
| **并发控制** | 前端设置，后端未实现 | 系统级调度，自动控制 |
| **任务调度** | 不清晰 | RQ 队列 + 自动调度 |
| **重试机制** | 无 | 自动重试 + 手动重试 |
| **实时统计** | 手动计算 | 数据库触发器自动更新 |
| **追加任务** | 不支持 | 支持，可选跳过/覆盖 |
| **批次控制** | 无 | 启动/暂停/恢复 |

---

这个设计方案怎么样？要我开始实现吗？
