import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, getSourceStatus, startRefresh } from '../api/client'
import type { SourceStatus, SourceStatusResponse } from '../api/types'
import {
  Button,
  InlineNotice,
  PillList,
  Progress,
  Skeleton,
  StatusPill,
  formatDateTime,
  type PillStatus,
} from './ui'

export interface StatusBarProps {
  /** Called once a run this bar triggered is no longer running. */
  onRefreshFinished: () => void
}

/** Delay between two status polls while a run is active. */
export const POLL_INTERVAL_MS = 2000
/** Consecutive failed polls after which the bar gives up and reports the error. */
const MAX_POLL_FAILURES = 3

/**
 * The sources the scraper knows (backend app/adapters/registry.py), in the order
 * of the mockups. A source without a SourceState row has never run: it is shown
 * as "noch kein Lauf", never as an error (design/mockups/deals-empty-no-data.html).
 */
const KNOWN_SOURCES: { name: string; label: string }[] = [
  { name: 'epic', label: 'Epic Games Store' },
  { name: 'steam', label: 'Steam' },
  { name: 'gog', label: 'GOG' },
  { name: 'playstation', label: 'PlayStation Store' },
  { name: 'gamerpower', label: 'GamerPower' },
]

function sourceLabel(name: string): string {
  return KNOWN_SOURCES.find((s) => s.name === name)?.label ?? name
}

interface SourceRow {
  name: string
  label: string
  status: PillStatus
  source: SourceStatus | null
}

function sourceRows(items: SourceStatus[]): SourceRow[] {
  const byName = new Map(items.map((item) => [item.name, item]))
  const names = [
    ...KNOWN_SOURCES.map((s) => s.name),
    ...items.map((item) => item.name).filter((n) => !KNOWN_SOURCES.some((s) => s.name === n)),
  ]
  return names.map((name) => {
    const source = byName.get(name) ?? null
    let status: PillStatus = 'idle'
    if (source && source.ok === true) status = 'ok'
    else if (source && source.ok === false) status = 'error'
    return { name, label: sourceLabel(name), status, source }
  })
}

/** The notice about the manual refresh, shown in the live region. */
type RefreshNotice =
  | { kind: 'running'; already: boolean }
  | { kind: 'done'; total: number; failed: number }
  | { kind: 'rate_limited' }
  | { kind: 'error'; message: string }

function errorMessage(err: unknown): string {
  if (err instanceof ApiError && err.status === 0) {
    return 'Der Server ist nicht erreichbar. Bitte prüfen Sie Ihre Verbindung und versuchen Sie es erneut.'
  }
  if (err instanceof ApiError) return `Der Server meldet: ${err.message}`
  return 'Ein unerwarteter Fehler ist aufgetreten. Bitte versuchen Sie es erneut.'
}

function Time({ value }: { value: string | null }) {
  const text = formatDateTime(value)
  if (!value || !text) return null
  return <time dateTime={value}>{text}</time>
}

function RefreshNoticeView({ notice }: { notice: RefreshNotice }) {
  switch (notice.kind) {
    case 'running':
      return (
        <InlineNotice
          tone="info"
          title={notice.already ? 'Aktualisierung läuft bereits.' : 'Aktualisierung läuft.'}
        >
          Die Quellen werden abgefragt, die Liste bleibt bis zum Abschluss unverändert.
        </InlineNotice>
      )
    case 'done':
      return (
        <InlineNotice tone="success" title="Aktualisierung abgeschlossen.">
          {notice.failed === 0
            ? `Alle ${notice.total} Quellen wurden abgefragt, die Liste ist auf dem neuesten Stand.`
            : `${notice.total} Quellen wurden abgefragt, ${notice.failed} davon mit Fehler. Die Angebote der übrigen Quellen sind auf dem neuesten Stand.`}
        </InlineNotice>
      )
    case 'rate_limited':
      return (
        <InlineNotice tone="warning" role="alert" title="Aktualisierung gerade nicht möglich.">
          Es wurden zu viele Anfragen gestellt. Bitte versuchen Sie es in einer Minute erneut.
        </InlineNotice>
      )
    case 'error':
      return (
        <InlineNotice tone="error" role="alert" title="Aktualisierung fehlgeschlagen.">
          {notice.message}
        </InlineNotice>
      )
  }
}

function SourceErrorNotice({ row, othersOk }: { row: SourceRow; othersOk: boolean }) {
  const source = row.source
  if (!source) return null
  return (
    <div data-testid="source-error-notice">
      <InlineNotice
        tone="error"
        title={`${row.label}: ${source.error?.trim() || 'Abruf fehlgeschlagen'}`}
      >
        {source.last_run_at && (
          <>
            (<Time value={source.last_run_at} />).{' '}
          </>
        )}
        {source.last_success_at ? (
          <>
            Die Angebote dieser Quelle stammen vom letzten erfolgreichen Lauf am{' '}
            <Time value={source.last_success_at} /> und bleiben erhalten.
          </>
        ) : (
          'Diese Quelle hatte noch keinen erfolgreichen Lauf.'
        )}
        {othersOk && ' Die übrigen Quellen sind aktuell.'}
      </InlineNotice>
    </div>
  )
}

/**
 * Last update, refresh button and per-source status — the `status-bar` region
 * of design/mockups/index.html with the states of deals-refreshing.html,
 * deals-refresh-limited.html and deals-source-error.html.
 */
