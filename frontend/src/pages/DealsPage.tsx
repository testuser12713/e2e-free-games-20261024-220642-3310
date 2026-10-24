import { useCallback, useEffect, useMemo, useState } from 'react'
import { ApiError, buildDealsQuery, getDeals, getStores } from '../api/client'
import type { DealFilters, DealList } from '../api/types'
import FilterBar from '../components/FilterBar'
import StatusBar from '../components/StatusBar'
import { DealCard, DealCardSkeleton, EmptyState, ErrorState } from '../components/ui'
import { hasActiveFilters, useDealFilters } from '../hooks/useDealFilters'

/** Delay before a typed title search is sent (ms). */
export const SEARCH_DEBOUNCE_MS = 300
/** Placeholder cards while the first list loads (design/mockups/deals-loading.html). */
const SKELETON_COUNT = 6

interface LoadedList {
  list: DealList
  /** The filters this list was requested with (decides which empty state applies). */
  filters: DealFilters
}

function isAbortError(err: unknown): boolean {
  return err instanceof DOMException && err.name === 'AbortError'
}

function toApiError(err: unknown): ApiError {
  return err instanceof ApiError ? err : new ApiError(-1, 'Unerwartete Antwort vom Backend')
}

function countLabel(total: number): string {
  return total === 1 ? '1 Spiel' : `${total} Spiele`
}

/** Debounces the title search; clearing it applies at once (reset, "x" in the field). */
function useDebouncedQuery(q: string): string {
  const [debounced, setDebounced] = useState(q)
  useEffect(() => {
    if (q === '') {
      setDebounced('')
      return undefined
    }
    const timer = window.setTimeout(() => setDebounced(q), SEARCH_DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [q])
  return debounced
}

/**
 * The deals list at "/" (design/mockups/index.html and its state screens):
 * status bar, filter bar, result count and the grid of DealCards, with the
 * loading, error and both empty states. Filter state lives in the URL.
 */
export default function DealsPage() {
  const { filters, setFilters, reset } = useDealFilters()
  const debouncedQ = useDebouncedQuery(filters.q)
  const requestFilters = useMemo<DealFilters>(
    () => ({ ...filters, q: debouncedQ }),
    [filters, debouncedQ],
  )
  const requestKey = buildDealsQuery(requestFilters)

  const [reloadKey, setReloadKey] = useState(0)
  const [loaded, setLoaded] = useState<LoadedList | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(true)
  const [stores, setStores] = useState<string[]>([])

  // Deals: refetched on every effective filter change; a newer request aborts the older one.
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    getDeals(requestFilters, { signal: controller.signal })
      .then((list) => {
        setLoaded({ list, filters: requestFilters })
        setError(null)
        setLoading(false)
      })
      .catch((err: unknown) => {
        if (isAbortError(err) || controller.signal.aborted) return
        setError(toApiError(err))
        setLoading(false)
      })
    return () => controller.abort()
    // requestKey is the serialized form of requestFilters: depending on it
    // instead of the object avoids a refetch when equal filters are re-created.
  }, [requestKey, reloadKey])

  // Store options for the filter bar; reloaded together with the list.
  useEffect(() => {
    let active = true
    getStores()
      .then((items) => {
        if (active) setStores(items)
      })
      .catch(() => {
        // The store filter then offers "Alle Shops" only; an unreachable backend
        // is reported by the deals request, which fails the same way.
        if (active) setStores([])
      })
    return () => {
      active = false
    }
  }, [reloadKey])

  const reload = useCallback(() => setReloadKey((key) => key + 1), [])

  const pageHead = (
    <div className="page-head">
      <h1>Gerade gratis für PC und PS5</h1>
      <p className="page-head__lead">
        Zeitlich begrenzte 100-%-Aktionen aus Epic, Steam, GOG, PlayStation Store und weiteren
        Shops – mit dem normalen Preis daneben.
      </p>
    </div>
  )

  // Backend unreachable: the whole screen is the error state (design/mockups/deals-error.html).
  if (error && error.status === 0) {
    return (
      <div data-testid="deals-page" style={{ display: 'contents' }}>
        {pageHead}
        <ErrorState
          detail="GET /api/deals – keine Antwort"
          onRetry={reload}
          retrying={loading}
        />
      </div>
    )
  }

  let content
  if (error) {
    // The backend answered, but with an error: keep the filters usable.
    content = (
      <ErrorState
        title="Liste konnte nicht geladen werden"
        text={error.message}
        detail={error.status > 0 ? `GET /api/deals – HTTP ${error.status}` : undefined}
        onRetry={reload}
        retrying={loading}
      />
    )
  } else if (!loaded) {
    content = (
      <>
        <div className="result-meta" aria-busy="true">
          <p className="result-meta__count" role="status">
            Spiele werden geladen …
          </p>
        </div>
        <ul className="deal-grid" aria-busy="true" data-testid="deal-list-loading">
          {Array.from({ length: SKELETON_COUNT }, (_, index) => (
            <li key={index} aria-hidden="true">
              <DealCardSkeleton />
            </li>
          ))}
        </ul>
      </>
    )
  } else if (loaded.list.items.length === 0) {
    content = hasActiveFilters(loaded.filters) ? (
      <>
        <div className="result-meta">
          <p className="result-meta__count" aria-live="polite" data-testid="result-count">
            {countLabel(0)}
          </p>
        </div>
        <EmptyState variant="filtered" onReset={reset} />
      </>
    ) : (
      <EmptyState variant="no-data" />
    )
  } else {
    const { items, total } = loaded.list
    content = (
      <>
        <div className="result-meta">
          <p className="result-meta__count" aria-live="polite" data-testid="result-count">
            {countLabel(total)}
            {items.length < total && (
              <span className="muted"> · die ersten {items.length} werden angezeigt</span>
            )}
          </p>
        </div>
        <ul className="deal-grid" aria-busy={loading} data-testid="deal-list">
          {items.map((deal) => (
            <li key={deal.id}>
              <DealCard deal={deal} />
            </li>
          ))}
        </ul>
      </>
    )
  }

  return (
    <div data-testid="deals-page" style={{ display: 'contents' }}>
      {pageHead}
      <StatusBar onRefreshFinished={reload} />
      <FilterBar filters={filters} stores={stores} onChange={setFilters} onReset={reset} />
      {content}
    </div>
  )
}
