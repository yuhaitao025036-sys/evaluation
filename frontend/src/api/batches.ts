import { client } from './client'
import type {
  Batch,
  BatchResult,
  BatchStats,
  BatchCreateRequest,
  BatchAddTasksRequest
} from '@/types'

export const batchesApi = {
  // ========== 批次 CRUD ==========
  
  /**
   * 创建批次
   */
  async create(data: BatchCreateRequest): Promise<{
    message: string
    data: {
      batch_id: number
      batch_name: string
      stats: {
        new_tasks: number
        skipped: number
        overwritten: number
        total: number
      }
    }
  }> {
    const res = await client.post('/api/v1/batches', data)
    return res.data
  },

  /**
   * 获取批次详情
   */
  async get(id: number): Promise<Batch> {
    const res = await client.get(`/api/v1/batches/${id}`)
    return res.data
  },

  /**
   * 列出批次
   */
  async list(params?: {
    skip?: number
    limit?: number
    status?: string
    model?: string
    tag?: string
  }): Promise<Batch[]> {
    const res = await client.get('/api/v1/batches', { params })
    return res.data
  },

  /**
   * 更新批次配置
   */
  async update(id: number, data: Partial<Batch>): Promise<Batch> {
    const res = await client.patch(`/api/v1/batches/${id}`, data)
    return res.data
  },

  /**
   * 删除批次
   */
  async delete(id: number): Promise<{ message: string }> {
    const res = await client.delete(`/api/v1/batches/${id}`)
    return res.data
  },

  // ========== 批次控制 ==========
  
  /**
   * 启动批次
   */
  async start(id: number, force?: boolean): Promise<{
    batch_id: number
    batch_name: string
    scheduled_tasks: number
    max_concurrency: number
  }> {
    const res = await client.post(`/api/v1/batches/${id}/start`, { force })
    return res.data.data
  },

  /**
   * 暂停批次
   */
  async pause(id: number, wait_for_running?: boolean): Promise<{
    batch_id: number
    batch_name: string
    cancelled_tasks: number
    running_tasks: number
    wait_for_running: boolean
  }> {
    const res = await client.post(`/api/v1/batches/${id}/pause`, { wait_for_running })
    return res.data.data
  },

  /**
   * 恢复批次
   */
  async resume(id: number): Promise<{
    batch_id: number
    batch_name: string
    scheduled_tasks: number
  }> {
    const res = await client.post(`/api/v1/batches/${id}/resume`)
    return res.data.data
  },

  /**
   * 重试失败任务
   */
  async retry(id: number, params?: {
    instance_ids?: string[]
    reset_retry_count?: boolean
  }): Promise<{
    batch_id: number
    retried_count: number
    scheduled_count: number
  }> {
    const res = await client.post(`/api/v1/batches/${id}/retry`, params)
    return res.data.data
  },

  // ========== 任务管理 ==========
  
  /**
   * 向批次追加任务
   */
  async addTasks(id: number, data: BatchAddTasksRequest): Promise<{
    new_tasks: number
    skipped: number
    overwritten: number
    total: number
  }> {
    const res = await client.post(`/api/v1/batches/${id}/tasks`, data)
    return res.data.data
  },

  /**
   * 获取批次任务列表
   */
  async getTasks(id: number, params?: {
    status?: string
    skip?: number
    limit?: number
  }): Promise<BatchResult[]> {
    const res = await client.get(`/api/v1/batches/${id}/tasks`, { params })
    return res.data
  },

  /**
   * 获取单个任务详情
   */
  async getTask(id: number, instance_id: string): Promise<BatchResult> {
    const res = await client.get(`/api/v1/batches/${id}/tasks/${encodeURIComponent(instance_id)}`)
    return res.data
  },

  // ========== 统计信息 ==========
  
  /**
   * 获取批次统计信息
   */
  async getStats(id: number): Promise<BatchStats> {
    const res = await client.get(`/api/v1/batches/${id}/stats`)
    return res.data
  },

  // ========== 文件读取 ==========
  
  /**
   * 获取任务的详细验证报告
   */
  async getTaskValidationDetail(id: number, instance_id: string): Promise<any> {
    const res = await client.get(`/api/v1/batches/${id}/tasks/${encodeURIComponent(instance_id)}/validation-detail`)
    return res.data
  },

  /**
   * 获取任务的执行轨迹
   */
  async getTaskTrace(id: number, instance_id: string): Promise<any[]> {
    const res = await client.get(`/api/v1/batches/${id}/tasks/${encodeURIComponent(instance_id)}/trace`)
    return res.data
  },

  /**
   * 获取任务的补丁内容 (文本形式)
   */
  async getTaskPatchContent(id: number, instance_id: string): Promise<{ content: string }> {
    const res = await client.get(`/api/v1/batches/${id}/tasks/${encodeURIComponent(instance_id)}/patch-content`)
    return res.data
  },

  /**
   * 下载任务的补丁文件
   */
  downloadTaskPatch(id: number, instance_id: string): string {
    return `${client.defaults.baseURL}/api/v1/batches/${id}/tasks/${encodeURIComponent(instance_id)}/patch`
  }
}
