import client from './client'
import { Dataset, DatasetInstance, PaginatedResponse } from '@/types'

export const datasetsApi = {
  list: (params?: { page?: number; page_size?: number; name?: string }) => 
    client.get<any, PaginatedResponse<Dataset>>('/v1/datasets/', { params }),

  get: (id: number) => 
    client.get<any, Dataset>(`/v1/datasets/${id}`),

  create: (data: { name: string; description?: string }) => 
    client.post<any, Dataset>('/v1/datasets/', data),

  update: (id: number, data: { name?: string; description?: string }) => 
    client.put<any, Dataset>(`/v1/datasets/${id}`, data),

  delete: (id: number) => 
    client.delete(`/v1/datasets/${id}`),

  getInstances: (id: number, params?: { page?: number; page_size?: number; instance_id?: string }) => 
    client.get<any, PaginatedResponse<DatasetInstance>>(`/v1/datasets/${id}/instances`, { params }),

  createInstance: (id: number, data: { instance_id: string; data: Record<string, any> }) => 
    client.post<any, DatasetInstance>(`/v1/datasets/${id}/instances`, data),

  importInstances: (id: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return client.post<any, { imported: number; failed: number; errors: string[] }>(
      `/v1/datasets/${id}/import`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
  },

  updateInstance: (datasetId: number, instanceId: number, data: { data: Record<string, any> }) => 
    client.put<any, DatasetInstance>(`/v1/datasets/${datasetId}/instances/${instanceId}`, data),

  deleteInstance: (datasetId: number, instanceId: number) => 
    client.delete(`/v1/datasets/${datasetId}/instances/${instanceId}`),
}
