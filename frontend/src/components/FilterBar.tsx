import type { FormEvent } from 'react'
import { DEFAULT_FILTERS, type DealFilters, type SortKey } from '../api/types'
import { Button, PriceRangeField, SearchField, SegmentedField, SelectField } from './ui'
import type { PriceRange, SegmentedOption, SelectOption } from './ui'

export interface FilterBarProps {
  filters: DealFilters
  stores: string[]
  onChange: (next: DealFilters) => void
  onReset: () => void
}

const PLATFORM_OPTIONS: SegmentedOption<DealFilters['platform']>[] = [
  { value: 'all', label: 'Alle' },
  { value: 'pc', label: 'PC' },
  { value: 'ps5', label: 'PS5' },
]

/** Sort choices of design/mockups/index.html:130-139, value = "<sort>:<order>". */
export const SORT_OPTIONS: SelectOption[] = [
  { value: 'first_seen:desc', label: 'Neueste zuerst' },
  { value: 'first_seen:asc', label: 'Älteste zuerst' },
  { value: 'title:asc', label: 'Titel A–Z' },
  { value: 'title:desc', label: 'Titel Z–A' },
  { value: 'original_price:desc', label: 'Normalpreis absteigend' },
  { value: 'original_price:asc', label: 'Normalpreis aufsteigend' },
  { value: 'ends_at:asc', label: 'Aktionsende: bald zuerst' },
  { value: 'ends_at:desc', label: 'Aktionsende: spät zuerst' },
]

const SORT_KEYS: SortKey[] = ['title', 'original_price', 'ends_at', 'first_seen']

/** "" (open bound) or a non-negative decimal number, possibly half-typed ("12."). */
const PRICE_PATTERN = /^\d+([.,]\d*)?$/

export function isAcceptablePrice(value: string): boolean {
  return value === '' || PRICE_PATTERN.test(value.trim())
}

export function filtersEqual(a: DealFilters, b: DealFilters): boolean {
  return (Object.keys(DEFAULT_FILTERS) as (keyof DealFilters)[]).every((key) => a[key] === b[key])
}

/** Search, platform, store, price and sort controls (design/mockups/index.html:94-141). */
export default function FilterBar({ filters, stores, onChange, onReset }: FilterBarProps) {
  const update = (patch: Partial<DealFilters>) => onChange({ ...filters, ...patch })

  const storeOptions: SelectOption[] = [{ value: '', label: 'Alle Shops' }]
  const storeNames = [...stores]
  if (filters.store && !storeNames.includes(filters.store)) storeNames.push(filters.store)
  for (const name of storeNames) storeOptions.push({ value: name, label: name })

  const handlePrice = (next: PriceRange) => {
    const min = next.min.trim()
    const max = next.max.trim()
    if (!isAcceptablePrice(min) || !isAcceptablePrice(max)) return
    update({ minPrice: min.replace(',', '.'), maxPrice: max.replace(',', '.') })
  }

  const handleSort = (value: string) => {
    const [sort, order] = value.split(':')
    if (!SORT_KEYS.includes(sort as SortKey) || (order !== 'asc' && order !== 'desc')) return
    update({ sort: sort as SortKey, order })
  }

  const minNum = Number(filters.minPrice)
  const maxNum = Number(filters.maxPrice)
  const invalidRange =
    filters.minPrice !== '' && filters.maxPrice !== '' && minNum > maxNum

  const isDefault = filtersEqual(filters, DEFAULT_FILTERS)

  return (
    <form
      className="filter-bar"
      role="search"
      aria-label="Spiele suchen und filtern"
      onSubmit={(event: FormEvent) => event.preventDefault()}
    >
      <SearchField
        id="f-q"
        name="q"
        label="Titel suchen"
        placeholder="z. B. Tropico"
        className="filter-bar__search"
        value={filters.q}
        onChange={(q) => update({ q })}
      />
      <SegmentedField
        legend="Plattform"
        name="platform"
        value={filters.platform}
        options={PLATFORM_OPTIONS}
        onChange={(platform) => update({ platform })}
      />
      <SelectField
        id="f-store"
        name="store"
        label="Shop"
        value={filters.store}
        options={storeOptions}
        onChange={(store) => update({ store })}
      />
      <PriceRangeField
        value={{ min: filters.minPrice, max: filters.maxPrice }}
        invalid={invalidRange}
        onChange={handlePrice}
      />
      <SelectField
        id="f-sort"
        name="sort"
        label="Sortierung"
        value={`${filters.sort}:${filters.order}`}
        options={SORT_OPTIONS}
        onChange={handleSort}
      />
      <div className="filter-bar__actions">
        <Button variant="ghost" disabled={isDefault} onClick={onReset}>
          Filter zurücksetzen
        </Button>
      </div>
    </form>
  )
}

export { FilterBar }
