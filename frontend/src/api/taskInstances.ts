import client from './client'
import { TaskInstance, PaginatedResponse } from '@/types'

export const taskInstancesApi = {
  list: (params?: {
    page?: number
    page_size?: number
    task_id?: number
    instance_id?: string
    tag?: string
    model?: string
    status?: string
  }) => client.get<any, PaginatedResponse<TaskInstance>>('/v1/task-instances/', { params }),

  get: (id: number) => 
    client.get<any, TaskInstance>(`/v1/task-instances/${id}`),

  retry: (id: number) => 
    client.post<any, TaskInstance>(`/v1/task-instances/${id}/retry`),

  getByInstanceId: (instanceId: string, params?: { tag?: string; model?: string }) => 
    client.get<any, TaskInstance[]>(`/v1/task-instances/instance/${instanceId}`, { params }),

  stats: (params?: { task_id?: number; tag?: string; model?: string }) => 
    client.get<any, {
      total: number
      pending: number
      running: number
      completed: number
      failed: number
      timeout: number
      success_rate: number
      avg_duration: number | null
    }>('/v1/task-instances/stats', { params }),
}
