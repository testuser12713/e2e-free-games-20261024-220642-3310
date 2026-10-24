import { Link } from 'react-router-dom'

/** Site header (region site-header). Minimal landmark; the UI kit fills it. */
export default function Header() {
  return (
    <header className="header" data-testid="site-header">
      <div className="container header__inner">
        <Link className="brand" to="/">
          <span>Gratis-Spiele</span>
        </Link>
      </div>
    </header>
  )
}
