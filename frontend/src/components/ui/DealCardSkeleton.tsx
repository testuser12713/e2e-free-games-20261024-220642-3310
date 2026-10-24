import type { CSSProperties } from 'react'
import './ui.css'

export type SkeletonVariant = 'line' | 'line-lg' | 'media' | 'btn' | 'pill'

export interface SkeletonProps {
  variant?: SkeletonVariant
  /** CSS width, e.g. "70%" or "11rem". */
  width?: string
  /** Element to render; "li" for a placeholder inside a list such as the pill-list. */
  as?: 'div' | 'li'
  style?: CSSProperties
}

// The pill placeholder of design/mockups/deals-loading.html:49 (inline there too).
const PILL_STYLE: CSSProperties = { width: '9rem', height: '2rem', borderRadius: 'var(--r-pill)' }

/** A shimmering placeholder block (design/mockups/styles.css:284-294). Decorative only. */
export function Skeleton({ variant = 'line', width, as = 'div', style }: SkeletonProps) {
  const Tag = as
  const className = variant === 'pill' ? 'skeleton' : `skeleton skeleton--${variant}`
  const merged: CSSProperties = {
    ...(variant === 'pill' ? PILL_STYLE : null),
    ...(width ? { width } : null),
    ...style,
  }
  return <Tag className={className} style={merged} aria-hidden="true" data-testid="skeleton" />
}

/**
 * Loading placeholder with the shape of a DealCard
 * (design/mockups/deals-loading.html:113-128). Put it into the deal grid's
 * <li> while the list loads; the busy state is announced by the list itself.
 */
export function DealCardSkeleton() {
  return (
    <div className="deal-card" aria-hidden="true" data-testid="deal-card-skeleton">
      <Skeleton variant="media" />
      <div className="deal-card__body">
        <Skeleton variant="line-lg" width="70%" />
        <Skeleton variant="line" width="40%" />
        <Skeleton variant="line-lg" width="55%" />
        <Skeleton variant="line" width="65%" />
        <Skeleton variant="btn" />
      </div>
    </div>
  )
}

export default DealCardSkeleton
