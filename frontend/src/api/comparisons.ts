import client from './client'
import { Comparison, PaginatedResponse, ComparisonResult, ModelComparisonSummary, TagComparisonSummary } from '@/types'

export const comparisonsApi = {
  list: (params?: { page?: number; page_size?: number; model?: string }) => 
    client.get<any, PaginatedResponse<Comparison>>('/v1/comparisons/', { params }),

  get: (id: number) => 
    client.get<any, Comparison>(`/v1/comparisons/${id}`),

  create: (data: {
    name: string
    description?: string
    baseline_tag: string
    comparison_tags: string[]
    model?: string
    filter_conditions?: Record<string, any>
  }) => client.post<any, Comparison>('/v1/comparisons/', data),

  delete: (id: number) => 
    client.delete(`/v1/comparisons/${id}`),

  compareByModels: (params: {
    tag: string
    models: string[]
    filter_conditions?: Record<string, any>
  }) => client.post<any, ModelComparisonSummary>('/v1/comparisons/compare-models', params),

  compareByTags: (params: {
    model: string
    baseline_tag: string
    comparison_tags: string[]
    filter_conditions?: Record<string, any>
  }) => client.post<any, TagComparisonSummary>('/v1/comparisons/compare-tags', params),

  compareInstance: (instanceId: string, params: {
    baseline_tag: string
    comparison_tags: string[]
    model?: string
  }) => client.get<any, ComparisonResult>(`/v1/comparisons/instance/${instanceId}`, { params }),

  getTags: () => 
    client.get<any, string[]>('/v1/comparisons/tags'),

  getModelsInUse: () => 
    client.get<any, string[]>('/v1/comparisons/models-in-use'),
}
