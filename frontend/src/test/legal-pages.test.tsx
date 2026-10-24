import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import App from '../App'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

function todoMarks(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll('.todo-mark')).map((el) => el.textContent ?? '')
}

describe('Impressum page', () => {
  it('renders the required headings', () => {
    renderAt('/impressum')
    expect(screen.getByRole('heading', { level: 1, name: 'Impressum' })).toBeInTheDocument()
    for (const name of [
      'Angaben gemäß § 5 DDG',
      'Hinweis zu den Inhalten',
      'Haftung für Links',
      'Marken',
    ]) {
      expect(screen.getByRole('heading', { level: 2, name })).toBeInTheDocument()
    }
  })

  it('marks name, address and e-mail as operator placeholders', () => {
    renderAt('/impressum')
    const page = screen.getByTestId('impressum-page')
    const section = within(page).getByRole('region', { name: 'Angaben gemäß § 5 DDG' })
    for (const term of ['Name', 'Anschrift', 'E-Mail']) {
      expect(within(section).getByText(term, { selector: 'dt' })).toBeInTheDocument()
    }
    const marks = todoMarks(section)
    expect(marks).toHaveLength(3)
    for (const mark of marks) expect(mark).toContain('vom Betreiber noch zu ergänzen')
    expect(screen.getByText(/Der Betreiber muss sie vor der Veröffentlichung/)).toBeInTheDocument()
  })
})

describe('Datenschutz page', () => {
  it('renders the required headings', () => {
    renderAt('/datenschutz')
    expect(
      screen.getByRole('heading', { level: 1, name: 'Datenschutzerklärung' }),
    ).toBeInTheDocument()
    for (const name of [
      'Verantwortlicher und Kontakt',
      'Überblick',
      'Server-Logs und Hosting',
      'Nachladen von Titelbildern',
      'Ihre Rechte',
      'Beschwerderecht',
    ]) {
      expect(screen.getByRole('heading', { level: 2, name })).toBeInTheDocument()
    }
  })

  it('marks controller, hoster, third-country transfer and log retention as placeholders', () => {
    renderAt('/datenschutz')
    const marks = todoMarks(screen.getByTestId('datenschutz-page')).join('\n')
    for (const needle of [
      'Name des Betreibers',
      'Anschrift',
      'E-Mail-Adresse',
      'Log-Aufbewahrung',
      'Hoster',
      'Drittlandtransfer',
      'Aufsichtsbehörde',
    ]) {
      expect(marks).toContain(needle)
    }
  })

  it('lists purpose, legal basis and storage period for hosting and logs', () => {
    renderAt('/datenschutz')
    const table = screen.getByTestId('processing-table')
    for (const col of ['Verarbeitung', 'Zweck', 'Rechtsgrundlage', 'Speicherdauer']) {
      expect(within(table).getByRole('columnheader', { name: col })).toBeInTheDocument()
    }
    expect(within(table).getByText('Hosting und Server-Logs')).toBeInTheDocument()
  })

  it('states what the application does not store and names rights and complaint', () => {
    renderAt('/datenschutz')
    expect(screen.getByText(/weder\s+IP-Adressen noch User-Agents/)).toBeInTheDocument()
    expect(screen.getByText(/keine Cookies/)).toBeInTheDocument()
    expect(screen.getByText('Auskunft (Art. 15 DSGVO)')).toBeInTheDocument()
    expect(screen.getByText(/Art\. 77\s+DSGVO/)).toBeInTheDocument()
    const page = screen.getByTestId('datenschutz-page')
    expect(within(page).getByRole('link', { name: 'Impressum' })).toHaveAttribute(
      'href',
      '/impressum',
    )
  })
})
