import { Link } from 'react-router-dom'

/** Site footer (region site-footer). Minimal landmark; the UI kit fills it. */
export default function Footer() {
  return (
    <footer className="footer" data-testid="site-footer">
      <div className="container footer__inner">
        <ul className="footer__links">
          <li>
            <Link to="/impressum">Impressum</Link>
          </li>
          <li>
            <Link to="/datenschutz">Datenschutzerklärung</Link>
          </li>
        </ul>
      </div>
    </footer>
  )
}
