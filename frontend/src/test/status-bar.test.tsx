import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { SourceStatus, SourceStatusResponse } from '../api/types'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, getSourceStatus: vi.fn(), startRefresh: vi.fn() }
})

import { ApiError, getSourceStatus, startRefresh } from '../api/client'
import StatusBar, { POLL_INTERVAL_MS } from '../components/StatusBar'

const mockStatus = vi.mocked(getSourceStatus)
const mockRefresh = vi.mocked(startRefresh)

function source(name: string, overrides: Partial<SourceStatus> = {}): SourceStatus {
  return {
    name,
    last_run_at: '2026-10-24T12:02:00Z',
    ok: true,
    error: null,
    deal_count: 2,
    last_success_at: '2026-10-24T12:02:00Z',
    ...overrides,
  }
}

const ALL_OK = ['epic', 'steam', 'gog', 'playstation', 'gamerpower'].map((n) => source(n))

function response(overrides: Partial<SourceStatusResponse> = {}): SourceStatusResponse {
  return { items: ALL_OK, last_updated_at: '2026-10-24T12:02:00Z', running: false, ...overrides }
}

async function flush() {
  await act(async () => {
    await Promise.resolve()
  })
}

async function advancePoll() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS)
  })
}

function refreshButton() {
  return screen.getByRole('button', { name: /aktualisier/i })
}

