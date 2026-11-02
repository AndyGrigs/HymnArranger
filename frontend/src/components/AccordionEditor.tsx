import { useEffect, useId, useRef, useState } from 'react'
import abcjs from 'abcjs'
import { useTranslation } from 'react-i18next'
import { Download, Save } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api, ApiError, type AccordionHands } from '../api'
import { useAbcPlayback } from '../hooks/useAbcPlayback'
import { useAuth } from '../hooks/useAuth'
import { composeAccordionAbc, hasNotes } from '../lib/accordionAbc'
import { saveBlob, safeName } from '../lib/download'
import { Spinner } from './ui/Spinner'

type Hand = 'right' | 'left'
type Duration = 'whole' | 'half' | 'quarter' | 'eighth' | 'sixteenth'
type Accidental = '' | '^' | '_' | '='

const DURATION_SUFFIX: Record<Duration, string> = {
  whole: '8', half: '4', quarter: '2', eighth: '', sixteenth: '/2',
}
const DURATION_SUFFIX_DOTTED: Record<Duration, string> = {
  whole: '12', half: '6', quarter: '3', eighth: '3/2', sixteenth: '3/4',
}
const DURATION_LABEL: Record<Duration, string> = {
  whole: '𝅝', half: '𝅗𝅥', quarter: '♩', eighth: '♪', sixteenth: '𝅘𝅥𝅯',
}
const DURATIONS: Duration[] = ['whole', 'half', 'quarter', 'eighth', 'sixteenth']
const PITCHES = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
const KEY_PRESETS = [
  'C', 'G', 'D', 'A', 'E', 'B', 'F#', 'F', 'Bb', 'Eb', 'Ab', 'Db',
  'Am', 'Em', 'Bm', 'Dm', 'Gm', 'Cm',
]
const METER_PRESETS = ['4/4', '3/4', '6/8', '2/4', '3/8', '12/8']

// Ліва рука пише в басовому регістрі: за замовчуванням октава нижче.
const DEFAULT_OCTAVE: Record<Hand, number> = { right: 0, left: -1 }

interface Props {
  initial?: Partial<AccordionHands>
  title: string
  onTitleChange: (title: string) => void
  onSaved?: () => void
}

