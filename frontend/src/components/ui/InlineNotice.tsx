import type { ReactNode } from 'react'
import { Icon, type IconName } from './icons'
import './ui.css'

export type NoticeTone = 'info' | 'success' | 'warning' | 'error'

const DEFAULT_ICON: Record<NoticeTone, IconName> = {
  info: 'info',
  success: 'check-circle',
  warning: 'warning',
  error: 'warning',
}

export interface InlineNoticeProps {
  tone?: NoticeTone
  /** Bold lead-in, e.g. "Aktualisierung läuft." */
  title?: ReactNode
  children?: ReactNode
  /** Overrides the tone's icon (the legal pages pair "warning" with "info"). */
  icon?: IconName
  /** "alert" for a notice that must interrupt (design/mockups/deals-refresh-limited.html). */
  role?: 'alert' | 'status'
}

/**
 * One-line notice (design/mockups/styles.css:308-318): info while a run is
 * active, success when it finished, warning when a refresh was refused,
 * error for a failed source.
 */
export function InlineNotice({ tone = 'info', title, children, icon, role }: InlineNoticeProps) {
  const className = tone === 'info' ? 'notice' : `notice notice--${tone}`
  return (
    <div className={className} role={role} data-tone={tone}>
      <Icon name={icon ?? DEFAULT_ICON[tone]} />
      <p>
        {title != null && <span className="notice__title">{title}</span>}
        {title != null && children != null && ' '}
        {children}
      </p>
    </div>
  )
}

export default InlineNotice
