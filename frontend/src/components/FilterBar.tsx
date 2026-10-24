import type { DealFilters } from '../api/types'

export interface FilterBarProps {
  filters: DealFilters
  stores: string[]
  onChange: (next: DealFilters) => void
  onReset: () => void
}

/** Search, platform, store, price and sort controls. Built by the filter-bar ticket. */
export default function FilterBar(_props: FilterBarProps) {
  return null
}

export { FilterBar }
