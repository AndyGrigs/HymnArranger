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
// Dotted = 3/2 of base: whole→12, half→6, quarter→3, eighth→3/2, sixteenth→3/4
const DURATION_SUFFIX_DOTTED: Record<Duration, string> = {
  whole: '12', half: '6', quarter: '3', eighth: '3/2', sixteenth: '3/4',
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

const KEY_PRESETS = [
  'C', 'G', 'D', 'A', 'E', 'B', 'F#',
  'F', 'Bb', 'Eb', 'Ab', 'Db',
  'Am', 'Em', 'Bm', 'Dm', 'Gm', 'Cm',
]
const METER_PRESETS = ['4/4', '3/4', '6/8', '2/4', '3/8', '12/8']

// Diatonic pitch names in order
const DIATONIC = ['C', 'D', 'E', 'F', 'G', 'A', 'B']

/**
 * Transpose one ABC note (at a known char range) by `step` diatonic steps.
 * Preserves accidentals and duration suffix. Returns unchanged text if the
 * range doesn't match a note pattern.
 */
function transposeNoteAt(
  abcText: string,
  startChar: number,
  endChar: number,
  step: number,
): string {
  const fragment = abcText.slice(startChar, endChar)
  // accidentals? + pitch letter + octave modifiers + duration
  const m = fragment.match(/^([\^_=]*)([ A-Ga-g])([',]*)([\d/]*)$/)
  if (!m || m[2].trim() === '') return abcText

  const acc = m[1]
  const letter = m[2].trim()
  const mods = m[3]
  const dur = m[4]

  const isLower = letter === letter.toLowerCase()
  let octave = isLower ? 1 : 0
  for (const c of mods) {
    if (c === "'") octave++
    else if (c === ',') octave--
  }

  const idx = DIATONIC.indexOf(letter.toUpperCase())
  if (idx < 0) return abcText

  const rawPos = octave * 7 + idx + step
  const newOctave = Math.floor(rawPos / 7)
  const newIdx = ((rawPos % 7) + 7) % 7
  const newLetter = DIATONIC[newIdx]

  let newNote = acc
  if (newOctave <= 0) {
    newNote += newLetter
    for (let i = newOctave; i < 0; i++) newNote += ','
  } else if (newOctave === 1) {
    newNote += newLetter.toLowerCase()
  } else {
    newNote += newLetter.toLowerCase()
    for (let i = 1; i < newOctave; i++) newNote += "'"
  }
  newNote += dur

  return abcText.slice(0, startChar) + newNote + abcText.slice(endChar)
}

/** Count barlines in the ABC body (after the K: header line). */
function countBars(abcText: string): number {
  const kMatch = abcText.match(/^K:.*$/m)
  if (!kMatch) return 0
  const body = abcText.slice(abcText.indexOf(kMatch[0]) + kMatch[0].length)
  return (body.match(/\|/g) ?? []).length
}

interface Props {
  initialAbc?: string
  onReady?: (getAbc: () => string) => void
}

export function AbcEditor({ initialAbc = DEFAULT_TUNE, onReady }: Props) {
  const uid = useId().replace(/:/g, '')
  const paperId = `abc-paper-${uid}`
  const textareaId = `abc-ta-${uid}`

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const editorRef = useRef<abcjs.Editor | null>(null)
  const synthRef = useRef<abcjs.MidiBuffer | null>(null)
  // Stable wrapper so abcjs.Editor's cached params always call the latest handler
  const dragHandlerRef = useRef<abcjs.ClickListener>(() => {})

  const [duration, setDuration] = useState<Duration>('eighth')
  const [octave, setOctave] = useState(0)
  const [accidental, setAccidental] = useState<Accidental>('')
  const [dot, setDot] = useState(false)
  const [chordRoot, setChordRoot] = useState('C')
  const [chordQuality, setChordQuality] = useState('')
  const [armedChord, setArmedChord] = useState<string | null>(null)
  const [abcWarnings, setAbcWarnings] = useState<string[]>([])
  const [barCount, setBarCount] = useState(() => countBars(initialAbc))
  const [isPlaying, setIsPlaying] = useState(false)

  const composedChord = chordRoot + chordQuality
  const octaveLabel = ['-1', '0', '+1', '+2'][octave + 1]
  const activeSuffix = dot ? DURATION_SUFFIX_DOTTED[duration] : DURATION_SUFFIX[duration]

  // Keep current drag handler in ref to avoid stale closures passed to abcjs
  dragHandlerRef.current = (
    abcElem: abcjs.AbcElem,
    _tune: number,
    _classes: string,
    _analysis: abcjs.ClickListenerAnalysis,
    drag: abcjs.ClickListenerDrag,
  ) => {
    if (!drag?.step) return
    const ta = textareaRef.current
    if (!ta || abcElem.startChar == null || abcElem.endChar == null) return
    const newText = transposeNoteAt(ta.value, abcElem.startChar, abcElem.endChar, drag.step)
    if (newText === ta.value) return
    // Replace entire text via execCommand so the undo stack is preserved
    ta.focus()
    ta.setSelectionRange(0, ta.value.length)
    document.execCommand('insertText', false, newText)
  }

  // abcjs.Editor handles textarea↔paper sync, cursor highlighting and auto-render.
  // dragging:true lets users drag notes up/down to change pitch; clickListener
  // receives startChar/endChar so we can rewrite just that note in the ABC text.
  useEffect(() => {
    const editor = new abcjs.Editor(textareaId, {
      paper_id: paperId,
      generate_warnings: true,
      abcjsParams: {
        responsive: 'resize',
        dragging: true,
        clickListener: (abcElem, tuneNumber, classes, analysis, drag) =>
          dragHandlerRef.current(abcElem, tuneNumber, classes, analysis, drag),
      },
      onchange: (ed: abcjs.Editor) => {
        setAbcWarnings((ed.getTunes()?.[0]?.warnings ?? []).map((w: string) => w.replace(/<[^>]+>/g, '')))
        setBarCount(countBars(textareaRef.current?.value ?? ''))
      },
    })
    editorRef.current = editor
    return () => { editorRef.current = null }
  }, [textareaId, paperId])

  useEffect(() => {
    onReady?.(() => textareaRef.current?.value ?? '')
  }, [onReady])

  // When the textarea isn't focused, snap cursor to just before the final |]
  // so toolbar insertions land in the body, not inside the ABC header.
  function ensureFocus() {
    const ta = textareaRef.current
    if (!ta) return
    if (document.activeElement === ta) return
    const finalBar = ta.value.lastIndexOf('|]')
    const pos = finalBar >= 0 ? finalBar : ta.value.length
    ta.focus()
    ta.setSelectionRange(pos, pos)
  }

  // Use execCommand('insertText') so every toolbar insertion is a single
  // undoable action in the browser's native undo stack.
  function insertAtCursor(text: string) {
    ensureFocus()
    document.execCommand('insertText', false, text)
  }

  // Replace an ABC header field (K: or M:) using execCommand to preserve undo.
  function setHeaderField(field: string, value: string) {
    const ta = textareaRef.current
    if (!ta) return
    const newText = ta.value.replace(new RegExp(`^${field}:.*$`, 'm'), `${field}:${value}`)
    ta.focus()
    ta.setSelectionRange(0, ta.value.length)
    document.execCommand('insertText', false, newText)
  }

  // Wrap current selection in a slur/ligature; if nothing selected, insert ()
  // and park cursor between the parens.
  function wrapInSlur() {
    const ta = textareaRef.current
    if (!ta) return
    const { selectionStart: s, selectionEnd: e } = ta
    ta.focus()
    if (s !== e) {
      const sel = ta.value.slice(s, e)
      ta.setSelectionRange(s, e)
      document.execCommand('insertText', false, `(${sel})`)
    } else {
      ensureFocus()
      document.execCommand('insertText', false, '()')
      ta.setSelectionRange(ta.selectionStart - 1, ta.selectionStart - 1)
    }
  }

  async function togglePlay() {
    const ta = textareaRef.current
    if (!ta) return

    if (isPlaying) {
      synthRef.current?.stop?.()
      setIsPlaying(false)
      return
    }

    if (!abcjs.synth.supportsAudio()) {
      alert('Ваш браузер не підтримує Web Audio API')
      return
    }

    try {
      // '*' = parse-only, no DOM rendering
      const visualObj = abcjs.renderAbc('*', ta.value)
      if (!visualObj?.[0]) return
      if (!synthRef.current) {
        synthRef.current = new abcjs.synth.CreateSynth()
      }
      const synth = synthRef.current
      await synth.init({ visualObj: visualObj[0] })
      const { duration } = await synth.prime()
      synth.start()
      setIsPlaying(true)
      setTimeout(() => setIsPlaying(false), duration * 1000 + 300)
    } catch {
      setIsPlaying(false)
    }
  }

  function insertNote(pitch: string) {
    let p = pitch
    if (octave === -1) p += ','
    if (octave === 1) p = p.toLowerCase()
    if (octave === 2) p = p.toLowerCase() + "'"
    const prefix = armedChord ? `"${armedChord}"` : ''
    insertAtCursor(prefix + accidental + p + activeSuffix)
    setAccidental('')
    if (armedChord) setArmedChord(null)
  }

  const btn = (active: boolean) =>
    `rounded border px-2 py-1 text-sm transition ${
      active
        ? 'border-accent/40 bg-accent/10 font-medium text-accent'
        : 'border-ink/15 bg-white text-ink/70 hover:bg-ink/5 hover:text-ink'
    }`

  return (
    <div className="space-y-2">
      {/* Рядок 0: тональність + розмір + лічильник тактів + відтворення */}
      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-ink/10 bg-ink/2 px-3 py-2">
        <span className="text-xs text-muted">Тон</span>
        <select
          defaultValue="C"
          onChange={(e) => setHeaderField('K', e.target.value)}
          className="rounded border border-ink/15 bg-white px-2 py-1 text-sm text-ink/80"
        >
          {KEY_PRESETS.map((k) => <option key={k} value={k}>{k}</option>)}
        </select>
        <span className="text-xs text-muted">Розмір</span>
        <select
          defaultValue="4/4"
          onChange={(e) => setHeaderField('M', e.target.value)}
          className="rounded border border-ink/15 bg-white px-2 py-1 text-sm text-ink/80"
        >
          {METER_PRESETS.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <div className="ml-auto flex items-center gap-2">
          {barCount > 0 && (
            <span className="text-xs text-muted">{barCount} тактів</span>
          )}
          <button
            type="button"
            onClick={togglePlay}
            className={`rounded border px-3 py-1 text-sm font-medium transition ${
              isPlaying
                ? 'border-red-300 bg-red-50 text-red-600 hover:bg-red-100'
                : 'border-green-300 bg-green-50 text-green-700 hover:bg-green-100'
            }`}
          >
            {isPlaying ? '■ Стоп' : '▶ Прослухати'}
          </button>
        </div>
      </div>

      {/* Рядок 1: тривалість + крапка + акциденції + октава + пауза + такт + ліґатура */}
      <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-ink/10 bg-ink/2 px-3 py-2">
        <span className="w-16 shrink-0 text-xs text-muted">Тривалість</span>
        {DURATIONS.map((d) => (
          <button key={d} type="button" onClick={() => setDuration(d)} className={btn(duration === d)}>
            {DURATION_LABEL[d]}
          </button>
        ))}
        <button
          type="button"
          onClick={() => setDot((v) => !v)}
          className={btn(dot)}
          title="Крапка — збільшує тривалість у 1.5 рази"
        >
          ·
        </button>
        <span className="mx-1 select-none text-ink/20">|</span>
        <button type="button" onClick={() => setAccidental('^')} className={btn(accidental === '^')}>♯</button>
        <button type="button" onClick={() => setAccidental('_')} className={btn(accidental === '_')}>♭</button>
        <button type="button" onClick={() => setAccidental('=')} className={btn(accidental === '=')}>♮</button>
        <span className="mx-1 select-none text-ink/20">|</span>
        <button type="button" onClick={() => setOctave((o) => Math.max(o - 1, -1))} className={btn(false)}>Oct ↓</button>
        <span className="w-5 text-center text-xs font-mono text-muted">{octaveLabel}</span>
        <button type="button" onClick={() => setOctave((o) => Math.min(o + 1, 2))} className={btn(false)}>Oct ↑</button>
        <span className="mx-1 select-none text-ink/20">|</span>
        <button type="button" onClick={() => insertAtCursor('z' + activeSuffix)} className={btn(false)}>
          Пауза
        </button>
        <button
          type="button"
          onClick={() => insertAtCursor(' | ')}
          className={btn(false) + ' font-mono font-bold'}
        >
          |
        </button>
        <button
          type="button"
          onClick={wrapInSlur}
          title="Ліґатура — виділіть ноти, потім натисніть"
          className={btn(false)}
        >
          ⌒
        </button>
      </div>

      {/* Рядок 2: ноти */}
      <div className="flex items-center gap-1.5 rounded-lg border border-ink/10 bg-ink/2 px-3 py-2">
        <span className="w-16 shrink-0 text-xs text-muted">Нота</span>
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
            → {accidental === '^' ? '♯' : accidental === '_' ? '♭' : '♮'} до наступної ноти
          </span>
        )}
      </div>

      {/* Рядок 3: акорди */}
      <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-ink/10 bg-ink/2 px-3 py-2">
        <span className="w-16 shrink-0 text-xs text-muted">Акорд</span>
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
          id={textareaId}
          ref={textareaRef}
          defaultValue={initialAbc}
          spellCheck={false}
          className="h-64 resize-none rounded-lg border border-ink/15 bg-white p-2.5 font-mono text-xs leading-relaxed text-ink/80 focus:border-accent/40 focus:outline-none"
        />
        <div className="overflow-auto rounded-lg border border-ink/10 bg-white p-2">
          <div id={paperId} />
        </div>
      </div>
    </div>
  )
}
