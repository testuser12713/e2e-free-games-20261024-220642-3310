import type { ReactNode } from 'react'
import { Icon, type IconName } from './icons'
import './ui.css'

export type PillStatus = 'ok' | 'error' | 'idle'

const ICONS: Record<PillStatus, IconName> = {
  ok: 'check-circle',
  error: 'warning',
  idle: 'idle-circle',
}

const SPOKEN: Record<PillStatus, string> = {
  ok: 'ok',
  error: 'Fehler',
  idle: 'noch kein Lauf',
}

export interface StatusPillProps {
  /** Source name, e.g. "Steam". */
  name: string
  status: PillStatus
  /** Deal count shown on an ok pill (design/mockups/index.html:52). */
  count?: number
  /** Tooltip, e.g. the error message of a failed source. */
  title?: string
}

/**
 * Status of one source (design/mockups/index.html:45-53,
 * deals-source-error.html "pill--error", deals-empty-no-data.html "pill--idle").
 * Render it as a child of PillList.
 */
export function StatusPill({ name, status, count, title }: StatusPillProps) {
  const trailing = status === 'ok' ? String(count ?? 0) : SPOKEN[status]
  return (
    <li className={`pill pill--${status}`} title={title} data-status={status}>
      <Icon name={ICONS[status]} />
      <span>
        {name}
        <span className="visually-hidden">: {SPOKEN[status]}</span>
      </span>
      <span className="pill__count">{trailing}</span>
    </li>
  )
}

export interface PillListProps {
  children: ReactNode
  'aria-label'?: string
}

/** The wrapping list of source pills (design/mockups/styles.css:237). */
export function PillList({ children, ...rest }: PillListProps) {
  return (
    <ul className="pill-list" {...rest}>
      {children}
    </ul>
  )
}

export default StatusPill
