import { useRef, useState } from 'react'
import { Music, Upload, X } from 'lucide-react'
import { Spinner } from './ui/Spinner'
import { formatBytes } from '../lib/music'

const ACCEPTED = ['.mxl', '.musicxml', '.xml']
const MAX_BYTES = 5 * 1024 * 1024 // збігається з MAX_BYTES у api.py

interface Props {
  onFile: (file: File) => void
  onClear: () => void
  fileName: string | null
  fileSize?: number
  loading: boolean
}

export function FileDropzone({ onFile, onClear, fileName, fileSize, loading }: Props) {
  const [dragging, setDragging] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Валідуємо на клієнті, щоб не ганяти завідомо непридатний файл
  // через мережу — бекенд перевіряє те саме ще раз.
  function accept(file: File) {
    const dot = file.name.lastIndexOf('.')
    const ext = dot >= 0 ? file.name.slice(dot).toLowerCase() : ''

    if (!ACCEPTED.includes(ext)) {
      setLocalError(`Потрібен файл ${ACCEPTED.join(', ')} — отримано «${ext || 'без розширення'}».`)
      return
    }
    if (file.size > MAX_BYTES) {
      setLocalError(`Файл завеликий: ${formatBytes(file.size)}, ліміт 5 МБ.`)
      return
    }
    setLocalError(null)
    onFile(file)
  }

  if (fileName) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-ink/10 bg-white px-5 py-4">
        <Music className="h-5 w-5 shrink-0 text-accent" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{fileName}</p>
          {fileSize !== undefined && (
            <p className="text-xs text-muted">{formatBytes(fileSize)}</p>
          )}
        </div>
        {loading && <Spinner className="text-accent" />}
        <button
          type="button"
          onClick={() => {
            setLocalError(null)
            onClear()
          }}
          className="rounded p-1 text-muted transition hover:bg-ink/5 hover:text-ink"
          aria-label="Прибрати файл"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    )
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          const file = e.dataTransfer.files?.[0]
          if (file) accept(file)
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            inputRef.current?.click()
          }
        }}
        className={`flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed px-6 py-12 text-center transition ${
          dragging
            ? 'border-accent bg-accent/5'
            : 'border-ink/15 bg-white hover:border-accent/50'
        }`}
      >
        <Upload className="h-8 w-8 text-accent" />
        <div>
          <p className="font-medium">Перетягни сюди ноти мелодії</p>
          <p className="mt-1 text-sm text-muted">
            або натисни, щоб обрати · {ACCEPTED.join(' · ')} · до 5 МБ
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(',')}
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) accept(file)
            e.target.value = '' // дозволяє обрати той самий файл повторно
          }}
        />
      </div>

      {localError && (
        <p className="mt-2 text-sm text-accent">{localError}</p>
      )}
    </div>
  )
}