import { useRef, useState } from 'react'
import type { ScoreSource } from '../api'

export type InputMode = 'upload' | 'abc'

interface Deps {
  analysisLoad:     (source: ScoreSource, name: string) => void
  arrangementClear: () => void
  analysisReset:    () => void
}

export function useInputSource({ analysisLoad, arrangementClear, analysisReset }: Deps) {
  const [inputMode, setInputMode] = useState<InputMode>('upload')
  const [fileSize,  setFileSize]  = useState<number | undefined>()
  const [resumedAbc, setResumedAbc] = useState<string | null>(null)
  const abcGetRef = useRef<(() => string) | null>(null)

  function handleFile(file: File) {
    setFileSize(file.size)
    arrangementClear()
    analysisLoad(file, file.name)
  }

  function handleClear() {
    setFileSize(undefined)
    arrangementClear()
    analysisReset()
  }

  function analyzeFromText(text: string, label: string) {
    if (!text?.trim()) return
    arrangementClear()
    analysisLoad(new File([text], 'melody.abc', { type: 'text/plain' }), label)
  }

  function handleAnalyzeFromAbc() {
    analyzeFromText(abcGetRef.current?.() ?? '', 'Мелодія з ABC-редактора')
  }

  return {
    inputMode, setInputMode,
    fileSize,
    abcGetRef,
    resumedAbc, setResumedAbc,
    handleFile, handleClear,
    analyzeFromText, handleAnalyzeFromAbc,
  }
}