beforeEach(() => {
  vi.useFakeTimers()
  mockStatus.mockReset()
  mockRefresh.mockReset()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('StatusBar', () => {
  it('idle: shows last update, enabled button and one ok pill per source', async () => {
    mockStatus.mockResolvedValue(response())
    render(<StatusBar onRefreshFinished={vi.fn()} />)
    await flush()

    const updated = screen.getByTestId('last-updated')
    expect(updated).toHaveTextContent('Zuletzt aktualisiert:')
    const time = within(updated).getByText(/2026/)
    expect(time.tagName).toBe('TIME')
    expect(time).toHaveAttribute('datetime', '2026-10-24T12:02:00Z')
    expect(time.textContent).toMatch(/^24\.10\.2026, \d{2}:\d{2} Uhr$/)

    const button = refreshButton()
    expect(button).toHaveTextContent('Jetzt aktualisieren')
    expect(button).toBeEnabled()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()

    const pills = within(screen.getByRole('list', { name: 'Status je Quelle' })).getAllByRole(
      'listitem',
    )
    expect(pills).toHaveLength(5)
    expect(pills.every((p) => p.getAttribute('data-status') === 'ok')).toBe(true)
    expect(screen.getByText('Epic Games Store')).toBeInTheDocument()
  })

  it('shows a neutral text when nothing has run yet and marks unknown sources as idle', async () => {
    mockStatus.mockResolvedValue(response({ items: [], last_updated_at: null }))
    render(<StatusBar onRefreshFinished={vi.fn()} />)
    await flush()

    expect(screen.getByTestId('last-updated')).toHaveTextContent('noch nie')
    const pills = screen.getAllByRole('listitem')
    expect(pills.every((p) => p.getAttribute('data-status') === 'idle')).toBe(true)
    expect(screen.queryByTestId('source-error-notice')).not.toBeInTheDocument()
  })

  it('progress then completion: polls until running is false and calls onRefreshFinished once', async () => {
    const onFinished = vi.fn()
    mockStatus
      .mockResolvedValueOnce(response())
      .mockResolvedValueOnce(response({ running: true }))
      .mockResolvedValueOnce(response({ running: false, last_updated_at: '2026-10-24T13:30:00Z' }))
    mockRefresh.mockResolvedValue({ started: true })

    render(<StatusBar onRefreshFinished={onFinished} />)
    await flush()
    fireEvent.click(refreshButton())
    await flush()

    expect(mockRefresh).toHaveBeenCalledTimes(1)
    expect(refreshButton()).toBeDisabled()
    expect(refreshButton()).toHaveTextContent('Aktualisiere …')
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
    expect(screen.getByText('Aktualisierung läuft.')).toBeInTheDocument()

    await advancePoll()
    expect(refreshButton()).toBeDisabled()
    expect(onFinished).not.toHaveBeenCalled()

    await advancePoll()
    expect(screen.getByText('Aktualisierung abgeschlossen.')).toBeInTheDocument()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    expect(refreshButton()).toBeEnabled()
    expect(screen.getByTestId('last-updated').querySelector('time')).toHaveAttribute(
      'datetime',
      '2026-10-24T13:30:00Z',
    )
    expect(onFinished).toHaveBeenCalledTimes(1)

    await advancePoll()
    expect(mockStatus).toHaveBeenCalledTimes(3)
    expect(onFinished).toHaveBeenCalledTimes(1)
  })

  it('409 reason "running": shows an already-running notice and still polls to completion', async () => {
    const onFinished = vi.fn()
    mockStatus
      .mockResolvedValueOnce(response())
      .mockResolvedValueOnce(response({ running: false }))
    mockRefresh.mockResolvedValue({ started: false, reason: 'running' })

    render(<StatusBar onRefreshFinished={onFinished} />)
    await flush()
    fireEvent.click(refreshButton())
    await flush()

    expect(screen.getByText('Aktualisierung läuft bereits.')).toBeInTheDocument()
    expect(refreshButton()).toBeDisabled()

    await advancePoll()
    expect(screen.getByText('Aktualisierung abgeschlossen.')).toBeInTheDocument()
    expect(onFinished).toHaveBeenCalledTimes(1)
  })

  it('429 reason "rate_limited": shows a try-again-later notice and does not poll', async () => {
    const onFinished = vi.fn()
    mockStatus.mockResolvedValue(response())
    mockRefresh.mockResolvedValue({ started: false, reason: 'rate_limited' })

    render(<StatusBar onRefreshFinished={onFinished} />)
    await flush()
    fireEvent.click(refreshButton())
    await flush()

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Aktualisierung gerade nicht möglich.')
    expect(alert).toHaveTextContent(/erneut/)
    expect(refreshButton()).toBeEnabled()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()

    await advancePoll()
    expect(mockStatus).toHaveBeenCalledTimes(1)
    expect(onFinished).not.toHaveBeenCalled()
  })

  it('network failure on refresh: shows an understandable error and re-enables the button', async () => {
    mockStatus.mockResolvedValue(response())
    mockRefresh.mockRejectedValue(new ApiError(0, 'Backend nicht erreichbar'))

    render(<StatusBar onRefreshFinished={vi.fn()} />)
    await flush()
    fireEvent.click(refreshButton())
    await flush()

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Aktualisierung fehlgeschlagen.')
    expect(alert).toHaveTextContent('nicht erreichbar')
    expect(refreshButton()).toBeEnabled()
  })

  it('a failing source is marked Fehler and its error text is visible', async () => {
    mockStatus.mockResolvedValue(
      response({
        items: ALL_OK.map((s) =>
          s.name === 'playstation'
            ? source('playstation', {
                ok: false,
                error: 'Zeitüberschreitung beim Abruf',
                last_success_at: '2026-10-24T06:02:00Z',
              })
            : s,
        ),
      }),
    )
    render(<StatusBar onRefreshFinished={vi.fn()} />)
    await flush()

    const pill = screen.getByText('PlayStation Store').closest('li')
    expect(pill).toHaveAttribute('data-status', 'error')
    expect(pill).toHaveTextContent('Fehler')

    const notice = screen.getByTestId('source-error-notice')
    expect(notice).toHaveTextContent('PlayStation Store: Zeitüberschreitung beim Abruf')
    expect(notice).toHaveTextContent('letzten erfolgreichen Lauf')
    expect(notice).toHaveTextContent('Die übrigen Quellen sind aktuell.')
  })

  it('shows an error notice when the status cannot be loaded, keeping the button usable', async () => {
    mockStatus.mockRejectedValue(new ApiError(0, 'Backend nicht erreichbar'))
    render(<StatusBar onRefreshFinished={vi.fn()} />)
    await flush()

    expect(screen.getByText('Quellenstatus konnte nicht geladen werden.')).toBeInTheDocument()
    expect(screen.getByTestId('last-updated')).toHaveTextContent('unbekannt')
    expect(refreshButton()).toBeEnabled()
  })
})
