import { useEffect, useMemo, useRef, useState } from 'react'
import type Embed from 'flat-embed'
import {
  Music, Music2, Download, Edit3, Loader2,
  Play, Link, Check,
} from 'lucide-react'
import { FileDropzone } from './components/FileDropzone'
import { AnalysisPanel } from './components/AnalysisPanel'
import { SheetViewer } from './components/SheetViewer'
import { SectionList } from './components/SectionList'
import { FlatEmbedEditor } from './components/FlatEmbedEditor'
import { MidiPlayer } from './components/MidiPlayer'
import { DownloadBar } from './components/DownloadBar'
import { Navbar } from './components/Navbar'
import { Hero } from './components/Hero'
import { Spinner } from './components/ui/Spinner'
import { useAnalysis } from './hooks/useAnalysis'
import { useArrangement, type Mode } from './hooks/useArrangement'
import { blankMusicXML, KEY_OPTIONS, METER_OPTIONS } from './lib/blankScore'
import { api } from './api'

const SOUNDFONT = 'https://storage.googleapis.com/magentadata/js/soundfonts/sgm_plus'
let midiRegistered = false
async function ensureMidiPlayer() {
  if (!midiRegistered) {
    await import('html-midi-player')
    midiRegistered = true
  }
}

type InputMode = 'upload' | 'compose' | 'url'
type ResultTab = 'score' | 'editor' | 'chords' | 'export'

const INPUT_TABS: { id: InputMode; label: string }[] = [
  { id: 'upload',  label: 'Завантажити файл'  },
  { id: 'compose', label: 'Написати мелодію'  },
  { id: 'url',     label: 'Вставити посилання' },
]

const SIDEBAR_TABS: { id: ResultTab; Icon: React.FC<{ className?: string }>; label: string }[] = [
  { id: 'score',  Icon: Music,    label: 'Партитура' },
  { id: 'editor', Icon: Edit3,    label: 'Редактор'  },
  { id: 'chords', Icon: Music2,   label: 'Акорди'    },
  { id: 'export', Icon: Download, label: 'Експорт'   },
]

