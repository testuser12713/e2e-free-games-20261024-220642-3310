import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { Footer } from '../components/chrome/Footer'
import { Header } from '../components/chrome/Header'
import { GALLERY_DEALS, GALLERY_NOW, Gallery } from '../components/ui/Gallery'
import {
  Button,
  DealCard,
  EmptyState,
  ErrorState,
  formatDateTime,
  formatPrice,
  formatTimeLeft,
  isSafeHttpUrl,
} from '../components/ui'

function renderGallery() {
  render(<Gallery />)
  return screen.getByTestId('ui-gallery')
}

describe('Gallery renders every kit component in every state', () => {
  it('shows each specimen', () => {
    renderGallery()
    for (const id of [
      'button',
      'badge',
      'deal-card',
      'skeleton',
      'fields',
      'pill',
      'progress',
      'notice',
      'empty',
      'error',
      'prose',
    ]) {
      expect(screen.getByTestId(`gallery-${id}`)).toBeInTheDocument()
    }
  })

  it('buttons: variants, disabled and loading are visible states', () => {
    renderGallery()
    const section = screen.getByTestId('gallery-button')
    const primary = within(section).getByRole('button', { name: /Primär/ })
    expect(primary).toHaveClass('btn', 'btn--primary')
    fireEvent.click(primary)
    expect(primary).toHaveTextContent('Primär (1)')
    expect(within(section).getByRole('button', { name: 'Deaktiviert' })).toBeDisabled()
    const loading = within(section).getByRole('button', { name: /Aktualisiere/ })
    expect(loading).toBeDisabled()
    expect(loading).toHaveClass('is-loading')
    expect(loading).toHaveAttribute('aria-busy', 'true')
    expect(within(section).getByRole('button', { name: 'Filter zurücksetzen' })).toHaveClass(
      'btn--ghost',
    )
    const shop = within(section).getByRole('link', { name: 'Zum Shop' })
    expect(shop).toHaveAttribute('target', '_blank')
    expect(shop).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('platform badges for PC and PS5', () => {
    renderGallery()
    const section = screen.getByTestId('gallery-badge')
    expect(within(section).getByText('PC')).toHaveClass('badge', 'badge--pc')
    expect(within(section).getByText('PS5')).toHaveClass('badge', 'badge--ps5')
  })

  it('skeletons are decorative placeholders', () => {
    renderGallery()
    const section = screen.getByTestId('gallery-skeleton')
    const card = within(section).getByTestId('deal-card-skeleton')
    expect(card).toHaveAttribute('aria-hidden', 'true')
    expect(card.querySelectorAll('.skeleton').length).toBe(6)
    expect(section.querySelectorAll('li.skeleton').length).toBe(2)
  })

  it('fields are wired, can be disabled and can show an invalid price range', () => {
    renderGallery()
    const search = screen.getByLabelText('Titel suchen')
    fireEvent.change(search, { target: { value: 'Lantern' } })
    expect(search).toHaveValue('Lantern')

    const store = screen.getByLabelText('Shop')
    fireEvent.change(store, { target: { value: 'GOG' } })
    expect(store).toHaveValue('GOG')

    const fields = screen.getByTestId('gallery-fields')
    const ps5 = within(fields).getAllByRole('radio', { name: 'PS5' })[0]
    fireEvent.click(ps5)
    expect(ps5).toBeChecked()

    const min = within(fields).getAllByLabelText('Normalpreis ab')[0]
    fireEvent.change(min, { target: { value: '5' } })
    expect(min).toHaveValue(5)

    const disabled = screen.getByTestId('gallery-fields-disabled')
    expect(within(disabled).getByRole('searchbox')).toBeDisabled()
    expect(within(disabled).getByRole('combobox')).toBeDisabled()
    for (const radio of within(disabled).getAllByRole('radio')) expect(radio).toBeDisabled()
    for (const input of within(disabled).getAllByRole('spinbutton')) expect(input).toBeDisabled()

    const invalid = screen.getByTestId('gallery-price-invalid')
    for (const input of within(invalid).getAllByRole('spinbutton')) {
      expect(input).toHaveClass('input--error')
      expect(input).toHaveAttribute('aria-invalid', 'true')
    }
  })

  it('status pills for ok, error and idle sources', () => {
    renderGallery()
    const list = screen.getByRole('list', { name: 'Quellen' })
    const [ok, error, idle] = within(list).getAllByRole('listitem')
    expect(ok).toHaveClass('pill--ok')
    expect(ok).toHaveTextContent('Steam: ok3')
    expect(error).toHaveClass('pill--error')
    expect(error).toHaveTextContent('PlayStation Store: FehlerFehler')
    expect(idle).toHaveClass('pill--idle')
    expect(idle).toHaveTextContent('noch kein Lauf')
  })

  it('progress bar and notices in every tone', () => {
    renderGallery()
    expect(screen.getByRole('progressbar', { name: 'Aktualisierung läuft' })).toBeInTheDocument()
    const section = screen.getByTestId('gallery-notice')
    const tones = [...section.querySelectorAll('.notice')].map((n) => n.className)
    expect(tones).toEqual([
      'notice',
      'notice notice--success',
      'notice notice--warning',
      'notice notice--error',
      'notice notice--warning',
    ])
    expect(within(section).getByRole('alert')).toHaveTextContent(
      'Aktualisierung gerade nicht möglich.',
    )
  })

  it('empty states: filtered offers a working reset, no-data explains the next step', () => {
    renderGallery()
    const filtered = screen.getByTestId('empty-filtered')
    expect(within(filtered).getByRole('heading', { name: 'Keine Treffer' })).toBeInTheDocument()
    fireEvent.click(within(filtered).getByRole('button', { name: 'Filter zurücksetzen' }))
    expect(screen.getByTestId('gallery-resets')).toHaveTextContent('Zurückgesetzt: 1')

    const noData = screen.getByTestId('empty-no-data')
    expect(
      within(noData).getByRole('heading', { name: 'Noch keine Daten vorhanden' }),
    ).toBeInTheDocument()
    expect(within(noData).queryByRole('button')).toBeNull()
  })

  it('error state with detail and retry', () => {
    renderGallery()
    const error = screen.getByTestId('error-state')
    expect(error).toHaveAttribute('role', 'alert')
    expect(within(error).getByRole('heading', { name: 'Backend nicht erreichbar' })).toBeVisible()
    expect(within(error).getByText('GET /api/deals – keine Antwort')).toBeInTheDocument()
    expect(within(error).getByRole('button', { name: 'Erneut versuchen' })).toBeEnabled()
  })

  it('prose with data list, todo marks, list and labelled table', () => {
    renderGallery()
    const section = screen.getByTestId('gallery-prose')
    expect(section.querySelector('.prose')).not.toBeNull()
    expect(within(section).getByRole('region', { name: 'Angaben gemäß § 5 DDG' })).toBeVisible()
    expect(within(section).getByText('Name')).toBeInTheDocument()
    expect(section.querySelectorAll('.todo-mark').length).toBe(2)
    const table = within(section).getByRole('table')
    expect(within(table).getAllByRole('columnheader')).toHaveLength(4)
    const cells = within(table).getAllByRole('cell')
    expect(cells[0]).toHaveAttribute('data-label', 'Verarbeitung')
    expect(cells[3]).toHaveAttribute('data-label', 'Speicherdauer')
  })
})

describe('DealCard', () => {
  it('shows image, title, store, platform, normal price, end and a safe shop link', () => {
    render(<DealCard deal={GALLERY_DEALS.pc} now={GALLERY_NOW} />)
    const card = screen.getByTestId('deal-card')
    expect(within(card).getByRole('img', { name: 'Titelbild von Lantern Valley' })).toHaveAttribute(
      'src',
      'https://images.example.org/cover-1.jpg',
    )
    expect(within(card).getByRole('heading', { name: 'Lantern Valley' })).toBeInTheDocument()
    expect(within(card).getByText('Steam')).toHaveClass('deal-card__store')
    expect(within(card).getByText('PC')).toHaveClass('badge--pc')
    expect(within(card).getByText('Gratis')).toHaveClass('badge--free')
    expect(within(card).getByText('Normalpreis')).toBeInTheDocument()
    const price = card.querySelector('del.price')
    expect(price?.textContent).toMatch(/^29,99\s€$/)
    expect(within(card).getByText(/Aktion endet/)).toBeInTheDocument()
    expect(card.querySelector('time')).toHaveAttribute('datetime', '2026-10-29T17:00:00Z')
    expect(within(card).getByText('(in 5 Tagen)')).toBeInTheDocument()

    const link = within(card).getByRole('link', { name: /Zum Shop/ })
    expect(link).toHaveAttribute('href', 'https://store.steampowered.com/app/1')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(link).toHaveTextContent('(Lantern Valley, öffnet in neuem Tab)')
  })

  it('PS5 deal gets the PS5 badge', () => {
    render(<DealCard deal={GALLERY_DEALS.ps5} now={GALLERY_NOW} />)
    expect(screen.getByText('PS5')).toHaveClass('badge--ps5')
  })

  it('without image and without end date', () => {
    render(<DealCard deal={{ ...GALLERY_DEALS.noEnd, image_url: null }} now={GALLERY_NOW} />)
    expect(screen.queryByRole('img')).toBeNull()
    expect(screen.getByText('Aktionsende nicht bekannt')).toBeInTheDocument()
    expect(document.querySelector('del.price')?.textContent).toMatch(/^9,99\s\$$/)
  })

  it('drops an unsafe image URL and replaces an unsafe shop URL by a disabled button', () => {
    render(
      <DealCard
        deal={{ ...GALLERY_DEALS.unsafeUrl, image_url: 'javascript:alert(1)' }}
        now={GALLERY_NOW}
      />,
    )
    expect(screen.queryByRole('img')).toBeNull()
    expect(screen.queryByRole('link')).toBeNull()
    expect(screen.getByRole('button', { name: 'Kein Shop-Link verfügbar' })).toBeDisabled()
  })

  it('renders scraper markup as plain text (AC-16)', () => {
    const { container } = render(<DealCard deal={GALLERY_DEALS.markup} now={GALLERY_NOW} />)
    expect(
      screen.getByRole('heading', { name: '<img src=x onerror="alert(1)"> Night Shift' }),
    ).toBeInTheDocument()
    expect(screen.getByText('<b>Shop</b>')).toBeInTheDocument()
    expect(container.querySelector('b')).toBeNull()
    expect(container.querySelectorAll('img')).toHaveLength(1)
  })
})

describe('kit behaviour', () => {
  it('EmptyState and ErrorState hide their buttons without a handler (AC-12)', () => {
    render(
      <>
        <EmptyState variant="filtered" />
        <ErrorState />
      </>,
    )
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('Button calls its handler and defaults to type="button"', () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Los</Button>)
    const button = screen.getByRole('button', { name: 'Los' })
    expect(button).toHaveAttribute('type', 'button')
    fireEvent.click(button)
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('formats prices, dates and time left in German', () => {
    expect(formatPrice(29.99, 'EUR')).toMatch(/^29,99\s€$/)
    expect(formatPrice(5, 'XYZ1')).toBe('5,00 XYZ1')
    expect(formatDateTime(null)).toBeNull()
    expect(formatDateTime('not a date')).toBeNull()
    expect(formatDateTime('2026-10-29T17:00:00Z')).toMatch(/^\d{2}\.\d{2}\.2026, \d{2}:\d{2} Uhr$/)
    const now = new Date(2026, 9, 24, 10, 0)
    expect(formatDateTime(new Date(2026, 9, 24, 20, 0).toISOString(), now)).toBe('Heute, 20:00 Uhr')
    expect(formatTimeLeft(new Date(2026, 9, 24, 16, 30).toISOString(), now)).toBe('in 6 Std.')
    expect(formatTimeLeft(new Date(2026, 9, 24, 10, 20).toISOString(), now)).toBe('in 20 Min.')
    expect(formatTimeLeft(new Date(2026, 9, 25, 9, 0).toISOString(), now)).toBe('morgen')
    expect(formatTimeLeft(new Date(2026, 10, 2, 1, 59).toISOString(), now)).toBe('in 9 Tagen')
    expect(formatTimeLeft(new Date(2026, 9, 23).toISOString(), now)).toBeNull()
  })

  it('accepts only http(s) URLs', () => {
    expect(isSafeHttpUrl('https://example.org')).toBe(true)
    expect(isSafeHttpUrl('http://example.org')).toBe(true)
    expect(isSafeHttpUrl('javascript:alert(1)')).toBe(false)
    expect(isSafeHttpUrl('data:text/html,x')).toBe(false)
    expect(isSafeHttpUrl('')).toBe(false)
    expect(isSafeHttpUrl(null)).toBe(false)
  })
})

describe('chrome', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('header links home and footer links to Impressum and Datenschutz', () => {
    render(
      <MemoryRouter>
        <Header />
        <Footer />
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: /Gratis-Spiele/ })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: 'Impressum' })).toHaveAttribute('href', '/impressum')
    expect(screen.getByRole('link', { name: 'Datenschutzerklärung' })).toHaveAttribute(
      'href',
      '/datenschutz',
    )
  })

  it.each([
    ['Impressum', 'impressum-page'],
    ['Datenschutzerklärung', 'datenschutz-page'],
  ])('footer link %s navigates on every route', (name, pageId) => {
    // Pages may load data; this test is about the chrome, so no request leaves.
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('offline')
      }),
    )
    for (const start of ['/', '/impressum', '/datenschutz']) {
      const { unmount } = render(
        <MemoryRouter initialEntries={[start]}>
          <App />
        </MemoryRouter>,
      )
      const footer = screen.getByRole('contentinfo')
      fireEvent.click(within(footer).getByRole('link', { name }))
      expect(screen.getByTestId(pageId)).toBeInTheDocument()
      expect(screen.getByRole('banner')).toBeInTheDocument()
      unmount()
    }
  })
})
