import i18n from '../i18n'

/** Тривалість такту у чвертках: "3/4" → 3, "6/8" → 3, "4/4" → 4. */
export function barQuarterLength(meter: string): number {
  const [num, den] = meter.split('/').map(Number)
  if (!num || !den) return 4
  return (num * 4) / den
}

/**
 * music21 віддає тональність як "D major" або "d minor" (мінор — з малої).
 * Українською: "Ре мажор", "Ре-дієз мінор"; німецькою: "D-Dur", "cis-Moll".
 */
export function formatKey(raw: string): string {
  const match = raw.trim().match(/^([A-Ga-g])([#\-b]*)\s*(major|minor)?$/)
  if (!match) return raw

  const [, letter, accidentals, mode] = match
  const base = letter.toUpperCase()
  const sharps = (accidentals.match(/#/g) ?? []).length
  const flats = (accidentals.match(/[-b]/g) ?? []).length
  const modeName = mode ? i18n.t(`panels.music.${mode}`) : ''

  if (i18n.language === 'de') {
    // У німецькій B — це сі-бемоль, а сі-бекар — H; бемолі: Es, As, решта + "es".
    let name = i18n.t(`panels.music.notes.${base}`)
    if (flats > 0 && base === 'B') name = 'B' + 'es'.repeat(flats - 1)
    else if (flats > 0) name += (base === 'E' || base === 'A' ? 's' : 'es') + 'es'.repeat(flats - 1)
    name += i18n.t('panels.music.sharp').repeat(sharps)
    if (mode === 'minor') name = name.charAt(0).toLowerCase() + name.slice(1)
    return modeName ? `${name}-${modeName}` : name
  }

  const marks = i18n.t('panels.music.sharp').repeat(sharps) + i18n.t('panels.music.flat').repeat(flats)
  return `${i18n.t(`panels.music.notes.${base}`)}${marks}${modeName ? ' ' + modeName : ''}`
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
  if (bytes < 1024) return `${bytes} ${i18n.t('panels.music.bytes')}`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} ${i18n.t('panels.music.kb')}`
  return `${(bytes / 1024 / 1024).toFixed(1)} ${i18n.t('panels.music.mb')}`
}