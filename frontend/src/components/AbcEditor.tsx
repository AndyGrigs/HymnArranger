import { useEffect, useId, useRef, useState } from 'react'
import abcjs from 'abcjs'

const DEFAULT_TUNE = `X:1
T:Нова мелодія
M:4/4
L:1/8
K:C
CDEF GABc |]`

type Duration = 'whole' | 'half' | 'quarter' | 'eighth' | 'sixteenth'
type Accidental = '' | '^' | '_' | '='

const DURATION_SUFFIX: Record<Duration, string> = {
  whole: '8', half: '4', quarter: '2', eighth: '', sixteenth: '/2',
}
const DURATION_LABEL: Record<Duration, string> = {
  whole: '𝅝', half: '𝅗𝅥', quarter: '♩', eighth: '♪', sixteenth: '𝅘𝅥𝅯',
}
const DURATIONS: Duration[] = ['whole', 'half', 'quarter', 'eighth', 'sixteenth']
const PITCHES = ['C', 'D', 'E', 'F', 'G', 'A', 'B']

const CHORD_ROOTS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
const CHORD_QUALITIES = [
  { label: 'maj', suffix: '' },
  { label: 'm', suffix: 'm' },
  { label: '7', suffix: '7' },
  { label: 'maj7', suffix: 'maj7' },
  { label: 'm7', suffix: 'm7' },
  { label: 'dim', suffix: 'dim' },
  { label: 'aug', suffix: 'aug' },
  { label: 'sus4', suffix: 'sus4' },
]

interface Props {
  initialAbc?: string
  onReady?: (getAbc: () => string) => void
}

