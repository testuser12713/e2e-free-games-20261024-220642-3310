import type { ReactNode } from 'react'
import { Button } from './Button'
import { Icon } from './icons'
import './ui.css'

export interface ErrorStateProps {
  title?: string
  text?: ReactNode
  /** Technical detail line, e.g. "GET /api/deals – keine Antwort". */
  detail?: string
  /** Shows "Erneut versuchen"; the button appears only with a handler (AC-12). */
  onRetry?: () => void
  /** Disables the retry button while a retry is in flight. */
  retrying?: boolean
}

/** The list could not be loaded (design/mockups/deals-error.html:31-45). */
export function ErrorState({
  title = 'Backend nicht erreichbar',
  text = 'Die Liste konnte nicht geladen werden. Prüfen Sie Ihre Verbindung oder ob der Dienst läuft, und versuchen Sie es erneut.',
  detail,
  onRetry,
  retrying = false,
}: ErrorStateProps) {
  return (
    <div className="state state--error" role="alert" data-testid="error-state">
      <Icon name="plug" className="state__icon" />
      <h2>{title}</h2>
      <p className="state__text">{text}</p>
      {detail && <p className="state__detail">{detail}</p>}
      {onRetry && (
        <Button variant="primary" icon="refresh" loading={retrying} onClick={onRetry}>
          Erneut versuchen
        </Button>
      )}
    </div>
  )
}

export default ErrorState
