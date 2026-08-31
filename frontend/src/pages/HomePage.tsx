import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Music, Music2, Download, Edit3, Loader2,
  Play, Check,
} from 'lucide-react'
import { FileDropzone } from '../components/FileDropzone'
import { GeneratePanel } from '../components/GeneratePanel'
import { AnalysisPanel } from '../components/AnalysisPanel'
import { SectionList } from '../components/SectionList'
import { MidiPlayer } from '../components/MidiPlayer'
import { DownloadBar } from '../components/DownloadBar'
import { Hero } from '../components/Hero'
import { Spinner } from '../components/ui/Spinner'
import { useAnalysis } from '../hooks/useAnalysis'
import { useArrangement, type Mode } from '../hooks/useArrangement'
import { useAuth } from '../hooks/useAuth'
import { useInputSource, type InputMode } from '../hooks/useInputSource'
import { useMidiPreview } from '../hooks/useMidiPreview'

const AbcPaper  = lazy(() => import('../components/AbcPaper').then(m => ({ default: m.AbcPaper })))
const AbcEditor = lazy(() => import('../components/AbcEditor').then(m => ({ default: m.AbcEditor })))

type ResultTab = 'score' | 'editor' | 'chords' | 'export'

type ResumeState = {
  resumeAbc: string
  resumeTitle: string
  resumeParams: Record<string, unknown>
} | null

const INPUT_TABS: { id: InputMode; label: string }[] = [
  { id: 'upload', label: 'Завантажити файл' },
  { id: 'abc',    label: 'ABC-нотація' },
]

const SIDEBAR_TABS: { id: ResultTab; Icon: React.FC<{ className?: string }>; label: string }[] = [
  { id: 'score',  Icon: Music,    label: 'Партитура' },
  { id: 'editor', Icon: Edit3,    label: 'Редактор'  },
  { id: 'chords', Icon: Music2,   label: 'Акорди'    },
  { id: 'export', Icon: Download, label: 'Експорт'   },
]

