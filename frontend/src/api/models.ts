import client from './client'

export const modelsApi = {
  list: (): Promise<string[]> =>
    client.get('/v1/models/'),

  inUse: (): Promise<string[]> =>
    client.get('/v1/comparisons/models-in-use'),
}
