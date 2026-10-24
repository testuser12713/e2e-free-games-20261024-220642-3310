import './ui.css'

export interface SelectOption {
  value: string
  label: string
}

export interface SelectFieldProps {
  id: string
  label: string
  value: string
  options: SelectOption[]
  onChange: (value: string) => void
  name?: string
  disabled?: boolean
  className?: string
}

/** Labelled native select with the chevron (design/mockups/index.html:110-121). */
export function SelectField({
  id,
  label,
  value,
  options,
  onChange,
  name,
  disabled = false,
  className,
}: SelectFieldProps) {
  return (
    <div className={className ? `field ${className}` : 'field'}>
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      <select
        className="select"
        id={id}
        name={name}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}

export default SelectField
