import { useState, type ReactNode } from 'react'
import type { Deal } from '../../api/types'
import { Button, LinkButton } from './Button'
import { DealCard } from './DealCard'
import { DealCardSkeleton, Skeleton } from './DealCardSkeleton'
import { EmptyState } from './EmptyState'
import { ErrorState } from './ErrorState'
import { InlineNotice } from './InlineNotice'
import { PlatformBadge } from './PlatformBadge'
import { PriceRangeField, type PriceRange } from './PriceRangeField'
import { Progress } from './Progress'
import { DataList, Prose, ProseSection, Table, TodoMark } from './Prose'
import { SearchField } from './SearchField'
import { SegmentedField } from './SegmentedField'
import { SelectField } from './SelectField'
import { PillList, StatusPill } from './StatusPill'
import './ui.css'

/** Fixed reference time of the gallery, the mockups' "now". */
export const GALLERY_NOW = new Date('2026-10-24T14:02:00Z')

const BASE_DEAL: Deal = {
  id: 1,
  title: 'Lantern Valley',
  store: 'Steam',
  platform: 'pc',
  original_price: 29.99,
  currency: 'EUR',
  url: 'https://store.steampowered.com/app/1',
  image_url: 'https://images.example.org/cover-1.jpg',
  starts_at: '2026-10-24T08:00:00Z',
  ends_at: '2026-10-29T17:00:00Z',
  first_seen_at: '2026-10-24T08:02:00Z',
  last_seen_at: '2026-10-24T14:02:00Z',
}

/** One deal per DealCard state the screens show. */
export const GALLERY_DEALS: Record<string, Deal> = {
  pc: BASE_DEAL,
  ps5: {
    ...BASE_DEAL,
    id: 2,
    title: 'Harbor Lights',
    store: 'PlayStation Store',
    platform: 'ps5',
    url: 'https://store.playstation.com/product/2',
    ends_at: '2026-11-02T01:59:00Z',
  },
  noImage: { ...BASE_DEAL, id: 3, title: 'Paper Garden', image_url: null },
  noEnd: {
    ...BASE_DEAL,
    id: 4,
    title: 'Cloud Orchard',
    store: 'itch.io',
    currency: 'USD',
    original_price: 9.99,
    ends_at: null,
  },
  unsafeUrl: { ...BASE_DEAL, id: 5, title: 'Quiet Signal', url: 'javascript:alert(1)' },
  markup: {
    ...BASE_DEAL,
    id: 6,
    title: '<img src=x onerror="alert(1)"> Night Shift',
    store: '<b>Shop</b>',
  },
}

const STORE_OPTIONS = [
  { value: '', label: 'Alle Shops' },
  { value: 'Epic Games Store', label: 'Epic Games Store' },
  { value: 'GOG', label: 'GOG' },
  { value: 'PlayStation Store', label: 'PlayStation Store' },
  { value: 'Steam', label: 'Steam' },
]

const PLATFORM_OPTIONS = [
  { value: 'all', label: 'Alle' },
  { value: 'pc', label: 'PC' },
  { value: 'ps5', label: 'PS5' },
] as const

type PlatformChoice = (typeof PLATFORM_OPTIONS)[number]['value']

function Specimen({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section className="stack" data-testid={`gallery-${id}`} aria-labelledby={`gallery-h-${id}`}>
      <h2 id={`gallery-h-${id}`}>{title}</h2>
      {children}
    </section>
  )
}

function Row({ children }: { children: ReactNode }) {
  return <div className="result-meta">{children}</div>
}

/**
 * Every kit component in every state the approved screens show. It is a
 * living reference rendered by the kit test; it is not routed in the product.
 */