export function AccordionEditor({ initial, title, onTitleChange, onSaved }: Props) {
  const { t } = useTranslation()
  const handLabel = (h: Hand) => t(h === 'right' ? 'editors.accordion.right' : 'editors.accordion.left')
  const { token } = useAuth()
  const uid = useId().replace(/:/g, '')
  const paperId = `acc-paper-${uid}`

  const [right, setRight] = useState(initial?.right ?? '')
  const [left, setLeft] = useState(initial?.left ?? '')
  const [keySig, setKeySig] = useState(initial?.key ?? 'C')
  const [meter, setMeter] = useState(initial?.meter ?? '4/4')

  const [hand, setHand] = useState<Hand>('right')
  const [duration, setDuration] = useState<Duration>('eighth')
  const [dot, setDot] = useState(false)
  const [accidental, setAccidental] = useState<Accidental>('')
  const [octaves, setOctaves] = useState<Record<Hand, number>>(DEFAULT_OCTAVE)

  const [warnings, setWarnings] = useState<string[]>([])
  const [busy, setBusy] = useState<'save' | 'xml' | null>(null)
  const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)

  const areaRefs = useRef<Record<Hand, HTMLTextAreaElement | null>>({ right: null, left: null })
  // Остання позиція курсора в кожному полі: клік по кнопці знімає фокус.
  const cursorRef = useRef<Record<Hand, number | null>>({ right: null, left: null })
  const visualRef = useRef<abcjs.TuneObject | null>(null)

  const hands: AccordionHands = { right, left, key: keySig, meter }
  const abc = composeAccordionAbc(hands, title)
  const canSave = hasNotes(right) || hasNotes(left)
  const { playState, play, stop } = useAbcPlayback(() => visualRef.current, abc)

  useEffect(() => {
    const visual = abcjs.renderAbc(paperId, abc, { responsive: 'resize' })
    visualRef.current = visual?.[0] ?? null
    const parserWarnings = (visual?.[0]?.warnings ?? []).map((w: string) => w.replace(/<[^>]+>/g, ''))
    setWarnings(parserWarnings)
  }, [paperId, abc])

  function setText(h: Hand, value: string) {
    if (h === 'right') setRight(value)
    else setLeft(value)
  }

  function insert(text: string) {
    const current = hand === 'right' ? right : left
    const pos = Math.min(cursorRef.current[hand] ?? current.length, current.length)
    const before = current.slice(0, pos)
    const prev = before.slice(-1)
    const needsSpace = prev !== '' && prev !== ' ' && prev !== '\n' && prev !== '|' && !/^[\s|\n]/.test(text)
    const chunk = (needsSpace ? ' ' : '') + text
    setText(hand, before + chunk + current.slice(pos))
    const next = pos + chunk.length
    cursorRef.current[hand] = next
    // Повертаємо фокус і курсор вже після перерендеру.
    requestAnimationFrame(() => {
      const ta = areaRefs.current[hand]
      if (!ta) return
      ta.focus()
      ta.setSelectionRange(next, next)
    })
  }

  const suffix = dot ? DURATION_SUFFIX_DOTTED[duration] : DURATION_SUFFIX[duration]

  function insertNote(pitch: string) {
    const oct = octaves[hand]
    let p = pitch
    if (oct <= -1) p += ','.repeat(-oct)
    if (oct === 1) p = p.toLowerCase()
    if (oct >= 2) p = p.toLowerCase() + "'".repeat(oct - 1)
    insert(accidental + p + suffix)
    setAccidental('')
  }

  function shiftOctave(delta: number) {
    setOctaves((o) => ({ ...o, [hand]: Math.max(-2, Math.min(3, o[hand] + delta)) }))
  }

  function clearHand() {
    if (!(hand === 'right' ? right : left)) return
    if (!confirm(t('editors.accordion.confirmClear', { hand: handLabel(hand).toLowerCase() }))) return
    setText(hand, '')
    cursorRef.current[hand] = null
  }

  const fileTitle = title.trim() || t('editors.accordion.defaultTitle')

  function downloadAbc() {
    saveBlob(new Blob([abc], { type: 'text/vnd.abc' }), safeName(fileTitle, t('editors.accordion.fileSuffix'), 'abc'))
  }

  async function downloadMusicXml() {
    setBusy('xml')
    setMessage(null)
    try {
      const xml = await api.accordionMusicxml(hands)
      saveBlob(
        new Blob([xml], { type: 'application/vnd.recordare.musicxml+xml' }),
        safeName(fileTitle, t('editors.accordion.fileSuffix'), 'musicxml'),
      )
    } catch (err) {
      setMessage({ kind: 'error', text: err instanceof ApiError ? err.message : t('editors.accordion.downloadFailed') })
    } finally {
      setBusy(null)
    }
  }

  async function saveToWorks() {
    if (!token) return
    setBusy('save')
    setMessage(null)
    try {
      await api.saveAccordionWork(token, { ...hands, title: fileTitle, abc })
      setMessage({ kind: 'ok', text: t('editors.accordion.saved') })
      onSaved?.()
    } catch (err) {
      setMessage({ kind: 'error', text: err instanceof ApiError ? err.message : t('editors.accordion.saveFailed') })
    } finally {
      setBusy(null)
    }
  }

  const btn = (active: boolean) =>
    `rounded-[7px] border px-2 py-1 text-sm transition ${
      active
        ? 'border-accent/40 bg-tint font-medium text-accent'
        : 'border-[#dcdad2] bg-white text-[#454a52] hover:border-[#b6bac2] hover:text-ink'
    }`
  const rowClass = 'flex flex-wrap items-center gap-1.5 rounded-[10px] border border-[#ecebe6] bg-[#faf9f6] px-3.5 py-2.25'
  const labelClass = 'w-19.5 shrink-0 font-mono text-[10.5px] uppercase tracking-[.13em] text-[#8a9099]'
  const selectClass = 'rounded-[7px] border border-[#dcdad2] bg-white px-2 py-1.25 text-[13px] text-ink'
  // Клік по кнопці не має знімати фокус із поля з нотами.
  const noStealFocus = { onMouseDown: (e: { preventDefault: () => void }) => e.preventDefault() }

  const octaveLabel = (n: number) => (n > 0 ? `+${n}` : String(n))

  return (
    <div className="space-y-2">
      {/* Назва, тональність, розмір, відтворення */}
      <div className={rowClass + ' gap-2.5'}>
        <input
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
          maxLength={255}
          placeholder={t('editors.accordion.titlePlaceholder')}
          aria-label={t('editors.accordion.titlePlaceholder')}
          className="min-w-40 flex-1 rounded-[7px] border border-[#dcdad2] bg-white px-2.5 py-1.25 text-[13px] text-ink outline-none focus:border-accent"
        />
        <span className="font-mono text-[10.5px] uppercase tracking-[.13em] text-[#8a9099]">{t('editors.accordion.key')}</span>
        <select value={keySig} onChange={(e) => setKeySig(e.target.value)} className={selectClass}>
          {KEY_PRESETS.map((k) => <option key={k} value={k}>{k}</option>)}
        </select>
        <span className="font-mono text-[10.5px] uppercase tracking-[.13em] text-[#8a9099]">{t('editors.accordion.meter')}</span>
        <select value={meter} onChange={(e) => setMeter(e.target.value)} className={selectClass}>
          {METER_PRESETS.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <button
          type="button"
          onClick={playState === 'idle' ? play : stop}
          disabled={playState === 'loading' || (playState === 'idle' && !canSave)}
          className={`ml-auto flex items-center gap-1.5 rounded-full border px-3.5 py-1.25 text-[13px] font-medium transition disabled:opacity-50 ${
            playState === 'playing' || playState === 'paused'
              ? 'border-red-300 bg-red-50 text-red-600 hover:bg-red-100'
              : 'border-[#dcdad2] bg-white text-ink hover:border-accent hover:text-accent'
          }`}
        >
          {playState === 'playing' || playState === 'paused' ? t('editors.accordion.stop') : playState === 'loading' ? t('editors.accordion.preparing') : t('editors.accordion.play')}
        </button>
      </div>

      {/* Яка рука зараз приймає ноти з кнопок */}
      <div className={rowClass}>
        <span className={labelClass}>{t('editors.accordion.input')}</span>
        {(['right', 'left'] as Hand[]).map((h) => (
          <button key={h} type="button" onClick={() => setHand(h)} {...noStealFocus} className={btn(hand === h)}>
            {handLabel(h)}
          </button>
        ))}
        <button type="button" onClick={clearHand} {...noStealFocus} className={btn(false) + ' ml-auto'}>
          {t('editors.accordion.clear')}
        </button>
      </div>

      {/* Тривалість, акциденції, октава, пауза, такт */}
      <div className={rowClass}>
        <span className={labelClass}>{t('editors.accordion.duration')}</span>
        {DURATIONS.map((d) => (
          <button key={d} type="button" onClick={() => setDuration(d)} {...noStealFocus} className={btn(duration === d)}>
            {DURATION_LABEL[d]}
          </button>
        ))}
        <button
          type="button"
          onClick={() => setDot((v) => !v)}
          {...noStealFocus}
          className={btn(dot)}
          title={t('editors.accordion.dotTitle')}
        >
          ·
        </button>
        <span className="mx-2 block h-5 w-px bg-[#e3e1da]" />
        {([['^', '♯'], ['_', '♭'], ['=', '♮']] as const).map(([sign, label]) => (
          <button
            key={sign}
            type="button"
            onClick={() => setAccidental((a) => (a === sign ? '' : sign))}
            {...noStealFocus}
            className={btn(accidental === sign)}
          >
            {label}
          </button>
        ))}
        <span className="mx-2 block h-5 w-px bg-[#e3e1da]" />
        <button type="button" onClick={() => shiftOctave(-1)} {...noStealFocus} className={btn(false)}>Oct ↓</button>
        <span className="w-6 text-center font-mono text-xs text-[#8a9099]">{octaveLabel(octaves[hand])}</span>
        <button type="button" onClick={() => shiftOctave(1)} {...noStealFocus} className={btn(false)}>Oct ↑</button>
        <span className="mx-2 block h-5 w-px bg-[#e3e1da]" />
        <button type="button" onClick={() => insert('z' + suffix)} {...noStealFocus} className={btn(false)}>{t('editors.accordion.rest')}</button>
        <button type="button" onClick={() => insert(' | ')} {...noStealFocus} className={btn(false) + ' font-mono font-bold'}>|</button>
        <button type="button" onClick={() => insert(' |]')} {...noStealFocus} className={btn(false) + ' font-mono font-bold'} title={t('editors.accordion.endBar')}>|]</button>
        <button type="button" onClick={() => insert('\n')} {...noStealFocus} className={btn(false)} title={t('editors.accordion.newLine')}>↵</button>
      </div>

      {/* Ноти */}
      <div className={rowClass}>
        <span className={labelClass}>{t('editors.accordion.note')}</span>
        {PITCHES.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => insertNote(p)}
            {...noStealFocus}
            className="h-9 w-9 rounded-lg border border-[#dcdad2] bg-white font-display text-[19px] font-semibold text-ink transition hover:border-accent hover:bg-tint hover:text-accent"
          >
            {p}
          </button>
        ))}
        {accidental && (
          <span className="ml-1 text-xs text-accent">
            {t('editors.accordion.accidentalToNext', { sign: accidental === '^' ? '♯' : accidental === '_' ? '♭' : '♮' })}
          </span>
        )}
      </div>

      {warnings.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-700">
          {warnings.join(' · ')}
        </div>
      )}

      {/* Поля двох рук + прев'ю */}
      <div className="grid gap-3 md:grid-cols-[35%_1fr]">
        <div className="space-y-3">
          {(['right', 'left'] as Hand[]).map((h) => (
            <label key={h} className="block">
              <span className={`mb-1 block text-xs font-medium ${hand === h ? 'text-accent' : 'text-[#8a9099]'}`}>
                {handLabel(h)} · {t(h === 'right' ? 'editors.accordion.trebleClef' : 'editors.accordion.bassClef')}
              </span>
              <textarea
                ref={(el) => { areaRefs.current[h] = el }}
                value={h === 'right' ? right : left}
                onChange={(e) => {
                  setText(h, e.target.value)
                  cursorRef.current[h] = e.target.selectionStart
                }}
                onFocus={() => setHand(h)}
                onSelect={(e) => { cursorRef.current[h] = e.currentTarget.selectionStart }}
                spellCheck={false}
                placeholder={h === 'right' ? 'CDEF GABc |' : 'C,2 E,2 G,2 E,2 |'}
                className={`h-[13.25rem] w-full resize-none rounded-[10px] border bg-white p-3 font-mono text-xs leading-[1.75] text-[#3a3f47] outline-none focus:border-accent ${
                  hand === h ? 'border-accent/50' : 'border-[#dcdad2]'
                }`}
              />
            </label>
          ))}
        </div>
        <div className="ha-score overflow-auto rounded-[10px] border border-parchment-edge bg-parchment p-3 px-3.5" style={{ height: '28rem' }}>
          <div id={paperId} />
        </div>
      </div>

      {/* Збереження */}
      <div className={rowClass + ' gap-2.5'}>
        <button
          type="button"
          onClick={downloadAbc}
          disabled={!canSave || busy !== null}
          className="flex items-center gap-2 rounded border border-ink/15 px-3 py-2 text-sm transition hover:border-accent/40 disabled:opacity-50"
        >
          <Download className="h-4 w-4" />
          {t('editors.accordion.downloadAbc')}
        </button>
        <button
          type="button"
          onClick={downloadMusicXml}
          disabled={!canSave || busy !== null}
          className="flex items-center gap-2 rounded border border-ink/15 px-3 py-2 text-sm transition hover:border-accent/40 disabled:opacity-50"
        >
          {busy === 'xml' ? <Spinner /> : <Download className="h-4 w-4" />}
          {t('editors.accordion.downloadXml')}
        </button>
        {token ? (
          <button
            type="button"
            onClick={saveToWorks}
            disabled={!canSave || busy !== null}
            className="flex items-center gap-2 rounded border border-accent bg-white px-3 py-2 text-sm font-medium text-accent transition hover:bg-tint disabled:opacity-50"
          >
            {busy === 'save' ? <Spinner /> : <Save className="h-4 w-4" />}
            {t('editors.accordion.saveToWorks')}
          </button>
        ) : (
          <span className="text-sm text-[#767c86]">
            <Link to="/login" className="text-accent hover:underline">{t('editors.accordion.loginPrefix')}</Link>{t('editors.accordion.loginSuffix')}
          </span>
        )}
        {message && (
          <span className={`text-sm ${message.kind === 'ok' ? 'text-green-700' : 'text-accent'}`}>{message.text}</span>
        )}
      </div>
    </div>
  )
}
