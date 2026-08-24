import { lazy, Suspense, useEffect, useState } from 'react'
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
import { useInputSource, type InputMode } from '../hooks/useInputSource'
import { useMidiPreview } from '../hooks/useMidiPreview'

const AbcPaper  = lazy(() => import('../components/AbcPaper').then(m => ({ default: m.AbcPaper })))
const AbcEditor = lazy(() => import('../components/AbcEditor').then(m => ({ default: m.AbcEditor })))

type ResultTab = 'score' | 'editor' | 'chords' | 'export'

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
  const analysis    = useAnalysis()
  const arrangement = useArrangement()

  const { inputMode, setInputMode, fileSize, abcGetRef, handleFile, handleClear, handleAnalyzeFromAbc } =
    useInputSource({
      analysisLoad:     analysis.load,
      arrangementClear: arrangement.clear,
      analysisReset:    analysis.reset,
    })

  const { midiHostRef, midiLoading, midiReady, handlePlayMidi } =
    useMidiPreview(arrangement.result?.musicxml)

  const [activeTab, setActiveTab] = useState<ResultTab>('score')

  const [mode,     setMode]     = useState<Mode>('suite')
  const [preset,   setPreset]   = useState('')
  const [seed,     setSeed]     = useState<number | null>(null)
  const [varyBass, setVaryBass] = useState(true)
  const [strophes, setStrophes] = useState(5)
  const [coda,     setCoda]     = useState(true)

  useEffect(() => {
    if (analysis.analysis?.presets.length) {
      setPreset(analysis.analysis.presets[0].id)
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
      <div className="relative z-10 mx-auto -mt-4 max-w-6xl px-3 sm:px-6">
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
              inputMode === 'abc' ? 'p-4' : 'p-6'
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

              {/* ABC notation editor */}
              {inputMode === 'abc' && (
                <div className="space-y-3">
                  <Suspense fallback={<div className="flex justify-center py-8"><Spinner /></div>}>
                    <AbcEditor onReady={(getAbc) => { abcGetRef.current = getAbc }} />
                  </Suspense>
                  <button
                    type="button"
                    onClick={handleAnalyzeFromAbc}
                    disabled={analysis.loading}
                    className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
                  >
                    {analysis.loading ? <Spinner /> : <Check className="h-4 w-4" />}
                    {analysis.loading ? 'Аналізую…' : 'Взяти ноти з редактора'}
                  </button>
                </div>
              )}
            </div>

            {/* Right — Settings */}
            <div className="w-full p-5 sm:p-6 md:w-72 md:shrink-0">
              <h3 className="font-semibold text-accent">Налаштування</h3>
              <div className="mt-4">
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
                  />
                ) : (
                  <button
                    type="button"
                    disabled
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-accent py-3 text-sm font-semibold text-white opacity-40"
                  >
                    <Music className="h-4 w-4" />
                    Створити партитуру
                  </button>
                )}
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
        <div className="mx-auto mt-6 max-w-6xl px-3 pb-12 sm:mt-8 sm:px-6 sm:pb-16">
          <div className="overflow-hidden rounded-2xl border border-ink/5 bg-white shadow-xl">
            {/* Mobile: horizontal tab bar */}
            <div className="flex overflow-x-auto border-b border-ink/10 md:hidden">
              {SIDEBAR_TABS.map(({ id, Icon, label }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setActiveTab(id)}
                  className={`flex shrink-0 items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition ${
                    activeTab === id
                      ? 'border-accent text-accent'
                      : 'border-transparent text-ink/55 hover:text-ink'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              ))}
            </div>

            <div className="flex md:min-h-160">
              {/* Desktop: vertical sidebar */}
              <div className="hidden w-48 shrink-0 border-r border-ink/10 p-4 md:block">
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

                        {displayTempo != null && (
                          <div className="flex items-center gap-1.5 text-sm">
                            <span className="text-muted">BPM</span>
                            <span className="font-medium">{displayTempo}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex-1 p-4">
                      {arrangement.result.abc ? (
                        <Suspense fallback={<div className="flex justify-center py-12"><Spinner /></div>}>
                          <AbcPaper abc={arrangement.result.abc} />
                        </Suspense>
                      ) : (
                        <p className="text-sm text-muted">
                          ABC-нотація недоступна для цього аранжування.
                        </p>
                      )}
                    </div>
                  </>
                )}

                {/* ─ Редактор ─ */}
                {activeTab === 'editor' && (
                  <div className="flex-1 p-5">
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
        </div>
      )}
    </>
  )
}