export function AbcEditor({ initialAbc = DEFAULT_TUNE, onReady }: Props) {
  const uid = useId().replace(/:/g, '')
  const paperId = `abc-paper-${uid}`
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const [duration, setDuration] = useState<Duration>('eighth')
  const [octave, setOctave] = useState(0)
  const [accidental, setAccidental] = useState<Accidental>('')
  const [chordRoot, setChordRoot] = useState('C')
  const [chordQuality, setChordQuality] = useState('')
  const [armedChord, setArmedChord] = useState<string | null>(null)
  const [abcWarnings, setAbcWarnings] = useState<string[]>([])
  const [renderTick, setRenderTick] = useState(0)

  const composedChord = chordRoot + chordQuality

  useEffect(() => {
    onReady?.(() => textareaRef.current?.value ?? '')
  }, [onReady])

  useEffect(() => {
    const val = textareaRef.current?.value ?? ''
    const result = abcjs.renderAbc(paperId, val, { responsive: 'resize' })
    // abcjs warnings contain HTML markup for position highlighting — strip tags for safe display
    const raw = result?.[0]?.warnings ?? []
    setAbcWarnings(raw.map((w) => w.replace(/<[^>]+>/g, '')))
  }, [renderTick, paperId])

  function triggerRender() {
    setRenderTick((t) => t + 1)
  }

  function insertAtCursor(text: string) {
    const ta = textareaRef.current
    if (!ta) return
    // When textarea has no focus (user clicked a toolbar button without first clicking
    // inside the text area), selectionStart defaults to 0 — which is inside the ABC
    // header (X:1…K:C). Inserting there corrupts the header structure.
    // Instead, fall back to just before the final barline |] or to the very end.
    const focused = document.activeElement === ta
    let start: number, end: number
    if (focused) {
      start = ta.selectionStart ?? ta.value.length
      end = ta.selectionEnd ?? ta.value.length
    } else {
      const finalBar = ta.value.lastIndexOf('|]')
      start = end = finalBar >= 0 ? finalBar : ta.value.length
    }
    ta.value = ta.value.slice(0, start) + text + ta.value.slice(end)
    ta.selectionStart = ta.selectionEnd = start + text.length
    ta.focus()
    triggerRender()
  }

  function insertNote(pitch: string) {
    let p = pitch
    if (octave === -1) p += ','
    if (octave === 1) p = p.toLowerCase()
    if (octave === 2) p = p.toLowerCase() + "'"
    const prefix = armedChord ? `"${armedChord}"` : ''
    insertAtCursor(prefix + accidental + p + DURATION_SUFFIX[duration])
    setAccidental('')
    if (armedChord) setArmedChord(null)
  }

  const btn = (active: boolean) =>
    `rounded border px-2 py-1 text-sm transition ${
      active
        ? 'border-accent/40 bg-accent/10 font-medium text-accent'
        : 'border-ink/15 bg-white text-ink/70 hover:bg-ink/5 hover:text-ink'
    }`

  const octaveLabel = ['-1', '0', '+1', '+2'][octave + 1]

  return (
    <div className="space-y-2">
      {/* Тривалість + акциденції + октава */}
      <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-ink/10 bg-ink/2 px-3 py-2">
        <span className="w-20 shrink-0 text-xs text-muted">Тривалість</span>
        {DURATIONS.map((d) => (
          <button key={d} type="button" onClick={() => setDuration(d)} className={btn(duration === d)}>
            {DURATION_LABEL[d]}
          </button>
        ))}
        <span className="mx-1 select-none text-ink/20">|</span>
        <button type="button" onClick={() => setAccidental('^')} className={btn(accidental === '^')}>♯</button>
        <button type="button" onClick={() => setAccidental('_')} className={btn(accidental === '_')}>♭</button>
        <button type="button" onClick={() => setAccidental('=')} className={btn(accidental === '=')}>♮</button>
        <span className="mx-1 select-none text-ink/20">|</span>
        <button type="button" onClick={() => setOctave((o) => Math.max(o - 1, -1))} className={btn(false)}>Oct ↓</button>
        <span className="w-5 text-center text-xs font-mono text-muted">{octaveLabel}</span>
        <button type="button" onClick={() => setOctave((o) => Math.min(o + 1, 2))} className={btn(false)}>Oct ↑</button>
        <span className="mx-1 select-none text-ink/20">|</span>
        <button type="button" onClick={() => insertAtCursor('z' + DURATION_SUFFIX[duration])} className={btn(false)}>Пауза</button>
        <button type="button" onClick={() => insertAtCursor(' | ')} className={btn(false) + ' font-mono font-bold'}>|</button>
      </div>

      {/* Ноти */}
      <div className="flex items-center gap-1.5 rounded-lg border border-ink/10 bg-ink/2 px-3 py-2">
        <span className="w-20 shrink-0 text-xs text-muted">Нота</span>
        {PITCHES.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => insertNote(p)}
            className="h-9 w-9 rounded border border-ink/15 bg-white text-sm font-semibold text-ink/80 transition hover:border-accent/40 hover:bg-accent/5 hover:text-accent"
          >
            {p}
          </button>
        ))}
        {accidental && (
          <span className="ml-1 text-xs text-accent">
            → наступна нота: {accidental === '^' ? '♯' : accidental === '_' ? '♭' : '♮'}
          </span>
        )}
      </div>

      {/* Акорди */}
      <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-ink/10 bg-ink/2 px-3 py-2">
        <span className="w-20 shrink-0 text-xs text-muted">Акорд</span>
        <select
          value={chordRoot}
          onChange={(e) => setChordRoot(e.target.value)}
          className="rounded border border-ink/15 bg-white px-2 py-1 text-sm text-ink/80"
        >
          {CHORD_ROOTS.map((r) => <option key={r}>{r}</option>)}
        </select>
        <select
          value={chordQuality}
          onChange={(e) => setChordQuality(e.target.value)}
          className="rounded border border-ink/15 bg-white px-2 py-1 text-sm text-ink/80"
        >
          {CHORD_QUALITIES.map((q) => (
            <option key={q.label} value={q.suffix}>{q.label}</option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => setArmedChord(composedChord)}
          className={btn(armedChord !== null)}
        >
          {armedChord ? `✓ "${armedChord}" → наступна нота` : `"${composedChord}" до наступної ноти`}
        </button>
        {armedChord && (
          <button type="button" onClick={() => setArmedChord(null)} className={btn(false)}>✕</button>
        )}
        <button
          type="button"
          onClick={() => insertAtCursor(`"${composedChord}"`)}
          className={btn(false)}
        >
          Вставити тут
        </button>
      </div>

      {/* Попередження */}
      {abcWarnings.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-700">
          {abcWarnings.join(' · ')}
        </div>
      )}

      {/* Редактор + прев'ю */}
      <div className="grid grid-cols-[35%_1fr] gap-3">
        <textarea
          ref={textareaRef}
          defaultValue={initialAbc}
          spellCheck={false}
          onChange={triggerRender}
          className="h-64 resize-none rounded-lg border border-ink/15 bg-white p-2.5 font-mono text-xs leading-relaxed text-ink/80 focus:border-accent/40 focus:outline-none"
        />
        <div className="overflow-auto rounded-lg border border-ink/10 bg-white p-2">
          <div id={paperId} />
        </div>
      </div>
    </div>
  )
}
