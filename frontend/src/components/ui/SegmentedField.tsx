import './ui.css'

export interface SegmentedOption<T extends string> {
  value: T
  label: string
}

export interface SegmentedFieldProps<T extends string> {
  legend: string
  /** Radio group name; must be unique on the page. */
  name: string
  value: T
  options: SegmentedOption<T>[]
  onChange: (value: T) => void
  disabled?: boolean
  className?: string
}

/**
 * Segmented single choice built from native radios, e.g. the platform filter
 * "Alle / PC / PS5" (design/mockups/index.html:105-109).
 */
export function SegmentedField<T extends string>({
  legend,
  name,
  value,
  options,
  onChange,
  disabled = false,
  className,
}: SegmentedFieldProps<T>) {
  return (
    <fieldset className={['field', 'segmented', className].filter(Boolean).join(' ')}>
      <legend>{legend}</legend>
      <div className="segmented__options">
        {options.map((option) => (
          <label className="segmented__option" key={option.value}>
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={option.value === value}
              disabled={disabled}
              onChange={() => onChange(option.value)}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}

export default SegmentedField
