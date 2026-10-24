import { Link } from 'react-router-dom'

/**
 * Site header (region site-header, design/mockups/index.html:12-24): the brand
 * link back to the deals list. The mark's colours are the mockup's own.
 */
export default function Header() {
  return (
    <header className="header" data-testid="site-header">
      <div className="container header__inner">
        <Link className="brand" to="/" data-testid="brand-link">
          <svg className="brand__mark" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
            <rect width="32" height="32" rx="8" fill="oklch(62% 0.17 152)" />
            <path
              d="M8 9.5h9.6a2 2 0 0 1 1.4.6l5.4 5.4a2 2 0 0 1 0 2.8l-4.3 4.3a2 2 0 0 1-2.8 0L7.9 17.2A2 2 0 0 1 7.3 15.8V10.2A.7.7 0 0 1 8 9.5z"
              fill="oklch(20% 0.05 265)"
            />
            <circle cx="12" cy="14" r="1.8" fill="oklch(62% 0.17 152)" />
          </svg>
          <span>Gratis-Spiele</span>
          <span className="brand__sub">PC · PS5</span>
        </Link>
      </div>
    </header>
  )
}

export { Header }
