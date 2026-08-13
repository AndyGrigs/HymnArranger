/** Тривалість такту у чвертках: "3/4" → 3, "6/8" → 3, "4/4" → 4. */
export function barQuarterLength(meter: string): number {
  const [num, den] = meter.split('/').map(Number)
  if (!num || !den) return 4
  return (num * 4) / den
}

const NOTE_UA: Record<string, string> = {
  C: 'До', D: 'Ре', E: 'Мі', F: 'Фа', G: 'Соль', A: 'Ля', B: 'Сі',
}

/**
 * music21 віддає тональність як "D major" або "d minor" (мінор — з малої).
 * Перекладаємо у звичний для музиканта вигляд: "Ре мажор".
 */
export function formatKey(raw: string): string {
  const match = raw.trim().match(/^([A-Ga-g])([#\-b]*)\s*(major|minor)?$/)
  if (!match) return raw

  const [, letter, accidentals, mode] = match
  const base = NOTE_UA[letter.toUpperCase()] ?? letter

  const marks = accidentals
    .split('')
    .map((ch) => (ch === '#' ? '-дієз' : '-бемоль'))
    .join('')

  const modeUa = mode === 'minor' ? 'мінор' : mode === 'major' ? 'мажор' : ''
  return `${base}${marks}${modeUa ? ' ' + modeUa : ''}`
}

/**
 * Абсолютне зміщення у чвертках → номер такту і доля всередині нього.
 * Затакт вважається тактом 0 — так само нумерує MuseScore.
 */
export function offsetToPosition(
  offset: number,
  meter: string,
  pickupQl: number,
): { measure: number; beat: number } {
  const bar = barQuarterLength(meter)
  if (pickupQl > 0 && offset < pickupQl) {
    return { measure: 0, beat: offset + 1 }
  }
  const rel = offset - pickupQl
  const measure = Math.floor(rel / bar) + 1
  return { measure, beat: rel - (measure - 1) * bar + 1 }
}

/** Розмір файлу для показу користувачу. */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} КБ`
  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`
}