export function Gallery() {
  const [clicks, setClicks] = useState(0)
  const [query, setQuery] = useState('')
  const [store, setStore] = useState('')
  const [platform, setPlatform] = useState<PlatformChoice>('all')
  const [price, setPrice] = useState<PriceRange>({ min: '', max: '' })
  const [resets, setResets] = useState(0)

  return (
    <div className="stack" data-testid="ui-gallery">
      <Specimen id="button" title="Button">
        <Row>
          <Button onClick={() => setClicks((n) => n + 1)}>Primär ({clicks})</Button>
          <Button variant="secondary" icon="refresh" onClick={() => setClicks((n) => n + 1)}>
            Jetzt aktualisieren
          </Button>
          <Button variant="ghost" onClick={() => setClicks((n) => n + 1)}>
            Filter zurücksetzen
          </Button>
          <Button variant="secondary" disabled>
            Deaktiviert
          </Button>
          <Button variant="secondary" icon="refresh" loading>
            Aktualisiere …
          </Button>
          <LinkButton href="https://store.epicgames.com/" external iconAfter="external">
            Zum Shop
          </LinkButton>
        </Row>
      </Specimen>

      <Specimen id="badge" title="PlatformBadge">
        <Row>
          <PlatformBadge platform="pc" />
          <PlatformBadge platform="ps5" />
        </Row>
      </Specimen>

      <Specimen id="deal-card" title="DealCard">
        <ul className="deal-grid">
          {Object.entries(GALLERY_DEALS).map(([key, deal]) => (
            <li key={key} data-testid={`gallery-deal-${key}`}>
              <DealCard deal={deal} now={GALLERY_NOW} />
            </li>
          ))}
        </ul>
      </Specimen>

      <Specimen id="skeleton" title="DealCardSkeleton">
        <ul className="deal-grid" aria-busy="true">
          <li aria-hidden="true">
            <DealCardSkeleton />
          </li>
        </ul>
        <Skeleton variant="line-lg" width="11rem" />
        <PillList>
          <Skeleton variant="pill" as="li" />
          <Skeleton variant="pill" as="li" />
        </PillList>
      </Specimen>

      <Specimen id="fields" title="SearchField, SelectField, SegmentedField, PriceRangeField">
        <div className="filter-bar">
          <SearchField
            id="gallery-q"
            label="Titel suchen"
            placeholder="z. B. Tropico"
            value={query}
            onChange={setQuery}
            className="filter-bar__search"
          />
          <SegmentedField
            legend="Plattform"
            name="gallery-platform"
            value={platform}
            options={[...PLATFORM_OPTIONS]}
            onChange={setPlatform}
          />
          <SelectField
            id="gallery-store"
            label="Shop"
            value={store}
            options={STORE_OPTIONS}
            onChange={setStore}
          />
          <PriceRangeField value={price} onChange={setPrice} />
        </div>
        <div className="filter-bar" data-testid="gallery-fields-disabled">
          <SearchField
            id="gallery-q-disabled"
            label="Titel suchen (deaktiviert)"
            value=""
            onChange={() => undefined}
            disabled
          />
          <SegmentedField
            legend="Plattform (deaktiviert)"
            name="gallery-platform-disabled"
            value="all"
            options={[...PLATFORM_OPTIONS]}
            onChange={() => undefined}
            disabled
          />
          <SelectField
            id="gallery-store-disabled"
            label="Shop (deaktiviert)"
            value=""
            options={STORE_OPTIONS}
            onChange={() => undefined}
            disabled
          />
          <PriceRangeField
            legend="Normalpreis (deaktiviert)"
            value={{ min: '', max: '' }}
            onChange={() => undefined}
            disabled
          />
        </div>
        <div data-testid="gallery-price-invalid">
          <PriceRangeField
            legend="Normalpreis (ungültig)"
            value={{ min: '50', max: '10' }}
            onChange={() => undefined}
            invalid
          />
        </div>
      </Specimen>

      <Specimen id="pill" title="StatusPill">
        <PillList aria-label="Quellen">
          <StatusPill name="Steam" status="ok" count={3} />
          <StatusPill
            name="PlayStation Store"
            status="error"
            title="Zeitüberschreitung beim Abruf"
          />
          <StatusPill name="GamerPower" status="idle" />
        </PillList>
      </Specimen>

      <Specimen id="progress" title="Progress">
        <Progress />
      </Specimen>

      <Specimen id="notice" title="InlineNotice">
        <InlineNotice title="Aktualisierung läuft.">
          Die Quellen werden abgefragt, die Liste bleibt bis zum Abschluss unverändert.
        </InlineNotice>
        <InlineNotice tone="success" title="Aktualisierung abgeschlossen.">
          Alle 5 Quellen wurden abgefragt, die Liste ist auf dem neuesten Stand.
        </InlineNotice>
        <InlineNotice tone="warning" role="alert" title="Aktualisierung gerade nicht möglich.">
          Es läuft bereits ein Lauf oder es wurden zu viele Anfragen gestellt. Bitte versuchen
          Sie es in einer Minute erneut.
        </InlineNotice>
        <InlineNotice tone="error" title="PlayStation Store: Zeitüberschreitung beim Abruf">
          Die Angebote dieser Quelle stammen vom letzten erfolgreichen Lauf und bleiben erhalten.
        </InlineNotice>
        <InlineNotice tone="warning" icon="info">
          Die markierten Angaben liefert die Produktspezifikation nicht. Der Betreiber muss sie
          vor der Veröffentlichung ergänzen.
        </InlineNotice>
      </Specimen>

      <Specimen id="empty" title="EmptyState">
        <EmptyState variant="filtered" onReset={() => setResets((n) => n + 1)} />
        <p className="muted" data-testid="gallery-resets">
          Zurückgesetzt: {resets}
        </p>
        <EmptyState variant="no-data" />
      </Specimen>

      <Specimen id="error" title="ErrorState">
        <ErrorState detail="GET /api/deals – keine Antwort" onRetry={() => setClicks((n) => n + 1)} />
      </Specimen>

      <Specimen id="prose" title="Prose">
        <Prose>
          <ProseSection id="gallery-h-anbieter" title="Angaben gemäß § 5 DDG">
            <DataList
              items={[
                {
                  term: 'Name',
                  value: <TodoMark>Name des Betreibers – vom Betreiber noch zu ergänzen</TodoMark>,
                },
                { term: 'E-Mail', value: 'kontakt@example.org' },
              ]}
            />
          </ProseSection>
          <ProseSection id="gallery-h-rechte" title="Ihre Rechte">
            <ul>
              <li>Auskunft (Art. 15 DSGVO)</li>
              <li>Berichtigung (Art. 16 DSGVO)</li>
            </ul>
            <Table
              columns={['Verarbeitung', 'Zweck', 'Rechtsgrundlage', 'Speicherdauer']}
              rows={[
                [
                  'Hosting und Server-Logs',
                  'Auslieferung der Seite, Betriebssicherheit',
                  'Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse)',
                  <TodoMark key="todo">Log-Aufbewahrung – vom Betreiber noch zu ergänzen</TodoMark>,
                ],
              ]}
            />
          </ProseSection>
        </Prose>
      </Specimen>
    </div>
  )
}

export default Gallery
