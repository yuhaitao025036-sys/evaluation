import client from './client'
import { TaskGroup, PaginatedResponse, TaskGroupStats, Task } from '@/types'

const normalizeTaskGroup = (group: any): TaskGroup => ({
  ...group,
  status: group.status === 'created' ? 'pending' : group.status,
  total_tasks: group.total_tasks ?? group.total_instances ?? 0,
  completed_tasks: group.completed_tasks ?? group.completed_instances ?? 0,
  failed_tasks: group.failed_tasks ?? group.failed_instances ?? 0,
})

const toPaginatedResponse = <T>(items: T[], page = 1, pageSize = 10): PaginatedResponse<T> => ({
  items,
  total: items.length,
  page,
  page_size: pageSize,
  pages: Math.max(1, Math.ceil(items.length / pageSize)),
})

export const taskGroupsApi = {
  async list(params?: {
    page?: number
    page_size?: number
    status?: string
    tag?: string
    model?: string
  }): Promise<PaginatedResponse<TaskGroup>> {
    const page = params?.page || 1
    const pageSize = params?.page_size || 10
    const { page: _page, page_size: _pageSize, ...rest } = params || {}
    const items = await client.get<any[]>('/v1/task-groups', {
      params: {
        ...rest,
        skip: (page - 1) * pageSize,
        limit: pageSize,
      },
    })
    return toPaginatedResponse(items.map(normalizeTaskGroup), page, pageSize)
  },

  async get(id: number): Promise<TaskGroup> {
    const group = await client.get<any>(`/v1/task-groups/${id}`)
    return normalizeTaskGroup(group)
  },

  create: (data: {
    name: string
    description?: string
    dataset_id: number
    script_id: number
    tag: string
    model?: string
    concurrency?: number
    filter_conditions?: Record<string, any>
  }): Promise<TaskGroup> => client.post('/v1/task-groups', data),

  start: (id: number): Promise<TaskGroup> =>
    client.post(`/v1/task-groups/${id}/start`),

  stop: (id: number): Promise<TaskGroup> =>
    client.post(`/v1/task-groups/${id}/pause`),

  retry: (_id?: number): Promise<TaskGroup> =>
    Promise.reject(new Error('后端当前未提供重试任务组接口')),

  async stats(): Promise<TaskGroupStats> {
    const rawGroups = await client.get<any[]>('/v1/task-groups', { params: { limit: 1000 } })
    const groups = rawGroups.map(normalizeTaskGroup)
    const total = groups.length
    const running = rawGroups.filter((group) => group.status === 'running' || group.status === 'queued').length
    const completed = groups.filter((group) => group.status === 'completed').length
    const failed = groups.filter((group) => group.status === 'failed').length
    const completedInstances = groups.reduce((sum, group) => sum + (group.completed_tasks || 0), 0)
    const failedInstances = groups.reduce((sum, group) => sum + (group.failed_tasks || 0), 0)
    const finishedInstances = completedInstances + failedInstances

    return {
      total,
      pending: groups.filter((group) => group.status === 'pending').length,
      running,
      completed,
      failed,
      success_rate: finishedInstances > 0 ? (completedInstances / finishedInstances) * 100 : 0,
    }
  },

  async getTasks(id: number, params?: { page?: number; page_size?: number; status?: string }): Promise<PaginatedResponse<Task>> {
    const page = params?.page || 1
    const pageSize = params?.page_size || 10
    const res = await client.get<any>(`/v1/task-groups/${id}/instances`, {
      params: {
        status: params?.status,
        skip: (page - 1) * pageSize,
        limit: pageSize,
      },
    })
    return toPaginatedResponse(res.instances || [], page, pageSize)
  },
}
