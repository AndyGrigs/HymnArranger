import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Download, FileMusic } from 'lucide-react'
import { api, ApiError } from '../api'
import { saveBlob, safeName } from '../lib/download'
import { Spinner } from './ui/Spinner'
import type { Mode } from '../hooks/useArrangement'

interface Props {
  mode: Mode
  musicxml: string
  fileName: string
}

const SUFFIX_KEY: Record<Mode, string> = {
  suite: 'panels.download.suffixSuite',
  preset: 'panels.download.suffixPreset',
  merge: 'panels.download.suffixMerge',
  style: 'panels.download.suffixStyle',
}

export function DownloadBar({ mode, musicxml, fileName }: Props) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState<'mxl' | 'midi' | null>(null)
  const [error, setError] = useState<string | null>(null)

  // MusicXML уже є в пам'яті — зберігаємо напряму, без зайвого запиту.
  function saveMusicXml() {
    const blob = new Blob([musicxml], { type: 'application/vnd.recordare.musicxml+xml' })
    saveBlob(blob, safeName(fileName, t(SUFFIX_KEY[mode]), 'musicxml'))
  }

  // Стиснений .mxl: передаємо вже готовий musicxml на бекенд лише для zip-упаковки.
  // Раніше тут іде перегенерація з оригінальної мелодії — ручні правки губилися.
  async function saveMxl() {
    setBusy('mxl')
    setError(null)
    try {
      const blob = await api.compress({ musicxml })
      saveBlob(blob, safeName(fileName, t(SUFFIX_KEY[mode]), 'mxl'))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('panels.download.failed'))
    } finally {
      setBusy(null)
    }
  }

  async function saveMidi() {
    setBusy('midi')
    setError(null)
    try {
      const blob = await api.midi({ musicxml: musicxml })
      saveBlob(blob, safeName(fileName, t(SUFFIX_KEY[mode]), 'mid'))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('panels.download.failed'))
    } finally {
      setBusy(null)
    }
  }

  const buttonClass =
    'flex items-center gap-2 rounded border border-ink/15 px-3 py-2 text-sm transition hover:border-accent/40 disabled:opacity-50'

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={saveMusicXml} className={buttonClass}>
          <FileMusic className="h-4 w-4 text-accent" />
          MusicXML
        </button>

        <button type="button" onClick={saveMxl} disabled={busy !== null} className={buttonClass}>
          {busy === 'mxl' ? <Spinner /> : <Download className="h-4 w-4 text-accent" />}
          {t('panels.download.mxl')}
        </button>

        <button type="button" onClick={saveMidi} disabled={busy !== null} className={buttonClass}>
          {busy === 'midi' ? <Spinner /> : <Download className="h-4 w-4 text-accent" />}
          MIDI
        </button>
      </div>

      {error && <p className="mt-2 text-sm text-accent">{error}</p>}
    </div>
  )
}