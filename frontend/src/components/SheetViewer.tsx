import { useEffect, useRef, useState } from 'react'
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay'
import { FileText, Minus, Plus, ScrollText } from 'lucide-react'
import { Spinner } from './ui/Spinner'

interface Props {
  musicxml: string
}

const ZOOM_MIN = 0.4
const ZOOM_MAX = 1.6
const ZOOM_STEP = 0.1

type Layout = 'a4' | 'endless'

export function SheetViewer({ musicxml }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const osmdRef = useRef<OpenSheetMusicDisplay | null>(null)
  const [zoom, setZoom] = useState(0.7)
  const [layout, setLayout] = useState<Layout>('a4')
  const [rendering, setRendering] = useState(true)
  const [failed, setFailed] = useState<string | null>(null)

  const zoomRef = useRef(zoom)
  zoomRef.current = zoom

  // Формат сторінки задається при створенні екземпляра: змінити його
  // на льоту можна, але OSMD усе одно перебудовує графіку повністю,
  // тож простіше створити наново — тому layout у залежностях.
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let cancelled = false
    container.innerHTML = ''
    setRendering(true)
    setFailed(null)

    const osmd = new OpenSheetMusicDisplay(container, {
      autoResize: false,
      backend: 'svg',
      // "A4_P" — портретний A4; "Endless" — суцільна стрічка без розривів.
      pageFormat: layout === 'a4' ? 'A4_P' : 'Endless',
      // Без явного тла аркуші прозорі й зливаються між собою.
      pageBackgroundColor: layout === 'a4' ? '#FFFFFF' : undefined,
      drawTitle: true,
      drawSubtitle: false,
      drawPartNames: false,
      drawMeasureNumbers: true,
      measureNumberInterval: 4,
    })
    osmdRef.current = osmd

    osmd
      .load(musicxml)
      .then(() => {
        if (cancelled) return
        osmd.zoom = zoomRef.current
        osmd.render()
        setRendering(false)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setFailed(err instanceof Error ? err.message : 'Не вдалося намалювати ноти')
        setRendering(false)
      })

    return () => {
      cancelled = true
      osmdRef.current = null
      container.innerHTML = ''
    }
  }, [musicxml, layout])

  useEffect(() => {
    const osmd = osmdRef.current
    if (!osmd || rendering) return
    osmd.zoom = zoom
    osmd.render()
  }, [zoom, rendering])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let timer: number | undefined
    const observer = new ResizeObserver(() => {
      window.clearTimeout(timer)
      timer = window.setTimeout(() => {
        const osmd = osmdRef.current
        if (osmd?.GraphicSheet) osmd.render()
      }, 250)
    })

    observer.observe(container)
    return () => {
      window.clearTimeout(timer)
      observer.disconnect()
    }
  }, [])

  const iconButton =
    'rounded p-1.5 text-muted transition hover:bg-ink/5 hover:text-ink disabled:opacity-30'

  return (
    <div className="rounded-lg border border-ink/10 bg-paper">
      <div className="flex items-center justify-between border-b border-ink/10 bg-white px-4 py-2">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setLayout('a4')}
            className={`flex items-center gap-1.5 rounded px-2 py-1.5 text-xs transition ${
              layout === 'a4' ? 'bg-accent/10 text-accent' : 'text-muted hover:text-ink'
            }`}
          >
            <FileText className="h-4 w-4" />
            Аркуші A4
          </button>
          <button
            type="button"
            onClick={() => setLayout('endless')}
            className={`flex items-center gap-1.5 rounded px-2 py-1.5 text-xs transition ${
              layout === 'endless' ? 'bg-accent/10 text-accent' : 'text-muted hover:text-ink'
            }`}
          >
            <ScrollText className="h-4 w-4" />
            Стрічка
          </button>
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(ZOOM_MIN, +(z - ZOOM_STEP).toFixed(2)))}
            disabled={zoom <= ZOOM_MIN}
            className={iconButton}
            aria-label="Зменшити"
          >
            <Minus className="h-4 w-4" />
          </button>
          <span className="w-12 text-center font-mono text-xs text-muted">
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(ZOOM_MAX, +(z + ZOOM_STEP).toFixed(2)))}
            disabled={zoom >= ZOOM_MAX}
            className={iconButton}
            aria-label="Збільшити"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
      </div>

      {rendering && (
        <div className="flex items-center justify-center gap-2 py-16 text-muted">
          <Spinner />
          <span className="text-sm">Малюю ноти…</span>
        </div>
      )}

      {failed && <p className="px-4 py-8 text-sm text-accent">Ноти не відобразились: {failed}</p>}

      <div
        ref={containerRef}
        className="osmd-container overflow-x-auto p-4"
        style={{ display: rendering || failed ? 'none' : 'block' }}
      />
    </div>
  )
}
