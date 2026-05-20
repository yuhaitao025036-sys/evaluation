import client from './client'
import type {
  CompareBatchesRequest,
  CompareByModelsRequest,
  CompareByTagsRequest,
  CompareInstanceRequest,
  ComparisonMetadata,
  ComparisonResponse,
  InstanceComparisonResponse,
} from '@/types'

export const comparisonsApi = {
  getMetadata(): Promise<ComparisonMetadata> {
    return client.get('/v1/comparisons/metadata')
  },

  compareBatches(params: CompareBatchesRequest): Promise<ComparisonResponse> {
    return client.post('/v1/comparisons/compare-batches', params)
  },

  compareByModels(params: CompareByModelsRequest): Promise<ComparisonResponse> {
    return client.post('/v1/comparisons/compare-by-models', params)
  },

  compareByTags(params: CompareByTagsRequest): Promise<ComparisonResponse> {
    return client.post('/v1/comparisons/compare-by-tags', params)
  },

  compareInstance(params: CompareInstanceRequest): Promise<InstanceComparisonResponse> {
    return client.post('/v1/comparisons/compare-instance', params)
  },

  getPatchContent(batchId: number, instanceId: string): Promise<{ content: string }> {
    return client.get(`/v1/batches/${batchId}/tasks/${encodeURIComponent(instanceId)}/patch-content`)
  },

  getTags(): Promise<string[]> {
    return client.get('/v1/comparisons/tags')
  },

  getModelsInUse(): Promise<string[]> {
    return client.get('/v1/comparisons/models-in-use')
  },
}
