import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { DEFAULT_FILTERS } from '../api/types'
import type { DealFilters, SortKey } from '../api/types'

// URL parameter names mirror the API's query parameters, so a shared link reads
// like the request it causes (e.g. /?platform=ps5&sort=title&order=asc).
const PARAM = {
  q: 'q',
  platform: 'platform',
  store: 'store',
  minPrice: 'min_price',
  maxPrice: 'max_price',
  sort: 'sort',
  order: 'order',
} as const

const SORT_KEYS: readonly SortKey[] = ['title', 'original_price', 'ends_at', 'first_seen']
// Non-negative decimal as typed into a number field ("5", "19.99", "0.5").
const PRICE_PATTERN = /^\d+(?:[.,]\d+)?$/

function readPrice(raw: string | null): string {
  const value = (raw ?? '').trim()
  return PRICE_PATTERN.test(value) ? value.replace(',', '.') : ''
}

/**
 * Reads filters from a query string. Unknown or malformed values fall back to
 * the default, so a hand-edited or outdated URL never produces a request the
 * API would reject.
 */
export function filtersFromSearchParams(params: URLSearchParams): DealFilters {
  const platform = params.get(PARAM.platform)
  const sort = params.get(PARAM.sort)
  const order = params.get(PARAM.order)
  return {
    q: params.get(PARAM.q) ?? DEFAULT_FILTERS.q,
    platform: platform === 'pc' || platform === 'ps5' ? platform : DEFAULT_FILTERS.platform,
    store: params.get(PARAM.store) ?? DEFAULT_FILTERS.store,
    minPrice: readPrice(params.get(PARAM.minPrice)),
    maxPrice: readPrice(params.get(PARAM.maxPrice)),
    sort: SORT_KEYS.includes(sort as SortKey) ? (sort as SortKey) : DEFAULT_FILTERS.sort,
    order: order === 'asc' || order === 'desc' ? order : DEFAULT_FILTERS.order,
  }
}

/** Writes filters to a query string; values equal to the default are left out. */
export function filtersToSearchParams(filters: DealFilters): URLSearchParams {
  const params = new URLSearchParams()
  if (filters.q) params.set(PARAM.q, filters.q)
  if (filters.platform !== DEFAULT_FILTERS.platform) params.set(PARAM.platform, filters.platform)
  if (filters.store) params.set(PARAM.store, filters.store)
  if (filters.minPrice) params.set(PARAM.minPrice, filters.minPrice)
  if (filters.maxPrice) params.set(PARAM.maxPrice, filters.maxPrice)
  if (filters.sort !== DEFAULT_FILTERS.sort) params.set(PARAM.sort, filters.sort)
  if (filters.order !== DEFAULT_FILTERS.order) params.set(PARAM.order, filters.order)
  return params
}

/** True when a filter narrows the list (sorting alone does not). */
export function hasActiveFilters(filters: DealFilters): boolean {
  return (
    filters.q.trim() !== '' ||
    filters.platform !== DEFAULT_FILTERS.platform ||
    filters.store !== '' ||
    filters.minPrice.trim() !== '' ||
    filters.maxPrice.trim() !== ''
  )
}

/**
 * Filter state of the deals list, mirrored in the URL query string so that a
 * reload, a bookmark or a shared link keeps it. Updates replace the current
 * history entry instead of adding one per keystroke.
 */
export function useDealFilters(): {
  filters: DealFilters
  setFilters: (next: DealFilters) => void
  reset: () => void
} {
  const [searchParams, setSearchParams] = useSearchParams()
  const key = searchParams.toString()
  // Memoized on the serialized query: same URL -> same filters object, so
  // effects depending on `filters` only rerun when the URL really changed.
  const filters = useMemo(() => filtersFromSearchParams(new URLSearchParams(key)), [key])

  const setFilters = useCallback(
    (next: DealFilters) => setSearchParams(filtersToSearchParams(next), { replace: true }),
    [setSearchParams],
  )
  const reset = useCallback(
    () => setSearchParams(new URLSearchParams(), { replace: true }),
    [setSearchParams],
  )

  return { filters, setFilters, reset }
}

export default useDealFilters
