import client from './client'

export const modelsApi = {
  list: () => 
    client.get<any, string[]>('/v1/models/'),

  inUse: () => 
    client.get<any, string[]>('/v1/comparisons/models-in-use'),
}
