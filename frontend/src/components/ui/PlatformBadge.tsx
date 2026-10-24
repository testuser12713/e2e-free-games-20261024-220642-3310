import type { Platform } from '../../api/types'
import './ui.css'

const LABELS: Record<Platform, string> = { pc: 'PC', ps5: 'PS5' }

export interface PlatformBadgeProps {
  platform: Platform
  className?: string
}

/** "PC" (outlined) or "PS5" (filled) badge (design/mockups/index.html:146, 213). */
export function PlatformBadge({ platform, className }: PlatformBadgeProps) {
  return (
    <span className={['badge', `badge--${platform}`, className].filter(Boolean).join(' ')}>
      {LABELS[platform]}
    </span>
  )
}

/** The green "Gratis" badge next to the normal price (design/mockups/index.html:150). */
export function FreeBadge() {
  return <span className="badge badge--free">Gratis</span>
}

export default PlatformBadge
