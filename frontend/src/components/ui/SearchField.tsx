import { Icon } from './icons'
import './ui.css'

export interface SearchFieldProps {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  name?: string
  placeholder?: string
  disabled?: boolean
  className?: string
}

/** Labelled search input with the magnifier icon (design/mockups/index.html:95-104). */
export function SearchField({
  id,
  label,
  value,
  onChange,
  name,
  placeholder,
  disabled = false,
  className,
}: SearchFieldProps) {
  return (
    <div className={className ? `field ${className}` : 'field'}>
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      <div className="input-wrap">
        <Icon name="search" />
        <input
          className="input"
          id={id}
          name={name}
          type="search"
          placeholder={placeholder}
          autoComplete="off"
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
        />
      </div>
    </div>
  )
}

export default SearchField
