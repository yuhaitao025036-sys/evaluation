import client from './client'
import { Script } from '@/types'

export const scriptsApi = {
  list: (params?: { page?: number; page_size?: number; name?: string }) => 
    client.get<any, { items: Script[]; total: number; page: number; page_size: number; pages: number }>(
      '/v1/scripts/',
      { params }
    ),

  get: (id: number) => 
    client.get<any, Script>(`/v1/scripts/${id}`),

  scan: () => 
    client.post<any, { scanned: number; added: number; updated: number }>('/v1/scripts/scan'),
}
