import { Link } from 'react-router-dom'
import { DataList, InlineNotice, Prose, ProseSection, Table, TodoMark } from '../components/ui'

/** Note above the legal text (design/mockups/datenschutz.html:27-34). */
const OPERATOR_TODO_NOTICE =
  'Die markierten Angaben liefert die Produktspezifikation nicht. Der Betreiber muss sie vor der Veröffentlichung ergänzen.'

const PROCESSING_COLUMNS = ['Verarbeitung', 'Zweck', 'Rechtsgrundlage', 'Speicherdauer']

const PROCESSING_ROWS = [
  [
    'Hosting und Server-Logs',
    'Auslieferung der Seite, Betriebssicherheit',
    'Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse)',
    <TodoMark key="todo">Log-Aufbewahrung – vom Betreiber noch zu ergänzen</TodoMark>,
  ],
  [
    'Hoster',
    'Betrieb des Servers',
    'Art. 28 DSGVO (Auftragsverarbeitung)',
    <TodoMark key="todo">Hoster, Sitz, Drittlandtransfer – vom Betreiber noch zu ergänzen</TodoMark>,
  ],
  [
    'Scraper-Läufe und Quellenfehler',
    'Nachvollziehbarkeit der Aktualisierung',
    'Art. 6 Abs. 1 lit. f DSGVO; ohne Personenbezug',
    <TodoMark key="todo">
      Aufbewahrungsdauer der Betriebs-Logs – vom Betreiber noch zu ergänzen
    </TodoMark>,
  ],
]

const RIGHTS = [
  'Auskunft (Art. 15 DSGVO)',
  'Berichtigung (Art. 16 DSGVO)',
  'Löschung (Art. 17 DSGVO)',
  'Einschränkung der Verarbeitung (Art. 18 DSGVO)',
  'Datenübertragbarkeit (Art. 20 DSGVO)',
  'Widerspruch gegen Verarbeitungen auf Grundlage berechtigter Interessen (Art. 21 DSGVO)',
]

/**
 * Datenschutzerklärung at "/datenschutz" (design/mockups/datenschutz.html:26-112).
 * Operator-specific values are visibly marked placeholders, never invented.
 */
export default function DatenschutzPage() {
  return (
    <>
      <div className="page-head">
        <h1>Datenschutzerklärung</h1>
        <p className="page-head__lead">
          Welche Daten bei der Nutzung von Gratis-Spiele verarbeitet werden – und welche nicht.
        </p>
      </div>
      <InlineNotice tone="warning" icon="info">
        {OPERATOR_TODO_NOTICE}
      </InlineNotice>
      <Prose data-testid="datenschutz-page">
        <ProseSection id="h-verantwortlich" title="Verantwortlicher und Kontakt">
          <DataList
            items={[
              {
                term: 'Verantwortlicher',
                value: <TodoMark>Name des Betreibers – vom Betreiber noch zu ergänzen</TodoMark>,
              },
              {
                term: 'Anschrift',
                value: <TodoMark>Anschrift – vom Betreiber noch zu ergänzen</TodoMark>,
              },
              {
                term: 'Kontakt',
                value: <TodoMark>E-Mail-Adresse – vom Betreiber noch zu ergänzen</TodoMark>,
              },
            ]}
          />
          <p>
            Die Angaben entsprechen dem <Link to="/impressum">Impressum</Link>.
          </p>
        </ProseSection>
        <ProseSection id="h-ueberblick" title="Überblick">
          <p>
            Es gibt keine Benutzerkonten, keine Cookies zur Wiedererkennung und keine Analyse- oder
            Werbedienste. Schriften, Skripte und alle übrigen Dateien der Oberfläche werden
            ausschließlich von dieser Domain ausgeliefert. Die Anwendung selbst speichert weder
            IP-Adressen noch User-Agents der Besucher; protokolliert werden nur Scraper-Läufe und
            Fehler einzelner Quellen.
          </p>
        </ProseSection>
        <ProseSection id="h-hosting" title="Server-Logs und Hosting">
          <p>
            Beim Aufruf der Seite verarbeitet der Server technisch notwendig die Anfrage des
            Browsers. Ob und wie der Hoster dabei Zugriffsdaten protokolliert, hängt vom Hosting ab
            und ist vom Betreiber anzugeben.
          </p>
          <Table
            columns={PROCESSING_COLUMNS}
            rows={PROCESSING_ROWS}
            data-testid="processing-table"
          />
        </ProseSection>
        <ProseSection id="h-bilder" title="Nachladen von Titelbildern">
          <p>
            Die Titelbilder der Spiele lädt Ihr Browser direkt von den Servern der jeweiligen
            Shops. Dabei erhalten diese Server technisch bedingt Ihre IP-Adresse und
            Browserangaben. Auf diese Verarbeitung hat der Betreiber keinen Einfluss.
            Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO (Darstellung der Angebote); die
            Speicherdauer richtet sich nach den Shops.
          </p>
        </ProseSection>
        <ProseSection id="h-rechte" title="Ihre Rechte">
          <p>Soweit personenbezogene Daten verarbeitet werden, haben Sie folgende Rechte:</p>
          <ul>
            {RIGHTS.map((right) => (
              <li key={right}>{right}</li>
            ))}
          </ul>
        </ProseSection>
        <ProseSection id="h-beschwerde" title="Beschwerderecht">
          <p>
            Sie haben das Recht, sich bei einer Datenschutz-Aufsichtsbehörde zu beschweren (Art. 77
            DSGVO), insbesondere in dem Mitgliedstaat Ihres Aufenthaltsorts oder des Orts des
            mutmaßlichen Verstoßes.
          </p>
          <p>
            Zuständige Aufsichtsbehörde des Betreibers:{' '}
            <TodoMark>Aufsichtsbehörde – vom Betreiber noch zu ergänzen</TodoMark>
          </p>
        </ProseSection>
      </Prose>
    </>
  )
}
