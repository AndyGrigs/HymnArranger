/** Зберігає Blob як файл через тимчасове посилання. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  // Відкладаємо: у Safari миттєве revoke іноді скасовує завантаження.
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** "Гімн №12.mxl" → безпечне ім'я без службових символів. */
export function safeName(base: string, suffix: string, ext: string): string {
  const stem = base.replace(/\.(mxl|musicxml|xml)$/i, '').replace(/[\\/:*?"<>|]/g, '_')
  return `${stem}_${suffix}.${ext}`
}