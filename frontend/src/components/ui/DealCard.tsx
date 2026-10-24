import { useState } from 'react'
import type { Deal } from '../../api/types'
import { Button, LinkButton } from './Button'
import { formatDateTime, formatPrice, formatTimeLeft, isSafeHttpUrl } from './format'
import { Icon } from './icons'
import { FreeBadge, PlatformBadge } from './PlatformBadge'
import './ui.css'

export interface DealCardProps {
  deal: Deal
  /** Reference time for "Heute" and the time left; defaults to the current time. */
  now?: Date
}

/**
 * One free deal (design/mockups/index.html:145-174): cover image when known,
 * platform badge, title, store, "Gratis" next to the struck-through normal
 * price, end of promotion and a "Zum Shop" link opening in a new tab.
 *
 * Everything the scrapers deliver is rendered as plain React text (AC-16); the
 * links only ever carry http(s) URLs and rel="noopener noreferrer".
 */
export function DealCard({ deal, now }: DealCardProps) {
  const [imageFailed, setImageFailed] = useState(false)
  const reference = now ?? new Date()
  const showImage = isSafeHttpUrl(deal.image_url) && !imageFailed
  const endsAt = formatDateTime(deal.ends_at, reference)
  const timeLeft = endsAt ? formatTimeLeft(deal.ends_at, reference) : null

  return (
    <article className="deal-card" data-testid="deal-card">
      <div className="deal-card__media">
        {showImage && (
          <img
            src={deal.image_url ?? undefined}
            width={460}
            height={215}
            loading="lazy"
            alt={`Titelbild von ${deal.title}`}
            referrerPolicy="no-referrer"
            onError={() => setImageFailed(true)}
          />
        )}
        <PlatformBadge platform={deal.platform} className="deal-card__platform" />
      </div>
      <div className="deal-card__body">
        <div className="deal-card__head">
          <h3 className="deal-card__title">{deal.title}</h3>
          <p className="deal-card__store">{deal.store}</p>
        </div>
        <div className="deal-card__price">
          <FreeBadge />
          <span className="deal-card__normal">
            <span className="deal-card__normal-label">Normalpreis</span>
            <del className="price">{formatPrice(deal.original_price, deal.currency)}</del>
          </span>
        </div>
        <p className="deal-card__end">
          <Icon name="clock" />
          {endsAt ? (
            <span>
              Aktion endet <time dateTime={deal.ends_at ?? undefined}>{endsAt}</time>
              {timeLeft && (
                <>
                  {' '}
                  <span className="muted">({timeLeft})</span>
                </>
              )}
            </span>
          ) : (
            <span>Aktionsende nicht bekannt</span>
          )}
        </p>
        <div className="deal-card__action">
          {isSafeHttpUrl(deal.url) ? (
            <LinkButton href={deal.url} external block iconAfter="external">
              Zum Shop
              <span className="visually-hidden"> ({deal.title}, öffnet in neuem Tab)</span>
            </LinkButton>
          ) : (
            // No usable shop link: visibly unavailable instead of a dead link (AC-12).
            <Button block disabled>
              Kein Shop-Link verfügbar
            </Button>
          )}
        </div>
      </div>
    </article>
  )
}

export default DealCard
