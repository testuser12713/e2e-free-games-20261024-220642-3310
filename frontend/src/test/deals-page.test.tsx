import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, getDeals, getStores } from '../api/client'
import type { Deal, DealFilters, DealList } from '../api/types'
import { DEFAULT_FILTERS } from '../api/types'
import {
  filtersFromSearchParams,
  filtersToSearchParams,
  hasActiveFilters,
} from '../hooks/useDealFilters'
import DealsPage from '../pages/DealsPage'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, getDeals: vi.fn(), getStores: vi.fn() }
})

// FilterBar and StatusBar belong to other tickets: test doubles expose exactly
// the props contract DealsPage has to wire.
vi.mock('../components/FilterBar', () => {
  function FakeFilterBar(props: {
    filters: DealFilters
    stores: string[]
    onChange: (next: DealFilters) => void
    onReset: () => void
  }) {
    return (
      <div data-testid="fake-filter-bar">
        <span data-testid="fb-stores">{props.stores.join('|')}</span>
        <span data-testid="fb-q">{props.filters.q}</span>
        <button type="button" onClick={() => props.onChange({ ...props.filters, platform: 'ps5' })}>
          set-ps5
        </button>
        <button
          type="button"
          onClick={() => props.onChange({ ...props.filters, sort: 'title', order: 'asc' })}
        >
          sort-title
        </button>
        <button type="button" onClick={() => props.onChange({ ...props.filters, q: 'Trop' })}>
          type-q
        </button>
        <button type="button" onClick={props.onReset}>
          fb-reset
        </button>
      </div>
    )
  }
  return { default: FakeFilterBar, FilterBar: FakeFilterBar }
})

vi.mock('../components/StatusBar', () => {
  function FakeStatusBar(props: { onRefreshFinished: () => void }) {
    return (
      <button type="button" onClick={props.onRefreshFinished}>
        refresh-finished
      </button>
    )
  }
  return { default: FakeStatusBar, StatusBar: FakeStatusBar }
})

const getDealsMock = vi.mocked(getDeals)
const getStoresMock = vi.mocked(getStores)

function deal(id: number, title: string, overrides: Partial<Deal> = {}): Deal {
  return {
    id,
    title,
    store: 'Steam',
    platform: 'pc',
    original_price: 19.99,
    currency: 'EUR',
    url: `https://store.example.test/app/${id}`,
    image_url: null,
    starts_at: null,
    ends_at: null,
    first_seen_at: '2026-10-24T08:00:00Z',
    last_seen_at: '2026-10-24T08:00:00Z',
    ...overrides,
  }
}

function list(items: Deal[], total = items.length): DealList {
  return { items, total, limit: 20, offset: 0 }
}

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="location">{location.search}</output>
}

