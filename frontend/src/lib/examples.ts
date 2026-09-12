/**
 * Каталог готових прикладів — простий JSON поруч зі статичними файлами,
 * без бекенда й бази даних. Vite віддає /public як є, тож fetch('/scores/…')
 * працює однаково і в розробці, і після збірки.
 */

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
    throw new Error(`Не вдалося завантажити список прикладів (${res.status})`)
  }
  return (await res.json()) as ExampleMeta[]
}

export async function fetchExampleXml(file: string): Promise<string> {
  const res = await fetch(`${SCORES_BASE}/${file}`)
  if (!res.ok) {
    throw new Error(`Файл «${file}» не знайдено в public/scores`)
  }
  return await res.text()
}
