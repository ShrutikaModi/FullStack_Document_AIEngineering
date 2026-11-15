import { request, type RequestOptions } from '@/lib/http'

type Options = Omit<RequestOptions, 'body'>

export const api = {
  get: <T>(path: string, options?: Options) => request<T>('GET', path, options),
  post: <T>(path: string, body?: unknown, options?: Options) =>
    request<T>('POST', path, { ...options, body }),
  put: <T>(path: string, body?: unknown, options?: Options) =>
    request<T>('PUT', path, { ...options, body }),
  patch: <T>(path: string, body?: unknown, options?: Options) =>
    request<T>('PATCH', path, { ...options, body }),
  delete: <T>(path: string, options?: Options) => request<T>('DELETE', path, options),
}

export { ApiError } from '@/lib/http'
