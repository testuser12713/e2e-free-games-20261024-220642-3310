import type { ReactNode } from 'react'
import { Button } from './Button'
import { Icon } from './icons'
import './ui.css'

export type EmptyStateVariant = 'filtered' | 'no-data'

const COPY: Record<EmptyStateVariant, { title: string; text: string }> = {
  // design/mockups/deals-empty-filtered.html:149-150
  filtered: {
    title: 'Keine Treffer',
    text: 'Für die aktuelle Suche und Filter ist gerade kein Gratis-Spiel verfügbar. Ändern Sie die Eingaben oder zeigen Sie wieder alle Spiele an.',
  },
  // design/mockups/deals-empty-no-data.html:146-147
  'no-data': {
    title: 'Noch keine Daten vorhanden',
    text: 'Es wurde noch kein Aktualisierungslauf abgeschlossen. Über „Jetzt aktualisieren“ oben können Sie einen Lauf starten; die Liste füllt sich, sobald die ersten Quellen geantwortet haben.',
  },
}

export interface EmptyStateProps {
  /** "filtered": filters match nothing; "no-data": no run has finished yet. */
  variant: EmptyStateVariant
  /** Shows the "Filter zurücksetzen" button (filtered variant). */
  onReset?: () => void
  title?: string
  text?: ReactNode
}

/**
 * Empty list (design/mockups/deals-empty-filtered.html "empty-filtered",
 * deals-empty-no-data.html "empty-no-data"). The reset button only appears
 * when there is a handler for it, so it never silently does nothing (AC-12).
 */
export function EmptyState({ variant, onReset, title, text }: EmptyStateProps) {
  const copy = COPY[variant]
  return (
    <div className="state" data-testid={`empty-${variant}`}>
      <Icon name={variant === 'filtered' ? 'search' : 'clock'} className="state__icon" />
      <h2>{title ?? copy.title}</h2>
      <p className="state__text">{text ?? copy.text}</p>
      {onReset && (
        <Button variant="primary" onClick={onReset}>
          Filter zurücksetzen
        </Button>
      )}
    </div>
  )
}

export default EmptyState
