import client from './client'
import { TaskGroup, PaginatedResponse, TaskGroupStats, Task } from '@/types'

export const taskGroupsApi = {
  list: (params?: {
    page?: number
    page_size?: number
    status?: string
    tag?: string
    model?: string
  }) => client.get<any, PaginatedResponse<TaskGroup>>('/v1/task-groups/', { params }),

  get: (id: number) => 
    client.get<any, TaskGroup>(`/v1/task-groups/${id}`),

  create: (data: {
    name: string
    description?: string
    dataset_id: number
    script_id: number
    tag: string
    model?: string
    concurrency?: number
    filter_conditions?: Record<string, any>
  }) => client.post<any, TaskGroup>('/v1/task-groups/', data),

  delete: (id: number) => 
    client.delete(`/v1/task-groups/${id}`),

  start: (id: number) => 
    client.post<any, TaskGroup>(`/v1/task-groups/${id}/start`),

  stop: (id: number) => 
    client.post<any, TaskGroup>(`/v1/task-groups/${id}/stop`),

  retry: (id: number) => 
    client.post<any, TaskGroup>(`/v1/task-groups/${id}/retry`),

  stats: () => 
    client.get<any, TaskGroupStats>('/v1/task-groups/stats'),

  getTasks: (id: number, params?: { page?: number; page_size?: number; status?: string }) => 
    client.get<any, PaginatedResponse<Task>>(`/v1/task-groups/${id}/tasks`, { params }),
}
