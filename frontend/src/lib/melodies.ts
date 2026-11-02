/**
 * Каталог мелодій з гармонією для гостей — статичний JSON у /public/melodies,
 * як і приклади в lib/examples.ts: без бекенда й бази даних.
 */

import i18n from '../i18n'

export interface MelodyMeta {
  id: string
  title: string
  meter: string
  key: string
  description?: string
  /** Одноголосна мелодія в ABC з акордами ("C", "G7", …) над нотами. */
  abc: string
}

export async function fetchMelodies(): Promise<MelodyMeta[]> {
  const res = await fetch('/melodies/manifest.json')
  if (!res.ok) {
    throw new Error(i18n.t('editors.melodies.loadFailed', { status: res.status }))
  }
  return (await res.json()) as MelodyMeta[]
}
