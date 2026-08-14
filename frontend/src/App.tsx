import { useEffect, useState } from 'react'
import { FileDropzone } from './components/FileDropzone'
import { AnalysisPanel } from './components/AnalysisPanel'
import { GeneratePanel } from './components/GeneratePanel'
import { SheetViewer } from './components/SheetViewer'
import { SectionList } from './components/SectionList'
import { useAnalysis } from './hooks/useAnalysis'
import { useArrangement, type Mode } from './hooks/useArrangement'
import { MidiPlayer } from './components/MidiPlayer'
import { DownloadBar } from './components/DownloadBar'
import { ScoreEditor } from './components/ScoreEditor'
import { SourcePicker, type SourceMode } from './components/SourcePicker'

export default function App() {
  const analysis = useAnalysis()
  const arrangement = useArrangement()

  const [fileSize, setFileSize] = useState<number | undefined>()
  const [mode, setMode] = useState<Mode>('suite')
  const [preset, setPreset] = useState('')
  const [seed, setSeed] = useState<number | null>(null)
  const [varyBass, setVaryBass] = useState(true)
  const [sourceMode, setSourceMode] = useState<SourceMode>('upload')

  // Набір пресетів залежить від розміру, тож після кожного аналізу
  // ставимо перший доступний — інакше в select лишиться id з попереднього файлу.
  useEffect(() => {
    if (analysis.analysis?.presets.length) {
      setPreset(analysis.analysis.presets[0].id)
    }
  }, [analysis.analysis])

  function handleFile(file: File) {
    setFileSize(file.size)
    arrangement.clear()
    analysis.load(file, file.name)
  }

  // Ноти з редактора приходять рядком — бекенд приймає їх тим самим
  // ендпоінтом, лише в JSON-тілі замість multipart.
  function handleComposed(musicxml: string) {
    setFileSize(undefined)
    arrangement.clear()
    analysis.load({ musicxml }, 'Мелодія з редактора')
  }

  function handleClear() {
    setFileSize(undefined)
    arrangement.clear()
    analysis.reset()
  }

  function handleGenerate() {
    if (!analysis.source) return
    arrangement.generate(analysis.source, mode, { preset, seed, varyBass })
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl text-accent">HymnArranger</h1>
        <p className="mt-1 text-muted">
          Автоматичне баянне аранжування з мелодії та акордових символів
        </p>
      </header>

      <div className="space-y-6">
        <SourcePicker
          value={sourceMode}
          onChange={(mode) => {
            setSourceMode(mode)
            handleClear()
          }}
        />

        {sourceMode === 'upload' ? (
          <FileDropzone
            onFile={handleFile}
            onClear={handleClear}
            fileName={analysis.fileName}
            fileSize={fileSize}
            loading={analysis.loading}
          />
        ) : (
          <ScoreEditor onSubmit={handleComposed} busy={analysis.loading} />
        )}

        {analysis.error && (
          <div className="rounded-lg border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
            {analysis.error}
          </div>
        )}

        {analysis.analysis && (
          <>
            <AnalysisPanel data={analysis.analysis} />

            <GeneratePanel
              analysis={analysis.analysis}
              mode={mode}
              onModeChange={setMode}
              preset={preset}
              onPresetChange={setPreset}
              seed={seed}
              onSeedChange={setSeed}
              varyBass={varyBass}
              onVaryBassChange={setVaryBass}
              onGenerate={handleGenerate}
              loading={arrangement.loading}
            />
          </>
        )}

        {arrangement.error && (
          <div className="rounded-lg border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
            {arrangement.error}
          </div>
        )}

       {arrangement.result && analysis.source && (
          <div className="space-y-4">
            <h2 className="font-display text-xl">{arrangement.result.title}</h2>

            <SectionList sections={arrangement.result.sections} />

            <MidiPlayer
              source={analysis.source}
              params={
                arrangement.result.mode === 'preset'
                  ? { preset: arrangement.result.params.preset }
                  : { seed: arrangement.result.params.seed ?? null }
              }
              resetKey={JSON.stringify(arrangement.result.params) + arrangement.result.mode}
            />

            <SheetViewer musicxml={arrangement.result.musicxml} />

            <DownloadBar
              source={analysis.source}
              mode={arrangement.result.mode}
              params={arrangement.result.params}
              musicxml={arrangement.result.musicxml}
              fileName={analysis.fileName ?? 'гімн'}
            />
          </div>
        )}
      </div>
    </div>
  )
}