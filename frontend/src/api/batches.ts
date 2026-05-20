import { client } from './client'
import type {
  Batch,
  BatchResult,
  BatchStats,
  BatchCreateRequest,
  BatchAddTasksRequest
} from '@/types'

export const batchesApi = {
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
    return client.post('/v1/batches', data)
  },

  async get(id: number): Promise<Batch> {
    return client.get(`/v1/batches/${id}`)
  },

  async list(params?: {
    skip?: number
    limit?: number
    status?: string
    model?: string
    tag?: string
  }): Promise<Batch[]> {
    return client.get('/v1/batches', { params })
  },

  async update(id: number, data: Partial<Batch>): Promise<Batch> {
    return client.patch(`/v1/batches/${id}`, data)
  },

  async delete(id: number): Promise<{ message: string }> {
    return client.delete(`/v1/batches/${id}`)
  },

  async start(id: number, force?: boolean): Promise<{
    batch_id: number
    batch_name: string
    scheduled_tasks: number
    max_concurrency: number
  }> {
    const res = await client.post<{ message: string; data: any }>(`/v1/batches/${id}/start`, { force })
    return res.data as any
  },

  async pause(id: number, wait_for_running?: boolean): Promise<{
    batch_id: number
    batch_name: string
    cancelled_tasks: number
    running_tasks: number
    wait_for_running: boolean
  }> {
    const res = await client.post<{ message: string; data: any }>(`/v1/batches/${id}/pause`, { wait_for_running })
    return res.data as any
  },

  async resume(id: number): Promise<{
    batch_id: number
    batch_name: string
    scheduled_tasks: number
  }> {
    const res = await client.post<{ message: string; data: any }>(`/v1/batches/${id}/resume`)
    return res.data as any
  },

  async retry(id: number, params?: {
    instance_ids?: string[]
    reset_retry_count?: boolean
  }): Promise<{
    batch_id: number
    retried_count: number
    scheduled_count: number
  }> {
    const res = await client.post<{ message: string; data: any }>(`/v1/batches/${id}/retry`, params)
    return res.data as any
  },

  async addTasks(id: number, data: BatchAddTasksRequest): Promise<{
    new_tasks: number
    skipped: number
    overwritten: number
    total: number
  }> {
    const res = await client.post<{ message: string; data: any }>(`/v1/batches/${id}/tasks`, data)
    return res.data as any
  },

  async getTasks(id: number, params?: {
    status?: string
    skip?: number
    limit?: number
  }): Promise<BatchResult[]> {
    return client.get(`/v1/batches/${id}/tasks`, { params })
  },

  async getTask(id: number, instance_id: string): Promise<BatchResult> {
    return client.get(`/v1/batches/${id}/tasks/${encodeURIComponent(instance_id)}`)
  },

  async runTask(id: number, instance_id: string): Promise<{
    batch_id: number
    task_id: number
    instance_id: string
    status: string
    job_id: string | null
  }> {
    const res = await client.post<{ message: string; data: any }>(`/v1/batches/${id}/tasks/${encodeURIComponent(instance_id)}/run`)
    return res.data as any
  },

  async rerunTask(id: number, instance_id: string, params?: {
    reset_retry_count?: boolean
  }): Promise<{
    batch_id: number
    task_id: number
    instance_id: string
    status: string
    job_id: string | null
  }> {
    const res = await client.post<{ message: string; data: any }>(`/v1/batches/${id}/tasks/${encodeURIComponent(instance_id)}/rerun`, params)
    return res.data as any
  },

  async getStats(id: number): Promise<BatchStats> {
    return client.get(`/v1/batches/${id}/stats`)
  },

  async getTaskValidationDetail(id: number, instance_id: string): Promise<any> {
    return client.get(`/v1/batches/${id}/tasks/${encodeURIComponent(instance_id)}/validation-detail`)
  },

  async getTaskTrace(id: number, instance_id: string): Promise<any[]> {
    return client.get(`/v1/batches/${id}/tasks/${encodeURIComponent(instance_id)}/trace`)
  },

  async getTaskPatchContent(id: number, instance_id: string): Promise<{ content: string }> {
    return client.get(`/v1/batches/${id}/tasks/${encodeURIComponent(instance_id)}/patch-content`)
  },

  async getTaskLogContent(id: number, instance_id: string, logName: string): Promise<{ content: string }> {
    return client.get(`/v1/batches/${id}/tasks/${encodeURIComponent(instance_id)}/logs/${logName}`)
  },

  downloadTaskPatch(id: number, instance_id: string): string {
    return `${client.defaults.baseURL}/v1/batches/${id}/tasks/${encodeURIComponent(instance_id)}/patch`
  }
}
