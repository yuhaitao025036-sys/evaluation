import client from './client'
import { Dataset, DatasetInstance, PaginatedResponse } from '@/types'

export interface ScanDatasetsResponse {
  message: string
  newly_registered: number
  skipped_existing?: number
  scanned_files?: number
  datasets: Array<{
    id: number
    name: string
    file_name: string
    total_instances: number
  }>
}

const toPaginatedResponse = <T>(items: T[], page = 1, pageSize = 10, total = items.length): PaginatedResponse<T> => ({
  items,
  total,
  page,
  page_size: pageSize,
  pages: Math.max(1, Math.ceil(total / pageSize)),
})

export const datasetsApi = {
  async list(params?: { page?: number; page_size?: number; name?: string }): Promise<PaginatedResponse<Dataset>> {
    const page = params?.page || 1
    const pageSize = params?.page_size || 10
    const datasets = await client.get<Dataset[]>('/v1/datasets', {
      params: {
        skip: (page - 1) * pageSize,
        limit: pageSize,
      },
    })
    const filtered = params?.name
      ? datasets.filter((dataset) => dataset.name.toLowerCase().includes(params.name!.toLowerCase()))
      : datasets
    return toPaginatedResponse(filtered, page, pageSize)
  },

  get: (id: number): Promise<Dataset> =>
    client.get(`/v1/datasets/${id}`),

  scan: (): Promise<ScanDatasetsResponse> =>
    client.post('/v1/datasets/scan'),

  update: (id: number, _data?: { name?: string; description?: string }): Promise<Dataset> =>
    client.get(`/v1/datasets/${id}`),

  delete: (_id?: number): Promise<{ message: string }> =>
    Promise.reject(new Error('后端当前未提供删除数据集接口')),

  async getInstances(id: number, params?: { page?: number; page_size?: number; instance_id?: string }): Promise<PaginatedResponse<DatasetInstance>> {
    const page = params?.page || 1
    const pageSize = params?.page_size || 10
    const res = await client.get<{ dataset_id: number; total: number; skip: number; limit: number; instances: DatasetInstance[] }>(`/v1/datasets/${id}/instances`, {
      params: {
        skip: (page - 1) * pageSize,
        limit: pageSize,
        instance_id: params?.instance_id,
      },
    })
    return toPaginatedResponse(res.instances, page, pageSize, res.total)
  },

  createInstance: (_id?: number, _data?: { instance_id: string; data: Record<string, any> }): Promise<DatasetInstance> =>
    Promise.reject(new Error('后端当前未提供创建数据实例接口')),

  importInstances: (id: number, params?: { start_index?: number; end_index?: number }): Promise<{ imported: number; failed: number; errors: string[] }> =>
    client.post<any>(`/v1/datasets/${id}/import`, null, { params }).then((res) => ({
      imported: res.imported_count || 0,
      failed: 0,
      errors: [],
    })),

  updateInstance: (_datasetId?: number, _instanceId?: number, _data?: { data: Record<string, any> }): Promise<DatasetInstance> =>
    Promise.reject(new Error('后端当前未提供更新数据实例接口')),

  deleteInstance: (_datasetId?: number, _instanceId?: number): Promise<{ message: string }> =>
    Promise.reject(new Error('后端当前未提供删除数据实例接口')),
}
