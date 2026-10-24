import type { ReactNode } from 'react'
import './ui.css'

export interface ProseProps {
  children: ReactNode
  'data-testid'?: string
}

/** Text column of the legal pages (design/mockups/impressum.html:35, styles.css:336-348). */
export function Prose({ children, ...rest }: ProseProps) {
  return (
    <div className="prose" {...rest}>
      {children}
    </div>
  )
}

export interface ProseSectionProps {
  /** Id of the heading; the section is labelled by it. */
  id: string
  title: string
  children: ReactNode
}

/** A titled section inside Prose (design/mockups/impressum.html:36). */
export function ProseSection({ id, title, children }: ProseSectionProps) {
  return (
    <section aria-labelledby={id}>
      <h2 id={id}>{title}</h2>
      {children}
    </section>
  )
}

export interface DataListItem {
  term: string
  value: ReactNode
}

/** Term/value cards, e.g. "Name", "Anschrift" (design/mockups/impressum.html:37-56). */
export function DataList({ items }: { items: DataListItem[] }) {
  return (
    <dl className="data-list">
      {items.map((item) => (
        <div key={item.term}>
          <dt>{item.term}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}

/** Marks a value the operator still has to fill in (design/mockups/impressum.html:42). */
export function TodoMark({ children }: { children: ReactNode }) {
  return <span className="todo-mark">{children}</span>
}

export interface TableProps {
  columns: string[]
  /** One array of cells per row, in column order. */
  rows: ReactNode[][]
  'data-testid'?: string
}

/**
 * Bordered table that stacks into labelled rows on small screens
 * (design/mockups/datenschutz.html:57-91, styles.css:321-333).
 */
export function Table({ columns, rows, ...rest }: TableProps) {
  return (
    <div className="table-wrap">
      <table className="table" {...rest}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th scope="col" key={column}>
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((cells, rowIndex) => (
            <tr key={rowIndex}>
              {cells.map((cell, cellIndex) => (
                <td key={columns[cellIndex] ?? cellIndex} data-label={columns[cellIndex]}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default Prose
