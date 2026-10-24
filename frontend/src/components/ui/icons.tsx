import type { ReactNode } from 'react'

/**
 * The line icons of the approved mockups (20x20, stroke 2, round caps), taken
 * path for path from design/mockups/*.html. Always decorative: the text next to
 * an icon carries the meaning, so every icon is aria-hidden.
 */
export type IconName =
  | 'refresh'
  | 'search'
  | 'clock'
  | 'external'
  | 'check-circle'
  | 'idle-circle'
  | 'warning'
  | 'info'
  | 'plug'

const PATHS: Record<IconName, ReactNode> = {
  // design/mockups/index.html:34-37
  refresh: (
    <>
      <path d="M16.5 10a6.5 6.5 0 1 1-2-4.7" />
      <path d="M16.5 3v3.5H13" />
    </>
  ),
  // design/mockups/index.html:98-101
  search: (
    <>
      <circle cx="9" cy="9" r="6" />
      <path d="m14 14 3.5 3.5" />
    </>
  ),
  // design/mockups/index.html:157-160
  clock: (
    <>
      <circle cx="10" cy="10" r="7.5" />
      <path d="M10 5.5V10l3 2" />
    </>
  ),
  // design/mockups/index.html:165-169
  external: (
    <>
      <path d="M8 4H5a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 5 16h9a1.5 1.5 0 0 0 1.5-1.5V12" />
      <path d="M11 3.5h5.5V9" />
      <path d="M16.5 3.5 9 11" />
    </>
  ),
  // design/mockups/index.html:46-49
  'check-circle': (
    <>
      <circle cx="10" cy="10" r="8" />
      <path d="m6.5 10.5 2.5 2.5 4.5-5" />
    </>
  ),
  // design/mockups/deals-empty-no-data.html:47-50
  'idle-circle': (
    <>
      <circle cx="10" cy="10" r="8" />
      <path d="M6.5 10h7" />
    </>
  ),
  // design/mockups/deals-source-error.html (pill--error, notice--error)
  warning: (
    <>
      <path d="M10 2.5 18 16.5H2z" />
      <path d="M10 8v4" />
      <path d="M10 14.2v.1" />
    </>
  ),
  // design/mockups/impressum.html:28-32
  info: (
    <>
      <circle cx="10" cy="10" r="8" />
      <path d="M10 9v5" />
      <path d="M10 6.2v.1" />
    </>
  ),
  // design/mockups/deals-error.html:32-35
  plug: (
    <>
      <path d="M7 3v4M13 3v4" />
      <path d="M5 7h10v3a5 5 0 0 1-10 0z" />
      <path d="M10 15v2.5" />
    </>
  ),
}

export interface IconProps {
  name: IconName
  className?: string
}

export function Icon({ name, className }: IconProps) {
  return (
    <svg
      className={className ? `icon ${className}` : 'icon'}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      data-icon={name}
    >
      {PATHS[name]}
    </svg>
  )
}

export default Icon
