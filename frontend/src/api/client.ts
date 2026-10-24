// Thin fetch wrappers around the backend API. The base URL comes from
// VITE_API_BASE_URL; empty (the default) means same origin.
import type { ApiErrorBody, DealFilters, DealList, SourceStatusResponse } from './types'

/** A failed API call. status 0 = the backend was not reachable at all. */
export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export interface RefreshResult {
  started: boolean
  reason?: 'running' | 'rate_limited'
}

function apiBase(): string {
  const raw = import.meta.env.VITE_API_BASE_URL
  const base = typeof raw === 'string' ? raw.trim() : ''
  return base.replace(/\/+$/, '')
}

function isErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== 'object' || value === null || !('error' in value)) return false
  const error = (value as { error: unknown }).error
  return (
    typeof error === 'object' &&
    error !== null &&
    typeof (error as { message?: unknown }).message === 'string'
  )
}

async function errorFrom(response: Response): Promise<ApiError> {
  let message = response.statusText || `HTTP ${response.status}`
  try {
    const body: unknown = await response.json()
    if (isErrorBody(body)) message = body.error.message
  } catch {
    // Body was not JSON (e.g. a proxy error page): keep the status text.
  }
  return new ApiError(response.status, message)
}

function isAbort(err: unknown): boolean {
  return err instanceof DOMException && err.name === 'AbortError'
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${apiBase()}${path}`, {
      ...init,
      headers: { Accept: 'application/json', ...init?.headers },
    })
  } catch (err) {
    // An aborted request is the caller's own decision, not a failure: pass it on.
    if (isAbort(err)) throw err
    throw new ApiError(0, 'Backend nicht erreichbar')
  }
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await send(path, { signal })
  if (!response.ok) throw await errorFrom(response)
  try {
    return (await response.json()) as T
  } catch {
    throw new ApiError(response.status, 'Ungültige Antwort vom Backend')
  }
}

/**
 * Query string for GET /api/deals: platform "all" and empty values are left
 * out, minPrice/maxPrice become min_price/max_price.
 */
export function buildDealsQuery(filters: DealFilters): string {
  const params = new URLSearchParams()
  const q = filters.q.trim()
  if (q) params.set('q', q)
  if (filters.platform !== 'all') params.set('platform', filters.platform)
  if (filters.store) params.set('store', filters.store)
  if (filters.sort) params.set('sort', filters.sort)
  if (filters.order) params.set('order', filters.order)
  const minPrice = filters.minPrice.trim()
  if (minPrice) params.set('min_price', minPrice)
  const maxPrice = filters.maxPrice.trim()
  if (maxPrice) params.set('max_price', maxPrice)
  return params.toString()
}

export function getDeals(filters: DealFilters, opts?: { signal?: AbortSignal }): Promise<DealList> {
  const query = buildDealsQuery(filters)
  return getJson<DealList>(query ? `/api/deals?${query}` : '/api/deals', opts?.signal)
}

export async function getStores(): Promise<string[]> {
  const body = await getJson<{ items: string[] }>('/api/stores')
  return body.items
}

export function getSourceStatus(): Promise<SourceStatusResponse> {
  return getJson<SourceStatusResponse>('/api/sources/status')
}

export async function startRefresh(): Promise<RefreshResult> {
  const response = await send('/api/refresh', { method: 'POST' })
  if (response.status === 202) return { started: true }
  if (response.status === 409) return { started: false, reason: 'running' }
  if (response.status === 429) return { started: false, reason: 'rate_limited' }
  throw await errorFrom(response)
}
