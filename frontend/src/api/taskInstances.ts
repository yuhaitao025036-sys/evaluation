import client from './client'
import { TaskInstance, PaginatedResponse } from '@/types'

const toPaginatedResponse = <T>(items: T[], page = 1, pageSize = 10): PaginatedResponse<T> => ({
  items,
  total: items.length,
  page,
  page_size: pageSize,
  pages: Math.max(1, Math.ceil(items.length / pageSize)),
})

export const taskInstancesApi = {
  async list(params?: {
    page?: number
    page_size?: number
    task_id?: number
    instance_id?: string
    tag?: string
    model?: string
    status?: string
  }): Promise<PaginatedResponse<TaskInstance>> {
    const page = params?.page || 1
    const pageSize = params?.page_size || 10
    const { page: _page, page_size: _pageSize, ...rest } = params || {}
    const items = await client.get<TaskInstance[]>('/v1/task-instances', {
      params: {
        ...rest,
        offset: (page - 1) * pageSize,
        limit: pageSize,
      },
    })
    return toPaginatedResponse(items, page, pageSize)
  },

  get: (id: number): Promise<TaskInstance> =>
    client.get(`/v1/task-instances/${id}`),

  retry: (id: number): Promise<TaskInstance> =>
    client.post(`/v1/task-instances/${id}/retry`),

  getByInstanceId: (instanceId: string): Promise<TaskInstance[]> =>
    client.get(`/v1/task-instances/by-instance-id/${encodeURIComponent(instanceId)}`),

  async stats(params?: { task_id?: number; tag?: string; model?: string }): Promise<{
    total: number
    pending: number
    running: number
    completed: number
    failed: number
    timeout: number
    success_rate: number
    avg_duration: number | null
  }> {
    const summary = await client.get<any>('/v1/task-instances/stats/summary', { params })
    return {
      total: summary.total_instances || 0,
      pending: summary.status_breakdown?.pending || 0,
      running: summary.status_breakdown?.running || 0,
      completed: summary.status_breakdown?.completed || 0,
      failed: summary.status_breakdown?.failed || 0,
      timeout: summary.status_breakdown?.timeout || 0,
      success_rate: (summary.success_rate || 0) * 100,
      avg_duration: summary.avg_duration_seconds ?? null,
    }
  },
}
