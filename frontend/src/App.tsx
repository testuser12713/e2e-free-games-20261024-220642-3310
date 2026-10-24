import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import DatenschutzPage from './pages/DatenschutzPage'
import DealsPage from './pages/DealsPage'
import ImpressumPage from './pages/ImpressumPage'

/** Route table; the router itself is provided by main.tsx (or a test). */
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DealsPage />} />
        <Route path="impressum" element={<ImpressumPage />} />
        <Route path="datenschutz" element={<DatenschutzPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