export function HomePage() {
  const location   = useLocation()
  const navigate   = useNavigate()
  const resumeRef  = useRef(location.state as ResumeState)

  const { user } = useAuth()
  const analysis    = useAnalysis()
  const arrangement = useArrangement()

  const {
    inputMode, setInputMode, fileSize, abcGetRef,
    resumedAbc, setResumedAbc,
    handleFile, handleClear, handleAnalyzeFromAbc, analyzeFromText,
  } = useInputSource({
    analysisLoad:     analysis.load,
    arrangementClear: arrangement.clear,
    analysisReset:    analysis.reset,
  })

  const { midiHostRef, midiLoading, midiReady, handlePlayMidi } =
    useMidiPreview(arrangement.result?.musicxml)

  const [activeTab, setActiveTab] = useState<ResultTab>('score')

  const [mode,     setMode]     = useState<Mode>('suite')
  const [preset,   setPreset]   = useState('')
  const [seed,     setSeed]     = useState<number | null>(
    () => (resumeRef.current?.resumeParams?.seed as number | null) ?? null
  )
  const [varyBass, setVaryBass] = useState(true)
  const [strophes, setStrophes] = useState(5)
  const [coda,     setCoda]     = useState(true)

  const handleAbcReady = useCallback((getAbc: () => string) => {
    abcGetRef.current = getAbc
  }, [abcGetRef])

  useEffect(() => {
    const state = resumeRef.current
    if (!state?.resumeAbc) return
    setInputMode('abc')
    setResumedAbc(state.resumeAbc)
    analyzeFromText(state.resumeAbc, state.resumeTitle ?? 'Мелодія')
    navigate('/', { replace: true })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (analysis.analysis?.presets.length) {
      const resumedPreset = resumeRef.current?.resumeParams?.preset as string | undefined
      const match = resumedPreset && analysis.analysis.presets.find(p => p.id === resumedPreset)
      setPreset(match ? match.id : analysis.analysis.presets[0].id)
    }
  }, [analysis.analysis])

  useEffect(() => {
    if (arrangement.result) setActiveTab('score')
  }, [arrangement.result])

  async function handleGenerate() {
    if (!analysis.source) return
    arrangement.generate(analysis.source, mode, { preset, seed, varyBass, strophes, coda })
  }

  const displayTempo = (() => {
    const raw = arrangement.result?.sections?.[0]?.detail
    const m = raw?.match(/^(\d+)/)
    return m ? parseInt(m[1]) : null
  })()

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <>
      <Hero />

      {/* ── Input card ──────────────────────────────────────────── */}
      <section className="mx-auto max-w-7xl px-8 pt-10">
        <div className="overflow-hidden rounded-[14px] border border-[#e3e1da] bg-white">

          {/* Card header: title + segmented tab control */}
          <div className="flex items-center gap-4 border-b border-[#ecebe6] px-5.5 py-4">
            <h2 className="font-display text-2xl font-semibold text-ink">Мелодія</h2>
            <div className="ml-auto flex gap-1 rounded-[9px] border border-[#e3e1da] bg-[#f8f7f4] p-0.75">
              {INPUT_TABS.map(({ id, label }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setInputMode(id)}
                  className={`rounded-md px-3.5 py-1.5 text-[13px] font-medium transition ${
                    inputMode === id
                      ? 'bg-white text-accent shadow-sm'
                      : 'bg-transparent text-[#767c86]'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-[1fr_auto]">
            {/* Left — input content */}
            <div className={`border-b border-[#ecebe6] md:border-b-0 md:border-r ${
              inputMode === 'abc' ? 'px-5.5 py-4.5' : 'p-5.5'
            }`}>

              {inputMode === 'upload' && (
                <FileDropzone
                  onFile={handleFile}
                  onClear={handleClear}
                  fileName={analysis.fileName}
                  fileSize={fileSize}
                  loading={analysis.loading}
                />
              )}

              {inputMode === 'abc' && (
                <div className="space-y-2.5">
                  <Suspense fallback={<div className="flex justify-center py-8"><Spinner /></div>}>
                    <AbcEditor
                      key={resumedAbc ?? 'new'}
                      initialAbc={resumedAbc ?? undefined}
                      onReady={handleAbcReady}
                    />
                  </Suspense>
                  <button
                    type="button"
                    onClick={handleAnalyzeFromAbc}
                    disabled={analysis.loading}
                    className="flex items-center gap-2 rounded-[9px] border border-accent bg-white px-4 py-2.5 text-[13.5px] font-medium text-accent transition hover:bg-tint disabled:opacity-50"
                  >
                    {analysis.loading ? <Spinner /> : <Check className="h-4 w-4" />}
                    {analysis.loading ? 'Аналізую…' : 'Взяти ноти з редактора'}
                  </button>
                </div>
              )}
            </div>

            {/* Right — Settings */}
            <div className="w-full p-5.5 md:w-79 md:shrink-0">
              <h2 className="font-display text-2xl font-semibold text-ink">Налаштування</h2>
              {analysis.analysis && (
                <p className="mt-1 font-mono text-[10.5px] uppercase tracking-[.13em] text-[#8a9099]">
                  Розмір {analysis.analysis.meter} · тональність {analysis.analysis.key}
                </p>
              )}
              <div className="mt-4.5">
                {analysis.analysis ? (
                  <GeneratePanel
                    bare
                    analysis={analysis.analysis}
                    mode={mode}
                    onModeChange={setMode}
                    preset={preset}
                    onPresetChange={setPreset}
                    seed={seed}
                    onSeedChange={setSeed}
                    varyBass={varyBass}
                    onVaryBassChange={setVaryBass}
                    strophes={strophes}
                    onStrophesChange={setStrophes}
                    coda={coda}
                    onCodaChange={setCoda}
                    onGenerate={handleGenerate}
                    loading={arrangement.loading}
                    isLoggedIn={!!user}
                  />
                ) : (
                  <button
                    type="button"
                    disabled
                    className="flex w-full items-center justify-center gap-2 rounded-[10px] bg-accent py-3 text-sm font-medium text-white opacity-40"
                  >
                    <Music className="h-4 w-4" />
                    Аранжувати
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Errors ──────────────────────────────────────────────── */}
      {(analysis.error || arrangement.error) && (
        <div className="mx-auto mt-4 max-w-7xl px-8">
          <div className="rounded-xl border border-accent/30 bg-tint/50 px-4 py-3 text-sm text-accent">
            {analysis.error || arrangement.error}
          </div>
        </div>
      )}

      {/* ── Results ─────────────────────────────────────────────── */}
      {arrangement.result && (
        <section className="mx-auto mt-6 max-w-7xl px-8 pb-18">
          <div className="overflow-hidden rounded-[14px] border border-[#e3e1da] bg-white">

            {/* Results header */}
            <div className="flex flex-wrap items-center gap-3.5 border-b border-[#ecebe6] px-6 py-4">
              <h2 className="font-display text-[26px] font-semibold text-ink">
                {arrangement.result.title}
              </h2>
              <span className="rounded-full border border-[#e3e1da] px-2.75 py-0.75 font-mono text-[10.5px] uppercase tracking-[.11em] text-[#8a9099]">
                Попередній перегляд
              </span>
              <div className="ml-auto flex items-center gap-4.5">
                <div className="flex items-center gap-2.5">
                  {!midiReady && (
                    <button
                      type="button"
                      onClick={handlePlayMidi}
                      disabled={midiLoading}
                      className="flex h-8.5 w-8.5 items-center justify-center rounded-full bg-accent text-white transition hover:brightness-110 disabled:opacity-50"
                    >
                      {midiLoading
                        ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        : <Play className="ml-0.5 h-3.5 w-3.5" />
                      }
                    </button>
                  )}
                  {/* Waveform decoration */}
                  <span className="flex items-end gap-0.5 h-4">
                    {[6, 12, 9, 15, 7, 11].map((h, i) => (
                      <span key={i} className="block w-0.5 bg-[#d3d6dc]" style={{ height: h }} />
                    ))}
                  </span>
                  <div ref={midiHostRef} className={midiReady ? 'min-w-55' : ''} />
                </div>
                {displayTempo != null && (
                  <span className="font-mono text-[11.5px] uppercase tracking-widest text-[#8a9099]">
                    {displayTempo} BPM
                  </span>
                )}
              </div>
            </div>

            <div className="flex md:min-h-150">
              {/* Desktop sidebar */}
              <div className="hidden w-49 shrink-0 border-r border-[#ecebe6] p-4 md:block">
                <nav className="space-y-0.5">
                  {SIDEBAR_TABS.map(({ id, Icon, label }) => (
                    <button
                      key={id}
                      type="button"
                      onClick={() => setActiveTab(id)}
                      className={`flex w-full items-center gap-2.75 rounded-[9px] px-3 py-2.5 text-[13.5px] text-left transition ${
                        activeTab === id
                          ? 'bg-tint font-semibold text-accent'
                          : 'bg-transparent font-normal text-[#6b717a] hover:bg-ink/5'
                      }`}
                    >
                      <Icon className="h-3.75 w-3.75 shrink-0" />
                      {label}
                    </button>
                  ))}
                </nav>
              </div>

              {/* Mobile tab bar */}
              <div className="flex overflow-x-auto border-b border-[#ecebe6] md:hidden w-full">
                {SIDEBAR_TABS.map(({ id, Icon, label }) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setActiveTab(id)}
                    className={`flex shrink-0 items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition ${
                      activeTab === id
                        ? 'border-accent text-accent'
                        : 'border-transparent text-[#6b717a] hover:text-ink'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </button>
                ))}
              </div>

              {/* Content area */}
              <div className="flex min-w-0 flex-1 flex-col bg-[#fcfcfa]">

                {/* ─ Партитура ─ */}
                {activeTab === 'score' && (
                  <div className="flex-1 p-[26px_30px_34px]">
                    {arrangement.result.abc ? (
                      <div
                        className="rounded-xl border border-parchment-edge bg-parchment"
                        style={{
                          padding: '34px 38px',
                          boxShadow: '0 1px 2px rgba(28,30,34,.04),0 22px 44px -34px rgba(28,30,34,.4)',
                        }}
                      >
                        <div className="ha-score">
                          <Suspense fallback={<div className="flex justify-center py-12"><Spinner /></div>}>
                            <AbcPaper abc={arrangement.result.abc} className="" />
                          </Suspense>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-muted">
                        ABC-нотація недоступна для цього аранжування.
                      </p>
                    )}
                  </div>
                )}

                {/* ─ Редактор ─ */}
                {activeTab === 'editor' && (
                  <div className="flex-1 p-[24px_30px]">
                    {arrangement.result.abc ? (
                      <Suspense fallback={<div className="flex justify-center py-12"><Spinner /></div>}>
                        <AbcEditor
                          key={arrangement.result.abc}
                          initialAbc={arrangement.result.abc}
                        />
                      </Suspense>
                    ) : (
                      <p className="text-sm text-muted">
                        ABC-нотація недоступна для цього аранжування.
                      </p>
                    )}
                  </div>
                )}

                {/* ─ Акорди ─ */}
                {activeTab === 'chords' && (
                  <div className="p-[26px_30px] space-y-5">
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
                  <div className="p-[26px_30px] space-y-5">
                    <MidiPlayer
                      source={{ musicxml: arrangement.result.musicxml }}
                      resetKey={
                        JSON.stringify(arrangement.result.params) +
                        arrangement.result.mode
                      }
                    />
                    <DownloadBar
                      mode={arrangement.result.mode}
                      musicxml={arrangement.result.musicxml}
                      fileName={analysis.fileName ?? 'гімн'}
                    />
                  </div>
                )}

              </div>
            </div>
          </div>
        </section>
      )}
    </>
  )
}
