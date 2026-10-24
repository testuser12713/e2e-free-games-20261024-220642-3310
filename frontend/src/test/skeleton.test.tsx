import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { buildDealsQuery, getDeals } from '../api/client'
import { DEFAULT_FILTERS } from '../api/types'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

describe('router frame', () => {
  it.each([
    ['/', 'deals-page'],
    ['/impressum', 'impressum-page'],
    ['/datenschutz', 'datenschutz-page'],
  ])('renders %s inside header, main and footer', (path, pageId) => {
    renderAt(path)
    const main = screen.getByRole('main')
    expect(screen.getByRole('banner')).toBeInTheDocument()
    expect(screen.getByRole('contentinfo')).toBeInTheDocument()
    expect(main).toContainElement(screen.getByTestId(pageId))
  })
})

describe('api client query string', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('omits platform "all" and empty values', () => {
    const params = new URLSearchParams(buildDealsQuery(DEFAULT_FILTERS))
    expect(params.has('platform')).toBe(false)
    expect(params.has('q')).toBe(false)
    expect(params.has('store')).toBe(false)
    expect(params.has('min_price')).toBe(false)
    expect(params.has('max_price')).toBe(false)
  })

  it('maps every set filter to its API parameter', () => {
    const params = new URLSearchParams(
      buildDealsQuery({
        q: ' Tropico ',
        platform: 'ps5',
        store: 'Epic Games Store',
        minPrice: '5',
        maxPrice: '30',
        sort: 'title',
        order: 'asc',
      }),
    )
    expect(params.get('q')).toBe('Tropico')
    expect(params.get('platform')).toBe('ps5')
    expect(params.get('store')).toBe('Epic Games Store')
    expect(params.get('min_price')).toBe('5')
    expect(params.get('max_price')).toBe('30')
    expect(params.get('sort')).toBe('title')
    expect(params.get('order')).toBe('asc')
  })

  it('getDeals requests /api/deals with that query and maps ErrorBody to ApiError', async () => {
    // Same-origin default: the run environment may set a base URL, so pin it here.
    vi.stubEnv('VITE_API_BASE_URL', '')
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({ error: { code: 'validation_error', message: 'bad limit', details: null } }),
        { status: 422, headers: { 'Content-Type': 'application/json' } },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(getDeals({ ...DEFAULT_FILTERS, platform: 'pc' })).rejects.toMatchObject({
      name: 'ApiError',
      status: 422,
      message: 'bad limit',
    })
    const url = String((fetchMock.mock.calls[0] as unknown[])[0])
    expect(url.startsWith('/api/deals?')).toBe(true)
    expect(new URLSearchParams(url.split('?')[1]).get('platform')).toBe('pc')
  })

  it('getDeals prefixes a configured VITE_API_BASE_URL', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://api.test/')
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ items: [], total: 0, limit: 20, offset: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await getDeals(DEFAULT_FILTERS)
    const url = String((fetchMock.mock.calls[0] as unknown[])[0])
    expect(url.startsWith('http://api.test/api/deals')).toBe(true)
  })
})
