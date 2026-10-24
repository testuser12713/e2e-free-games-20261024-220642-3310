import './ui.css'

export interface ProgressProps {
  /** Accessible name of the bar. */
  label?: string
}

/**
 * Indeterminate progress bar shown while a refresh run is active
 * (design/mockups/deals-refreshing.html, "progress"). Render it only while
 * the work is running.
 */
export function Progress({ label = 'Aktualisierung läuft' }: ProgressProps) {
  return (
    <div className="progress" role="progressbar" aria-label={label}>
      <div className="progress__bar" />
    </div>
  )
}

export default Progress
