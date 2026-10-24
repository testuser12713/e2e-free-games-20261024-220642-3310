import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DEFAULT_FILTERS, type DealFilters } from '../api/types'
import FilterBar from '../components/FilterBar'

function setup(filters: DealFilters = DEFAULT_FILTERS) {
  const onChange = vi.fn()
  const onReset = vi.fn()
  render(
    <FilterBar filters={filters} stores={['GOG', 'Steam']} onChange={onChange} onReset={onReset} />,
  )
  return { onChange, onReset }
}

describe('FilterBar', () => {
  it('search emits q', () => {
    const { onChange } = setup()
    fireEvent.change(screen.getByLabelText('Titel suchen'), { target: { value: 'quest' } })
    expect(onChange).toHaveBeenCalledWith({ ...DEFAULT_FILTERS, q: 'quest' })
  })

  it('platform emits pc', () => {
    const { onChange } = setup()
    fireEvent.click(screen.getByLabelText('PC'))
    expect(onChange).toHaveBeenCalledWith({ ...DEFAULT_FILTERS, platform: 'pc' })
  })

  it('store lists all option plus stores and emits store', () => {
    const { onChange } = setup()
    const select = screen.getByLabelText('Shop') as HTMLSelectElement
    expect([...select.options].map((o) => o.textContent)).toEqual(['Alle Shops', 'GOG', 'Steam'])
    fireEvent.change(select, { target: { value: 'Steam' } })
    expect(onChange).toHaveBeenCalledWith({ ...DEFAULT_FILTERS, store: 'Steam' })
  })

  it('price emits numeric bounds and drops non-numeric input', () => {
    const { onChange } = setup()
    fireEvent.change(screen.getByLabelText('Normalpreis ab'), { target: { value: '5' } })
    expect(onChange).toHaveBeenCalledWith({ ...DEFAULT_FILTERS, minPrice: '5' })
    fireEvent.change(screen.getByLabelText('Normalpreis bis'), { target: { value: '20.5' } })
    expect(onChange).toHaveBeenLastCalledWith({ ...DEFAULT_FILTERS, maxPrice: '20.5' })
    onChange.mockClear()
    fireEvent.change(screen.getByLabelText('Normalpreis bis'), { target: { value: 'abc' } })
    for (const [arg] of onChange.mock.calls) expect(arg.maxPrice).not.toBe('abc')
  })

  it('sort covers all keys in both directions and emits sort + order', () => {
    const { onChange } = setup()
    const select = screen.getByLabelText('Sortierung') as HTMLSelectElement
    const values = [...select.options].map((o) => o.value)
    for (const key of ['title', 'original_price', 'ends_at', 'first_seen']) {
      expect(values).toContain(`${key}:asc`)
      expect(values).toContain(`${key}:desc`)
    }
    fireEvent.change(select, { target: { value: 'original_price:asc' } })
    expect(onChange).toHaveBeenCalledWith({
      ...DEFAULT_FILTERS,
      sort: 'original_price',
      order: 'asc',
    })
  })

  it('reset is disabled on defaults and calls onReset otherwise', () => {
    setup()
    expect(screen.getByRole('button', { name: 'Filter zurücksetzen' })).toBeDisabled()
  })

  it('reset calls onReset when filters differ', () => {
    const { onReset } = setup({ ...DEFAULT_FILTERS, q: 'x' })
    const button = screen.getByRole('button', { name: 'Filter zurücksetzen' })
    expect(button).toBeEnabled()
    fireEvent.click(button)
    expect(onReset).toHaveBeenCalledTimes(1)
  })
})