export default function App() {
  const analysis    = useAnalysis()
  const arrangement = useArrangement()

  // Ref to the compose-mode editor (input melody)
  const composeEmbedRef = useRef<Embed | null>(null)
  // Ref to the result-editor (post-arrangement editing)
  const flatEmbedRef    = useRef<Embed | null>(null)

  // UI state
  const [inputMode,      setInputMode]      = useState<InputMode>('upload')
  const [activeTab,      setActiveTab]      = useState<ResultTab>('score')
  const [fileSize,       setFileSize]       = useState<number | undefined>()
  const [urlInput,       setUrlInput]       = useState('')
  const [composeLoading, setComposeLoading] = useState(false)

  // Settings (meter/key sync with analysis result when available)
  const [editorMeter,  setEditorMeter]  = useState('4/4')
  const [editorFifths, setEditorFifths] = useState(0)
  const [bpm,          setBpm]          = useState(84)

  // Blank MusicXML for compose mode — remounts editor when meter/key change
  const blankXml = useMemo(
    () => blankMusicXML({ meter: editorMeter, fifths: editorFifths, measures: 16 }),
    [editorMeter, editorFifths],
  )

  // Generation params
  const [mode]     = useState<Mode>('suite')
  const [preset,   setPreset]   = useState('')
  const [seed]     = useState<number | null>(null)
  const [varyBass] = useState(true)

  // Inline MIDI player in the Партитура toolbar
  const midiHostRef = useRef<HTMLDivElement>(null)
  const midiUrlRef  = useRef<string | null>(null)
  const [midiLoading, setMidiLoading] = useState(false)
  const [midiReady,   setMidiReady]   = useState(false)

  // Reflect detected meter/key in the settings panel
  useEffect(() => {
    if (!analysis.analysis) return
    setEditorMeter(analysis.analysis.meter)
    setEditorFifths(analysis.analysis.sharps)
  }, [analysis.analysis])

  useEffect(() => {
    if (analysis.analysis?.presets.length) {
      setPreset(analysis.analysis.presets[0].id)
    }
  }, [analysis.analysis])

  // Show score tab as soon as a new arrangement lands
  useEffect(() => {
    if (arrangement.result) setActiveTab('score')
  }, [arrangement.result])

  // Reset inline MIDI player when arrangement changes
  useEffect(() => {
    if (midiUrlRef.current) {
      URL.revokeObjectURL(midiUrlRef.current)
      midiUrlRef.current = null
    }
    if (midiHostRef.current) midiHostRef.current.innerHTML = ''
    setMidiReady(false)
    setMidiLoading(false)
  }, [arrangement.result?.musicxml])

  // ── Handlers ──────────────────────────────────────────────────────────────

  function handleFile(file: File) {
    setFileSize(file.size)
    arrangement.clear()
    analysis.load(file, file.name)
  }

  function handleClear() {
    setFileSize(undefined)
    arrangement.clear()
    analysis.reset()
  }

  async function handleAnalyzeFromCompose() {
    const embed = composeEmbedRef.current
    if (!embed) return
    setComposeLoading(true)
    try {
      const xml = await embed.getMusicXML()
      if (typeof xml === 'string') {
        arrangement.clear()
        analysis.load({ musicxml: xml }, 'Мелодія з редактора')
      }
    } finally {
      setComposeLoading(false)
    }
  }

  async function handleGenerate() {
    if (!analysis.source) return
    arrangement.generate(analysis.source, mode, { preset, seed, varyBass })
  }

  async function handlePlayMidi() {
    if (!arrangement.result || midiLoading || midiReady) return
    setMidiLoading(true)
    try {
      await ensureMidiPlayer()
      const blob = await api.midi({ musicxml: arrangement.result.musicxml })
      if (midiUrlRef.current) URL.revokeObjectURL(midiUrlRef.current)
      const url = URL.createObjectURL(blob)
      midiUrlRef.current = url
      const player = document.createElement('midi-player')
      player.setAttribute('sound-font', SOUNDFONT)
      player.setAttribute('src', url)
      player.style.width = '100%'
      if (midiHostRef.current) {
        midiHostRef.current.innerHTML = ''
        midiHostRef.current.appendChild(player)
      }
      setMidiReady(true)
    } catch {
      // user can fall back to Export tab
    } finally {
      setMidiLoading(false)
    }
  }

  // Parse tempo from first section detail string "84 уд/хв · …"
  const displayTempo = (() => {
    const raw = arrangement.result?.sections?.[0]?.detail
    if (!raw) return bpm
    const m = raw.match(/^(\d+)/)
    return m ? parseInt(m[1]) : bpm
  })()

  const btnBase =
    'flex h-7 w-7 items-center justify-center rounded border border-ink/15 text-sm text-muted transition hover:bg-ink/5'

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen">
      <Navbar />
      <Hero />

      {/* ── Input card ──────────────────────────────────────────── */}
      <div className="relative z-10 mx-auto -mt-4 max-w-6xl px-6">
        <div className="overflow-hidden rounded-2xl border border-ink/5 bg-white shadow-xl">
          {/* Input mode tabs */}
          <div className="flex border-b border-ink/10">
            {INPUT_TABS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                onClick={() => setInputMode(id)}
                className={`px-6 py-3.5 text-sm font-medium transition ${
                  inputMode === id
                    ? 'border-b-2 border-accent text-accent'
                    : 'text-muted hover:text-ink'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-[1fr_auto]">
            {/* Left — input content */}
            <div className={`border-b border-ink/10 md:border-b-0 md:border-r ${
              inputMode === 'compose' ? 'p-4' : 'p-6'
            }`}>

              {/* File upload */}
              {inputMode === 'upload' && (
                <FileDropzone
                  onFile={handleFile}
                  onClear={handleClear}
                  fileName={analysis.fileName}
                  fileSize={fileSize}
                  loading={analysis.loading}
                />
              )}

              {/* Compose melody */}
              {inputMode === 'compose' && (
                <div className="space-y-3">
                  <FlatEmbedEditor
                    key={`compose-${editorMeter}-${editorFifths}`}
                    musicXml={blankXml}
                    onEmbedChange={(embed) => { composeEmbedRef.current = embed }}
                    height="480px"
                  />
                  <button
                    type="button"
                    onClick={handleAnalyzeFromCompose}
                    disabled={composeLoading || analysis.loading}
                    className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
                  >
                    {composeLoading || analysis.loading
                      ? <Spinner />
                      : <Check className="h-4 w-4" />
                    }
                    {composeLoading || analysis.loading
                      ? 'Аналізую…'
                      : 'Взяти ноти з редактора'
                    }
                  </button>
                </div>
              )}

              {/* URL input */}
              {inputMode === 'url' && (
                <div className="space-y-3">
                  <p className="text-xs text-muted">
                    YouTube, SoundCloud або інше посилання на мелодію
                  </p>
                  <div className="relative">
                    <input
                      type="url"
                      value={urlInput}
                      onChange={(e) => setUrlInput(e.target.value)}
                      placeholder="Вставте посилання"
                      className="w-full rounded-lg border border-ink/15 bg-white px-4 py-2.5 pr-10 text-sm outline-none transition focus:border-accent/50 focus:ring-1 focus:ring-accent/20"
                    />
                    <Link className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
                  </div>
                  <button
                    disabled
                    className="w-full cursor-not-allowed rounded-lg border border-ink/10 bg-ink/5 py-2.5 text-sm text-muted/50"
                  >
                    Завантажити
                  </button>
                  <p className="text-center text-xs text-muted/40">Незабаром доступно</p>
                </div>
              )}
            </div>

            {/* Right — Settings */}
            <div className="w-72 shrink-0 p-6">
              <h3 className="font-semibold text-accent">Налаштування</h3>
              <div className="mt-4 space-y-4">

                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted">Розмір</span>
                  <select
                    value={editorMeter}
                    onChange={(e) => setEditorMeter(e.target.value)}
                    className="rounded-lg border border-ink/15 bg-white px-3 py-1.5 text-sm"
                  >
                    {METER_OPTIONS.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>

                <div className="flex items-start justify-between gap-3">
                  <span className="mt-1.5 shrink-0 text-sm text-muted">Тональність</span>
                  <select
                    value={editorFifths}
                    onChange={(e) => setEditorFifths(Number(e.target.value))}
                    className="min-w-0 flex-1 rounded-lg border border-ink/15 bg-white px-3 py-1.5 text-sm"
                  >
                    {KEY_OPTIONS.map((k) => (
                      <option key={k.fifths} value={k.fifths}>{k.label}</option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted">Темп (BPM)</span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setBpm((b) => Math.max(40, b - 4))}
                      className={btnBase}
                    >—</button>
                    <span className="w-10 text-center text-sm font-medium">{bpm}</span>
                    <button
                      type="button"
                      onClick={() => setBpm((b) => Math.min(240, b + 4))}
                      className={btnBase}
                    >+</button>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleGenerate}
                  disabled={!analysis.source || arrangement.loading || analysis.loading}
                  className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-accent py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
                >
                  {arrangement.loading ? <Spinner /> : <Music className="h-4 w-4" />}
                  {arrangement.loading ? 'Генерую…' : 'Створити партитуру'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Errors ──────────────────────────────────────────────── */}
      {(analysis.error || arrangement.error) && (
        <div className="mx-auto mt-4 max-w-6xl px-6">
          <div className="rounded-xl border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
            {analysis.error || arrangement.error}
          </div>
        </div>
      )}

      {/* ── Results ─────────────────────────────────────────────── */}
      {arrangement.result && (
        <div className="mx-auto mt-8 max-w-6xl px-6 pb-16">
          <div className="overflow-hidden rounded-2xl border border-ink/5 bg-white shadow-xl">
            <div className="flex min-h-160">

              {/* Sidebar */}
              <div className="w-48 shrink-0 border-r border-ink/10 p-4">
                <nav className="space-y-1">
                  {SIDEBAR_TABS.map(({ id, Icon, label }) => (
                    <button
                      key={id}
                      type="button"
                      onClick={() => setActiveTab(id)}
                      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                        activeTab === id
                          ? 'bg-accent/10 font-medium text-accent'
                          : 'text-ink/55 hover:bg-ink/5 hover:text-ink'
                      }`}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      {label}
                    </button>
                  ))}
                </nav>
              </div>

              {/* Content */}
              <div className="flex min-w-0 flex-1 flex-col">

                {/* ─ Партитура ─ */}
                {activeTab === 'score' && (
                  <>
                    <div className="flex flex-wrap items-center gap-3 border-b border-ink/10 px-5 py-3">
                      <span className="font-semibold text-ink/80">
                        {arrangement.result.title}
                      </span>
                      <span className="rounded-full bg-ink/5 px-2.5 py-0.5 text-xs text-muted">
                        Попередній перегляд
                      </span>

                      <div className="ml-auto flex flex-wrap items-center gap-4">
                        {!midiReady && (
                          <button
                            type="button"
                            onClick={handlePlayMidi}
                            disabled={midiLoading}
                            className="flex h-8 w-8 items-center justify-center rounded-full bg-accent text-white shadow transition hover:opacity-90 disabled:opacity-50"
                          >
                            {midiLoading
                              ? <Loader2 className="h-4 w-4 animate-spin" />
                              : <Play className="ml-0.5 h-4 w-4" />
                            }
                          </button>
                        )}
                        <div ref={midiHostRef} className={midiReady ? 'min-w-55' : ''} />

                        <div className="flex items-center gap-1.5 text-sm">
                          <span className="text-muted">BPM</span>
                          <span className="font-medium">{displayTempo}</span>
                          <button type="button" className="text-muted/40 transition hover:text-muted">—</button>
                          <button type="button" className="text-muted/40 transition hover:text-muted">+</button>
                        </div>

                        <div className="flex items-center gap-1.5 text-sm">
                          <span className="text-muted">Транспонувати</span>
                          <span className="font-medium">0</span>
                          <button type="button" className="text-muted/40 transition hover:text-muted">—</button>
                          <button type="button" className="text-muted/40 transition hover:text-muted">+</button>
                        </div>
                      </div>
                    </div>

                    <div className="flex-1 p-4">
                      <SheetViewer musicxml={arrangement.result.musicxml} />
                    </div>
                  </>
                )}

                {/* ─ Редактор ─ */}
                {activeTab === 'editor' && (
                  <div className="flex-1 p-5">
                    <p className="mb-3 text-sm text-muted">
                      Редагуй аранжування прямо тут. Зміни враховуються при експорті.
                    </p>
                    <FlatEmbedEditor
                      musicXml={arrangement.result.musicxml}
                      onEmbedChange={(embed) => { flatEmbedRef.current = embed }}
                      height="600px"
                    />
                  </div>
                )}

                {/* ─ Акорди ─ */}
                {activeTab === 'chords' && (
                  <div className="p-5 space-y-5">
                    {analysis.analysis ? (
                      <>
                        <AnalysisPanel data={analysis.analysis} />
                        <SectionList sections={arrangement.result.sections} />
                      </>
                    ) : (
                      <p className="text-sm text-muted">Немає даних аналізу.</p>
                    )}
                  </div>
                )}

                {/* ─ Експорт ─ */}
                {activeTab === 'export' && (
                  <div className="p-5 space-y-5">
                    <MidiPlayer
                      source={{ musicxml: arrangement.result.musicxml }}
                      resetKey={
                        JSON.stringify(arrangement.result.params) +
                        arrangement.result.mode
                      }
                    />
                    {analysis.source && (
                      <DownloadBar
                        source={analysis.source}
                        mode={arrangement.result.mode}
                        params={arrangement.result.params}
                        musicxml={arrangement.result.musicxml}
                        fileName={analysis.fileName ?? 'гімн'}
                      />
                    )}
                  </div>
                )}

              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
