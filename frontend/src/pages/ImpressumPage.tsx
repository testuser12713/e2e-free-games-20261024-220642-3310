import { DataList, InlineNotice, Prose, ProseSection, TodoMark } from '../components/ui'

/** Note above the legal text (design/mockups/impressum.html:27-34). */
const OPERATOR_TODO_NOTICE =
  'Die markierten Angaben liefert die Produktspezifikation nicht. Der Betreiber muss sie vor der Veröffentlichung ergänzen.'

/**
 * Impressum at "/impressum" (design/mockups/impressum.html:26-62).
 * The spec supplies no operator data, so every operator value is a visibly
 * marked placeholder — never an invented value.
 */
export default function ImpressumPage() {
  return (
    <>
      <div className="page-head">
        <h1>Impressum</h1>
        <p className="page-head__lead">Angaben zum Betreiber dieses Angebots.</p>
      </div>
      <InlineNotice tone="warning" icon="info">
        {OPERATOR_TODO_NOTICE}
      </InlineNotice>
      <Prose data-testid="impressum-page">
        <ProseSection id="h-anbieter" title="Angaben gemäß § 5 DDG">
          <DataList
            items={[
              {
                term: 'Name',
                value: <TodoMark>Name des Betreibers – vom Betreiber noch zu ergänzen</TodoMark>,
              },
              {
                term: 'Anschrift',
                value: (
                  <TodoMark>Straße, Hausnummer, PLZ, Ort – vom Betreiber noch zu ergänzen</TodoMark>
                ),
              },
              {
                term: 'E-Mail',
                value: <TodoMark>Kontakt-E-Mail-Adresse – vom Betreiber noch zu ergänzen</TodoMark>,
              },
            ]}
          />
        </ProseSection>
        <ProseSection id="h-inhalt" title="Hinweis zu den Inhalten">
          <p>
            Die Liste wird automatisiert aus öffentlich abrufbaren Angeboten von Spieleshops und
            einem Aggregator erzeugt. Titel, Preise, Titelbilder und Aktionszeiträume stammen von
            den jeweiligen Anbietern; für ihre Richtigkeit und Aktualität wird keine Gewähr
            übernommen.
          </p>
        </ProseSection>
        <ProseSection id="h-links" title="Haftung für Links">
          <p>
            Die Links zu den Angebotsseiten führen auf externe Seiten der Shops, auf deren Inhalte
            der Betreiber keinen Einfluss hat. Für diese fremden Inhalte ist stets der jeweilige
            Anbieter verantwortlich.
          </p>
        </ProseSection>
        <ProseSection id="h-marken" title="Marken">
          <p>
            Alle genannten Spiele- und Shop-Namen sind Eigentum ihrer jeweiligen Inhaber. Dieses
            Angebot steht in keiner Verbindung zu den genannten Unternehmen.
          </p>
        </ProseSection>
      </Prose>
    </>
  )
}