export default function StatusBar({ onRefreshFinished }: StatusBarProps) {
  const [status, setStatus] = useState<SourceStatusResponse | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [polling, setPolling] = useState(false)
  const [notice, setNotice] = useState<RefreshNotice | null>(null)

  const mounted = useRef(true)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const onFinished = useRef(onRefreshFinished)
  onFinished.current = onRefreshFinished

  const clearTimer = useCallback(() => {
    if (timer.current !== null) {
      clearTimeout(timer.current)
      timer.current = null
    }
  }, [])

  /** Polls the status until the active run is over, then reports completion once. */
  const pollUntilDone = useCallback(
    (failures: number) => {
      clearTimer()
      timer.current = setTimeout(async () => {
        timer.current = null
        try {
          const next = await getSourceStatus()
          if (!mounted.current) return
          setStatus(next)
          setLoadError(null)
          if (next.running) {
            pollUntilDone(0)
            return
          }
          const failed = next.items.filter((item) => item.ok === false).length
          setPolling(false)
          setNotice({ kind: 'done', total: next.items.length, failed })
          onFinished.current()
        } catch (err) {
          if (!mounted.current) return
          if (failures + 1 < MAX_POLL_FAILURES) {
            pollUntilDone(failures + 1)
            return
          }
          setPolling(false)
          setNotice({ kind: 'error', message: errorMessage(err) })
        }
      }, POLL_INTERVAL_MS)
    },
    [clearTimer],
  )

  useEffect(() => {
    mounted.current = true
    getSourceStatus()
      .then((initial) => {
        if (!mounted.current) return
        setStatus(initial)
        // A scheduled run is already active: show it and report when it ends.
        if (initial.running) {
          setPolling(true)
          setNotice({ kind: 'running', already: true })
          pollUntilDone(0)
        }
      })
      .catch((err: unknown) => {
        if (!mounted.current) return
        setLoadError(errorMessage(err))
      })
    return () => {
      mounted.current = false
      clearTimer()
    }
  }, [clearTimer, pollUntilDone])

  async function handleRefresh() {
    if (polling) return
    setPolling(true)
    setNotice(null)
    try {
      const result = await startRefresh()
      if (!mounted.current) return
      if (result.started || result.reason === 'running') {
        setNotice({ kind: 'running', already: !result.started })
        pollUntilDone(0)
        return
      }
      setPolling(false)
      setNotice({ kind: 'rate_limited' })
    } catch (err) {
      if (!mounted.current) return
      setPolling(false)
      setNotice({ kind: 'error', message: errorMessage(err) })
    }
  }

  const loading = status === null && loadError === null
  const rows = sourceRows(status?.items ?? [])
  const failing = rows.filter((row) => row.status === 'error')
  const othersOk = failing.length === 1 && rows.every((r) => r.status !== 'idle')
  const updatedText = formatDateTime(status?.last_updated_at ?? null)

  return (
    <section
      className="status-bar"
      aria-label="Aktualität und Quellen"
      aria-busy={loading || undefined}
      data-testid="status-bar"
    >
      <div className="status-bar__row">
        {loading ? (
          <div className="status-bar__updated">
            <span>Zuletzt aktualisiert:</span>
            <Skeleton variant="line-lg" width="11rem" style={{ marginTop: '.25rem' }} />
          </div>
        ) : (
          <p className="status-bar__updated" data-testid="last-updated">
            <span>Zuletzt aktualisiert:</span>
            {status?.last_updated_at && updatedText ? (
              <time dateTime={status.last_updated_at}>{updatedText}</time>
            ) : (
              <span
                className="mono"
                style={{ color: 'var(--c-ink)', fontWeight: 600, fontSize: 'var(--fs-base)' }}
              >
                {status ? 'noch nie' : 'unbekannt'}
              </span>
            )}
          </p>
        )}
        <Button variant="secondary" icon="refresh" loading={polling} onClick={handleRefresh}>
          {polling ? 'Aktualisiere …' : 'Jetzt aktualisieren'}
        </Button>
      </div>
      {polling && <Progress />}
      <div>
        <p className="status-bar__sources-title">Quellen</p>
        {loading ? (
          <ul className="pill-list" aria-hidden="true">
            {KNOWN_SOURCES.map((s) => (
              <Skeleton key={s.name} as="li" variant="pill" />
            ))}
          </ul>
        ) : (
          <PillList aria-label="Status je Quelle">
            {rows.map((row) => (
              <StatusPill
                key={row.name}
                name={row.label}
                status={row.status}
                count={row.source?.deal_count ?? 0}
                title={row.status === 'error' ? (row.source?.error ?? undefined) : undefined}
              />
            ))}
          </PillList>
        )}
      </div>
      <div
        role="status"
        aria-live="polite"
        data-testid="status-live"
        style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-2)' }}
      >
        {loadError && (
          <InlineNotice tone="error" title="Quellenstatus konnte nicht geladen werden.">
            {loadError}
          </InlineNotice>
        )}
        {notice && <RefreshNoticeView notice={notice} />}
        {failing.map((row) => (
          <SourceErrorNotice key={row.name} row={row} othersOk={othersOk} />
        ))}
      </div>
    </section>
  )
}

export { StatusBar }
