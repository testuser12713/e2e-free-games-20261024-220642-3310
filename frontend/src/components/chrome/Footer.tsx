import { Link } from 'react-router-dom'

/**
 * Site footer (region site-footer, design/mockups/index.html:567-579): the
 * disclaimer and the links to Impressum and Datenschutzerklärung.
 */
export default function Footer() {
  return (
    <footer className="footer" data-testid="site-footer">
      <div className="container footer__inner">
        <p className="footer__note">
          Gratis-Spiele sammelt zeitlich begrenzte 100-%-Aktionen für PC und PS5. Preise und
          Aktionszeiträume ohne Gewähr; maßgeblich ist die Angebotsseite des Shops.
        </p>
        <ul className="footer__links">
          <li>
            <Link to="/impressum" data-testid="footer-impressum">
              Impressum
            </Link>
          </li>
          <li>
            <Link to="/datenschutz" data-testid="footer-datenschutz">
              Datenschutzerklärung
            </Link>
          </li>
        </ul>
      </div>
    </footer>
  )
}

export { Footer }
