// German display formats of the approved mockups: "29,99 €", "9,99 $",
// "24.10.2026, 14:02 Uhr", "Heute, 20:00 Uhr", "(in 6 Std.)", "(morgen)",
// "(in 9 Tagen)" (design/mockups/index.html:153, 161, 196, 228, 522).
// Dates are shown in the visitor's local time zone.

const LOCALE = 'de-DE'

/** "29,99 €" for (29.99, "EUR"); an unknown currency code is shown verbatim after the amount. */
export function formatPrice(amount: number, currency: string): string {
  const code = currency.trim().toUpperCase()
  try {
    return new Intl.NumberFormat(LOCALE, { style: 'currency', currency: code }).format(amount)
  } catch {
    const number = new Intl.NumberFormat(LOCALE, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount)
    return code ? `${number} ${code}` : number
  }
}

/** Parses an ISO 8601 string; null for a missing or unparsable value. */
export function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function startOfDay(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime()
}

/** Whole calendar days from `now` to `date` in local time (0 = same day, 1 = tomorrow). */
export function calendarDaysBetween(now: Date, date: Date): number {
  return Math.round((startOfDay(date) - startOfDay(now)) / 86_400_000)
}

const TIME = new Intl.DateTimeFormat(LOCALE, { hour: '2-digit', minute: '2-digit' })
const DATE_TIME = new Intl.DateTimeFormat(LOCALE, {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

/**
 * "24.10.2026, 14:02 Uhr"; with `now` given, a moment on the same day reads
 * "Heute, 14:02 Uhr". Null when the value is missing or unparsable.
 */
export function formatDateTime(value: string | null | undefined, now?: Date): string | null {
  const date = parseDate(value)
  if (!date) return null
  if (now && calendarDaysBetween(now, date) === 0) return `Heute, ${TIME.format(date)} Uhr`
  return `${DATE_TIME.format(date)} Uhr`
}

/**
 * Time left until a future moment: "in 6 Std." / "in 25 Min." on the same day,
 * "morgen", else "in 9 Tagen". Null when the moment is unknown or already past.
 */
export function formatTimeLeft(value: string | null | undefined, now: Date): string | null {
  const date = parseDate(value)
  if (!date) return null
  const ms = date.getTime() - now.getTime()
  if (ms <= 0) return null
  const days = calendarDaysBetween(now, date)
  if (days <= 0) {
    const hours = Math.floor(ms / 3_600_000)
    if (hours >= 1) return `in ${hours} Std.`
    return `in ${Math.max(1, Math.ceil(ms / 60_000))} Min.`
  }
  if (days === 1) return 'morgen'
  return `in ${days} Tagen`
}

/** Only http(s) URLs are ever put into an href (AC-15/AC-16 defence in depth). */
export function isSafeHttpUrl(value: string | null | undefined): value is string {
  if (!value) return false
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}