function renderPage(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/"
          element={
            <>
              <DealsPage />
              <LocationProbe />
            </>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

function lastFilters(): DealFilters {
  const calls = getDealsMock.mock.calls
  return calls[calls.length - 1][0]
}

beforeEach(() => {
  getStoresMock.mockResolvedValue(['Epic Games Store', 'Steam'])
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('DealsPage list', () => {
  it('renders every deal as a DealCard with the result count', async () => {
    getDealsMock.mockResolvedValue(
      list([deal(1, 'Ghostrunner'), deal(2, 'Moving Out 2', { platform: 'ps5' })]),
    )
    renderPage()

    const grid = await screen.findByTestId('deal-list')
    expect(within(grid).getAllByTestId('deal-card')).toHaveLength(2)
    expect(within(grid).getByText('Ghostrunner')).toBeInTheDocument()
    expect(screen.getByTestId('result-count')).toHaveTextContent('2 Spiele')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Gerade gratis für PC und PS5',
    )
    await waitFor(() =>
      expect(screen.getByTestId('fb-stores')).toHaveTextContent('Epic Games Store|Steam'),
    )
  })

  it('renders scraper titles as text and shop links with noopener noreferrer', async () => {
    getDealsMock.mockResolvedValue(list([deal(1, '<img src=x onerror=alert(1)>')]))
    renderPage()

    const card = await screen.findByTestId('deal-card')
    expect(within(card).getByText('<img src=x onerror=alert(1)>')).toBeInTheDocument()
    expect(card.querySelector('img[src="x"]')).toBeNull()
    const link = within(card).getByRole('link')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('says when only the first page of a larger result is shown', async () => {
    getDealsMock.mockResolvedValue(list([deal(1, 'Ghostrunner')], 25))
    renderPage()
    expect(await screen.findByTestId('result-count')).toHaveTextContent(
      '25 Spiele · die ersten 1 werden angezeigt',
    )
  })
})

describe('DealsPage filters and URL state', () => {
  it('reads the initial filters from the URL', async () => {
    getDealsMock.mockResolvedValue(list([deal(1, 'Moving Out 2', { platform: 'ps5' })]))
    renderPage('/?platform=ps5&store=Steam&sort=title&order=asc&min_price=5&q=Moving')

    await screen.findByTestId('deal-list')
    expect(getDealsMock).toHaveBeenCalledTimes(1)
    expect(lastFilters()).toEqual({
      q: 'Moving',
      platform: 'ps5',
      store: 'Steam',
      minPrice: '5',
      maxPrice: '',
      sort: 'title',
      order: 'asc',
    })
  })

  it('refetches on a filter change and writes it to the URL', async () => {
    getDealsMock.mockResolvedValue(list([deal(1, 'Ghostrunner')]))
    renderPage()
    await screen.findByTestId('deal-list')

    fireEvent.click(screen.getByText('set-ps5'))
    await waitFor(() => expect(lastFilters().platform).toBe('ps5'))
    expect(screen.getByTestId('location')).toHaveTextContent('?platform=ps5')

    fireEvent.click(screen.getByText('sort-title'))
    await waitFor(() => expect(lastFilters()).toMatchObject({ sort: 'title', order: 'asc' }))
    const params = new URLSearchParams(screen.getByTestId('location').textContent ?? '')
    expect(params.get('platform')).toBe('ps5')
    expect(params.get('sort')).toBe('title')
    expect(params.get('order')).toBe('asc')
  })

  it('debounces the title search', async () => {
    getDealsMock.mockResolvedValue(list([deal(1, 'Tropico 6')]))
    renderPage()
    await screen.findByTestId('deal-list')
    const callsBefore = getDealsMock.mock.calls.length

    fireEvent.click(screen.getByText('type-q'))
    // URL and field update at once, the request waits for the debounce.
    expect(screen.getByTestId('location')).toHaveTextContent('?q=Trop')
    expect(screen.getByTestId('fb-q')).toHaveTextContent('Trop')
    expect(getDealsMock.mock.calls.length).toBe(callsBefore)

    await waitFor(() => expect(lastFilters().q).toBe('Trop'))
  })

  it('aborts a stale request when the filters change', async () => {
    const signals: AbortSignal[] = []
    getDealsMock.mockImplementation((_filters, opts) => {
      if (opts?.signal) signals.push(opts.signal)
      if (signals.length === 1) {
        return new Promise<DealList>((_resolve, reject) => {
          opts?.signal?.addEventListener('abort', () =>
            reject(new DOMException('aborted', 'AbortError')),
          )
        })
      }
      return Promise.resolve(list([deal(2, 'Moving Out 2', { platform: 'ps5' })]))
    })
    renderPage()

    fireEvent.click(screen.getByText('set-ps5'))
    expect(await screen.findByText('Moving Out 2')).toBeInTheDocument()
    expect(signals[0].aborted).toBe(true)
    expect(screen.queryByTestId('error-state')).not.toBeInTheDocument()
  })

  it('reloads deals and stores when a refresh run finished', async () => {
    getDealsMock.mockResolvedValue(list([deal(1, 'Ghostrunner')]))
    renderPage()
    await screen.findByTestId('deal-list')
    await waitFor(() => expect(getStoresMock).toHaveBeenCalledTimes(1))
    const dealCalls = getDealsMock.mock.calls.length

    fireEvent.click(screen.getByText('refresh-finished'))
    await waitFor(() => expect(getDealsMock.mock.calls.length).toBe(dealCalls + 1))
    await waitFor(() => expect(getStoresMock).toHaveBeenCalledTimes(2))
  })
})

describe('DealsPage states', () => {
  it('shows skeleton cards while loading', async () => {
    let resolve: (value: DealList) => void = () => undefined
    getDealsMock.mockReturnValue(
      new Promise<DealList>((r) => {
        resolve = r
      }),
    )
    renderPage()

    expect(screen.getByText('Spiele werden geladen …')).toBeInTheDocument()
    expect(screen.getAllByTestId('deal-card-skeleton').length).toBeGreaterThan(0)

    await act(async () => resolve(list([deal(1, 'Ghostrunner')])))
    expect(screen.queryByTestId('deal-card-skeleton')).not.toBeInTheDocument()
    expect(screen.getByText('Ghostrunner')).toBeInTheDocument()
  })

  it('shows the error state with a working retry when the backend is unreachable', async () => {
    getDealsMock.mockRejectedValueOnce(new ApiError(0, 'Backend nicht erreichbar'))
    getDealsMock.mockResolvedValue(list([deal(1, 'Ghostrunner')]))
    renderPage()

    const error = await screen.findByTestId('error-state')
    expect(within(error).getByText('Backend nicht erreichbar')).toBeInTheDocument()
    fireEvent.click(within(error).getByRole('button', { name: /Erneut versuchen/ }))

    expect(await screen.findByText('Ghostrunner')).toBeInTheDocument()
    expect(screen.queryByTestId('error-state')).not.toBeInTheDocument()
  })

  it('shows the filtered empty state with a reset that clears URL and filters', async () => {
    getDealsMock.mockImplementation(async (filters) =>
      filters.platform === 'ps5' ? list([]) : list([deal(1, 'Ghostrunner')]),
    )
    renderPage('/?platform=ps5&sort=title')

    const empty = await screen.findByTestId('empty-filtered')
    expect(screen.getByTestId('result-count')).toHaveTextContent('0 Spiele')
    expect(screen.queryByTestId('empty-no-data')).not.toBeInTheDocument()

    fireEvent.click(within(empty).getByRole('button', { name: 'Filter zurücksetzen' }))
    expect(await screen.findByText('Ghostrunner')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent(/^$/)
    expect(lastFilters()).toEqual(DEFAULT_FILTERS)
  })

  it('shows the no-data state only when the unfiltered list is empty', async () => {
    getDealsMock.mockResolvedValue(list([]))
    renderPage('/?sort=title&order=asc')

    expect(await screen.findByTestId('empty-no-data')).toBeInTheDocument()
    expect(screen.queryByTestId('empty-filtered')).not.toBeInTheDocument()
  })
})

describe('useDealFilters URL mapping', () => {
  it('round-trips filters and omits defaults', () => {
    expect(filtersToSearchParams(DEFAULT_FILTERS).toString()).toBe('')
    const filters: DealFilters = {
      q: 'Tropico',
      platform: 'pc',
      store: 'Epic Games Store',
      minPrice: '5',
      maxPrice: '30.5',
      sort: 'ends_at',
      order: 'asc',
    }
    expect(filtersFromSearchParams(filtersToSearchParams(filters))).toEqual(filters)
  })

  it('falls back to defaults for malformed values', () => {
    const filters = filtersFromSearchParams(
      new URLSearchParams('platform=xbox&sort=price&order=up&min_price=abc&max_price=-3'),
    )
    expect(filters).toEqual(DEFAULT_FILTERS)
  })

  it('treats sorting alone as unfiltered', () => {
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, sort: 'title', order: 'asc' })).toBe(false)
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, store: 'GOG' })).toBe(true)
  })
})
