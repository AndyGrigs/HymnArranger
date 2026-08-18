/**
 * Типи дзеркалять Pydantic-схеми з hymnarranger/api.py.
 * Змінюєш схему на бекенді — правиш і тут.
 */

/** Акордовий символ із абсолютним зміщенням у чвертках від початку п'єси. */
export interface ChordOut {
  offset: number
  figure: string
}

/** Пресет фактури, доступний для конкретного розміру. */
export interface PresetOut {
  id: string
  name: string
  tempo: number
  mode: string
}

/** Один розділ сюїти в плані, який повертає /analyze і /suite. */
export interface SuiteSection {
  index: number
  preset: string
  name: string
  tempo: number
  bass: string
}

/** Розділ у відповіді /merge — там лише пресет і назва. */
export interface MergeSection {
  preset: string
  name: string
}

/** POST /analyze */
export interface AnalyzeOut {
  meter: string
  meter_family: 'simple' | 'compound'
  key: string
  sharps: number
  measures: number
  total_ql: number
  pickup_ql: number
  chord_source: string
  chords: ChordOut[]
  warnings: string[]
  presets: PresetOut[]
  suite: SuiteSection[]
}

/** POST /arrange */
export interface ArrangeOut {
  musicxml: string
  preset: string
  name: string
  tempo: number
  meter: string
}

/** POST /suite */
export interface SuiteOut {
  musicxml: string
  meter: string
  meter_family: 'simple' | 'compound'
  seed: number | null
  sections: SuiteSection[]
}

/** POST /merge */
export interface MergeOut {
  musicxml: string
  meter: string
  sections: MergeSection[]
}

/** Один розділ у відповіді /style. */
export interface StyleSection {
  index: number
  texture: string
  name: string
  octave: number
  link_after: boolean
}

/** POST /style */
export interface StyleOut {
  musicxml: string
  style: string
  meter: string
  key: string
  sections: StyleSection[]
}

/** Параметри генерації стилю. */
export interface StyleParams {
  style?: string
  strophes?: number
  coda?: boolean
  [key: string]: unknown
}

/** GET /health */
export interface HealthOut {
  status: string
  [key: string]: unknown
}

/**
 * Джерело нот: або файл від користувача, або MusicXML рядком
 * (знадобиться, коли додамо вбудований редактор).
 */
export type ScoreSource = File | { musicxml: string }

/** Параметри генерації сюїти. */
export interface SuiteParams {
  seed?: number | null
  vary_bass?: boolean
  [key: string]: unknown
}