# 前端开发指南

## 技术栈

- **构建工具**: Vite 5
- **框架**: React 18 + TypeScript
- **UI 组件**: Ant Design 5
- **路由**: React Router v6
- **HTTP 客户端**: Axios
- **状态管理**: Zustand
- **图表**: Recharts

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
# 方式一：使用启动脚本
./start_dev.sh

# 方式二：直接使用 npm
npm run dev
```

开发服务器将在 `http://localhost:5173` 启动，API 请求会自动代理到 `http://localhost:8000`。

### 3. 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist/` 目录。

### 4. 预览生产版本

```bash
npm run preview
```

## 项目结构

```
frontend/
├── public/              # 静态资源
├── src/
│   ├── api/            # API 客户端
│   │   ├── client.ts          # Axios 实例配置
│   │   ├── datasets.ts        # 数据集 API
│   │   ├── scripts.ts         # 脚本 API
│   │   ├── models.ts          # 模型 API
│   │   ├── taskGroups.ts      # 任务组 API
│   │   ├── taskInstances.ts   # 任务实例 API
│   │   └── comparisons.ts     # 对比 API
│   ├── components/     # 公共组件
│   │   └── Layout/            # 布局组件
│   │       ├── index.tsx      # 主布局
│   │       ├── Sidebar.tsx    # 侧边栏
│   │       └── Header.tsx     # 顶部栏
│   ├── pages/          # 页面组件
│   │   ├── Dashboard/         # 任务面板
│   │   ├── DataManagement/    # 数据管理
│   │   ├── TaskCreate/        # 创建任务
│   │   ├── TaskDetail/        # 任务详情
│   │   └── Comparison/        # 结果对比
│   ├── types/          # TypeScript 类型定义
│   │   └── index.ts           # 全局类型
│   ├── App.tsx         # 根组件
│   ├── main.tsx        # 应用入口
│   └── index.css       # 全局样式
├── index.html          # HTML 入口
├── package.json        # 依赖配置
├── tsconfig.json       # TypeScript 配置
├── vite.config.ts      # Vite 配置
└── start_dev.sh        # 启动脚本

```

## 核心功能

### 1. 任务面板 (Dashboard)

- 任务列表展示
- 任务状态统计
- 任务启动/停止/重试
- 状态、标签、模型筛选
- 实时刷新

### 2. 数据管理 (DataManagement)

**数据集管理**:
- 创建数据集
- 查看数据集实例
- 导入 JSONL 数据
- 删除数据集

**脚本管理**:
- 扫描脚本目录
- 查看脚本列表

### 3. 创建任务 (TaskCreate)

- 选择数据集和脚本
- 设置标签和模型
- 配置并发数
- JSON 格式过滤条件

### 4. 任务详情 (TaskDetail)

- 任务信息展示
- 执行进度展示
- 子任务列表
- 任务实例列表
- 实例重试功能
- 5秒自动刷新

### 5. 结果对比 (Comparison)

**模型对比**:
- 同一标签下不同模型对比
- 对比指标展示

**标签对比**:
- 同一模型下不同标签对比
- 基线 vs 实验版本

**实例对比**:
- 单个实例的详细对比
- 差异摘要展示

## API 集成

所有 API 请求通过 `src/api/` 目录下的服务模块进行，已实现：

- 自动错误处理（Toast 提示）
- 统一超时配置（30秒）
- API 代理到后端（/api -> http://localhost:8000）

示例：

```typescript
import { taskGroupsApi } from '@/api/taskGroups'

// 获取任务列表
const response = await taskGroupsApi.list({ page: 1, page_size: 10 })

// 启动任务
await taskGroupsApi.start(taskId)
```

## 开发注意事项

### 1. 路径别名

TypeScript 和 Vite 已配置路径别名 `@` 指向 `src` 目录：

```typescript
import { Dataset } from '@/types'
import { datasetsApi } from '@/api/datasets'
```

### 2. API 代理

开发环境下，所有 `/api` 开头的请求会自动代理到 `http://localhost:8000`：

```typescript
// 实际请求: http://localhost:8000/api/v1/datasets/
client.get('/api/v1/datasets/')
```

### 3. Ant Design 国际化

已在 `src/main.tsx` 中配置中文语言包：

```typescript
import zhCN from 'antd/locale/zh_CN'

<ConfigProvider locale={zhCN}>
  <App />
</ConfigProvider>
```

### 4. 类型安全

所有 API 响应和组件 Props 都有完整的 TypeScript 类型定义，位于 `src/types/index.ts`。

## 环境要求

- Node.js: v16.0.0+
- npm: v7.0.0+

## 常见问题

### 1. 端口冲突

如果 5173 端口被占用，可以修改 `vite.config.ts`:

```typescript
export default defineConfig({
  server: {
    port: 3000, // 修改为其他端口
  },
})
```

### 2. API 代理失败

确保后端服务运行在 `http://localhost:8000`，可以修改 `vite.config.ts` 中的代理配置。

### 3. 依赖安装失败

尝试清除缓存后重新安装：

```bash
rm -rf node_modules package-lock.json
npm install
```

## 待扩展功能

- WebSocket 实时更新
- 图表可视化（Recharts）
- Zustand 全局状态管理
- 更多交互优化
