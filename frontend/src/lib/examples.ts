/**
 * Каталог готових прикладів — простий JSON поруч зі статичними файлами,
 * без бекенда й бази даних. Vite віддає /public як є, тож fetch('/scores/…')
 * працює однаково і в розробці, і після збірки.
 */

import i18n from '../i18n'

export interface ExampleMeta {
  id: string
  title: string
  /** Ім'я файлу в /public/scores — саме нестиснений .musicxml. */
  file: string
  meter: string
  key: string
  description?: string
}

const SCORES_BASE = '/scores'

export async function fetchExamples(): Promise<ExampleMeta[]> {
  const res = await fetch(`${SCORES_BASE}/manifest.json`)
  if (!res.ok) {
    throw new Error(i18n.t('editors.examples.loadFailed', { status: res.status }))
  }
  return (await res.json()) as ExampleMeta[]
}

export async function fetchExampleXml(file: string): Promise<string> {
  // .mxl — стиснений ZIP, OSMD сам завантажить і розпакує за URL
  if (file.endsWith('.mxl')) {
    const url = `${SCORES_BASE}/${encodeURIComponent(file)}`
    const res = await fetch(url, { method: 'HEAD' })
    if (!res.ok) throw new Error(i18n.t('editors.examples.fileNotFound', { file }))
    return url
  }
  const res = await fetch(`${SCORES_BASE}/${file}`)
  if (!res.ok) {
    throw new Error(i18n.t('editors.examples.fileNotFound', { file }))
  }
  return await res.text()
}
