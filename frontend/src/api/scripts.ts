import client from './client'
import { PaginatedResponse, Script } from '@/types'

export interface ScanScriptsResponse {
  message: string
  registered_count: number
  updated_count: number
  deleted_count: number
  scripts: Array<{
    id: number
    file_name: string
    status: 'registered' | 'updated'
  }>
}

const toPaginatedResponse = <T>(items: T[], page = 1, pageSize = 10, total = items.length): PaginatedResponse<T> => ({
  items,
  total,
  page,
  page_size: pageSize,
  pages: Math.max(1, Math.ceil(total / pageSize)),
})

export const scriptsApi = {
  async list(params?: { page?: number; page_size?: number; name?: string }): Promise<PaginatedResponse<Script>> {
    const page = params?.page || 1
    const pageSize = params?.page_size || 10
    const scripts = await client.get<Script[]>('/v1/scripts', {
      params: {
        offset: (page - 1) * pageSize,
        limit: pageSize,
      },
    })
    const filtered = params?.name
      ? scripts.filter((script) => (script.file_name || script.name || '').toLowerCase().includes(params.name!.toLowerCase()))
      : scripts
    return toPaginatedResponse(filtered, page, pageSize)
  },

  get: (id: number): Promise<Script> =>
    client.get(`/v1/scripts/${id}`),

  scan: (): Promise<ScanScriptsResponse> =>
    client.post('/v1/scripts/scan'),
}
