import './ui.css'

export interface PriceRange {
  min: string
  max: string
}

export interface PriceRangeFieldProps {
  /** Both bounds as typed ("" = open). */
  value: PriceRange
  onChange: (next: PriceRange) => void
  legend?: string
  disabled?: boolean
  /** Marks the bounds as invalid (input--error, aria-invalid), e.g. min above max. */
  invalid?: boolean
  className?: string
}

/**
 * Min/max inputs for the normal price (design/mockups/index.html:122-129).
 * Values stay strings so a half-typed number is never rewritten under the user.
 */
export function PriceRangeField({
  value,
  onChange,
  legend = 'Normalpreis (Betrag)',
  disabled = false,
  invalid = false,
  className,
}: PriceRangeFieldProps) {
  const inputClass = invalid ? 'input input--error' : 'input'
  return (
    <fieldset className={['field', 'price-range', className].filter(Boolean).join(' ')}>
      <legend>{legend}</legend>
      <div className="price-range__inputs">
        <input
          className={inputClass}
          name="min"
          type="number"
          min={0}
          step="0.01"
          inputMode="decimal"
          placeholder="Min"
          aria-label="Normalpreis ab"
          aria-invalid={invalid || undefined}
          value={value.min}
          disabled={disabled}
          onChange={(event) => onChange({ ...value, min: event.target.value })}
        />
        <span className="price-range__sep" aria-hidden="true">
          –
        </span>
        <input
          className={inputClass}
          name="max"
          type="number"
          min={0}
          step="0.01"
          inputMode="decimal"
          placeholder="Max"
          aria-label="Normalpreis bis"
          aria-invalid={invalid || undefined}
          value={value.max}
          disabled={disabled}
          onChange={(event) => onChange({ ...value, max: event.target.value })}
        />
      </div>
    </fieldset>
  )
}

export default PriceRangeField
