// Shapes of the HTTP contract (SPEC "shared interface"). Timestamps are ISO 8601
// UTC strings exactly as the API sends them.

export type Platform = 'pc' | 'ps5'

/** One free deal (= DealOut of the API). */
export interface Deal {
  id: number
  title: string
  store: string
  platform: Platform
  original_price: number
  currency: string
  url: string
  image_url: string | null
  starts_at: string | null
  ends_at: string | null
  first_seen_at: string
  last_seen_at: string
}

/** GET /api/deals response. */
export interface DealList {
  items: Deal[]
  total: number
  limit: number
  offset: number
}

/** Last run of one source (= SourceStatusOut of the API). */
export interface SourceStatus {
  name: string
  last_run_at: string | null
  ok: boolean | null
  error: string | null
  deal_count: number
  last_success_at: string | null
}

/** GET /api/sources/status response. */
export interface SourceStatusResponse {
  items: SourceStatus[]
  last_updated_at: string | null
  running: boolean
}

/** The uniform error body of every non-2xx answer. */
export interface ApiErrorBody {
  error: {
    code: string
    message: string
    details: object[] | null
  }
}

export type SortKey = 'title' | 'original_price' | 'ends_at' | 'first_seen'

/** Filter state of the deals list; every field is a string as typed by the user. */
export interface DealFilters {
  q: string
  platform: 'all' | Platform
  /** "" = all stores */
  store: string
  minPrice: string
  maxPrice: string
  sort: SortKey
  order: 'asc' | 'desc'
}

export const DEFAULT_FILTERS: DealFilters = {
  q: '',
  platform: 'all',
  store: '',
  minPrice: '',
  maxPrice: '',
  sort: 'first_seen',
  order: 'desc',
}
