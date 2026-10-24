import { Outlet } from 'react-router-dom'
import Footer from './chrome/Footer'
import Header from './chrome/Header'

/**
 * The frame of every screen: site-header, main, site-footer
 * (design/mockups/index.html:12-25, 566-579). Pages bring their own heading.
 */
export default function Layout() {
  return (
    <>
      <Header />
      <main className="main container" data-testid="main">
        <Outlet />
      </main>
      <Footer />
    </>
  )
}
