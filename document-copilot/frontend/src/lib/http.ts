import { env } from '@/lib/env'
import { supabase } from '@/lib/supabase'

export type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export type RequestOptions = {
  body?: unknown
  signal?: AbortSignal
  timeoutMs?: number
}

const DEFAULT_TIMEOUT_MS = 30_000

export class ApiError extends Error {
  readonly status: number
  readonly body: unknown
  // True when no HTTP response arrived at all (offline, CORS, server down, timeout).
  readonly isNetworkError: boolean
  readonly isTimeout: boolean

  constructor(
    message: string,
    init: { status: number; body?: unknown; isNetworkError?: boolean; isTimeout?: boolean },
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = init.status
    this.body = init.body
    this.isNetworkError = init.isNetworkError ?? false
    this.isTimeout = init.isTimeout ?? false
  }
}

async function authHeader(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function readBody(response: Response): Promise<unknown> {
  const text = await response.text()
  if (!text) return undefined
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

// FastAPI errors look like { detail: "message" }.
function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
    return body.detail
  }
  return fallback
}

export async function request<T>(
  method: Method,
  path: string,
  { body, signal, timeoutMs = DEFAULT_TIMEOUT_MS }: RequestOptions = {},
): Promise<T> {
  const timeout = AbortSignal.timeout(timeoutMs)
  let response: Response
  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, {
      method,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined && { 'Content-Type': 'application/json' }),
        ...(await authHeader()),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    })
  } catch (error) {
    if (signal?.aborted) throw error // the caller cancelled; not an API failure
    const isTimeout = timeout.aborted
    throw new ApiError(
      isTimeout
        ? 'The request timed out.'
        : 'Could not reach the server. Check your connection and try again.',
      { status: 0, isNetworkError: true, isTimeout },
    )
  }

  const data = await readBody(response)
  if (!response.ok) {
    throw new ApiError(errorMessage(data, response.statusText || 'Request failed'), {
      status: response.status,
      body: data,
    })
  }
  return data as T
}
