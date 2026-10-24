import type { ComponentPropsWithoutRef, ReactNode } from 'react'
import { Icon, type IconName } from './icons'
import './ui.css'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost'

interface ButtonLook {
  /** btn--primary (default), btn--secondary or btn--ghost (design/mockups/styles.css:147-154). */
  variant?: ButtonVariant
  /** Full width (btn--block). */
  block?: boolean
  /** Icon in front of the label. */
  icon?: IconName
  /** Icon after the label (the "Zum Shop" external-link icon). */
  iconAfter?: IconName
}

export function buttonClassName({
  variant = 'primary',
  block = false,
  loading = false,
  className,
}: {
  variant?: ButtonVariant
  block?: boolean
  loading?: boolean
  className?: string
}): string {
  return ['btn', `btn--${variant}`, block && 'btn--block', loading && 'is-loading', className]
    .filter(Boolean)
    .join(' ')
}

export interface ButtonProps extends ButtonLook, ComponentPropsWithoutRef<'button'> {
  /**
   * Busy state (design/mockups/deals-refreshing.html: "is-loading", disabled,
   * aria-busy, spinning icon). A loading button is always disabled.
   */
  loading?: boolean
  children: ReactNode
}

/**
 * The kit's button. Disabled and loading buttons are visibly unavailable
 * (AC-12): `disabled` greys them out and sets the native disabled state.
 */
export function Button({
  variant = 'primary',
  block = false,
  loading = false,
  icon,
  iconAfter,
  className,
  type = 'button',
  disabled,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      type={type}
      className={buttonClassName({ variant, block, loading, className })}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
    >
      {icon && <Icon name={icon} />}
      {children}
      {iconAfter && <Icon name={iconAfter} />}
    </button>
  )
}

export interface LinkButtonProps
  extends ButtonLook,
    Omit<ComponentPropsWithoutRef<'a'>, 'target' | 'rel'> {
  href: string
  /** Opens in a new tab with rel="noopener noreferrer" (AC-11, AC-16). */
  external?: boolean
  children: ReactNode
}

/** A link styled as a button, e.g. "Zum Shop" (design/mockups/index.html:165). */
export function LinkButton({
  variant = 'primary',
  block = false,
  icon,
  iconAfter,
  external = false,
  className,
  children,
  ...rest
}: LinkButtonProps) {
  return (
    <a
      {...rest}
      className={buttonClassName({ variant, block, className })}
      target={external ? '_blank' : undefined}
      rel={external ? 'noopener noreferrer' : undefined}
    >
      {icon && <Icon name={icon} />}
      {children}
      {iconAfter && <Icon name={iconAfter} />}
    </a>
  )
}

export default Button
