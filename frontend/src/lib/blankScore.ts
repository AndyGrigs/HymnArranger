/**
 * Порожній шаблон MusicXML для редактора: один нотоносець у скрипковому
 * ключі, задана тональність і розмір, потрібна кількість тактів пауз.
 *
 * Flat уміє почати з чистого аркуша сам, але тоді користувач мусив би
 * шукати в меню розмір і знаки — а тут він задає їх до відкриття редактора.
 */

export interface TemplateOptions {
  meter: string
  fifths: number
  measures: number
  title?: string
}

/** Кількість чвертей у такті: "3/4" → 3, "6/8" → 3. */
function barQuarters(meter: string): number {
  const [num, den] = meter.split('/').map(Number)
  return (num * 4) / den
}

const DIVISIONS = 4 // одиниць на чвертку

export function blankMusicXML(opts: TemplateOptions): string {
  const [beats, beatType] = opts.meter.split('/')
  const barDuration = barQuarters(opts.meter) * DIVISIONS
  const title = opts.title || 'Мелодія'

  const measures = Array.from({ length: opts.measures }, (_, i) => {
    // Ключ, тональність і розмір виписуються лише в першому такті.
    const attributes =
      i === 0
        ? `
      <attributes>
        <divisions>${DIVISIONS}</divisions>
        <key><fifths>${opts.fifths}</fifths></key>
        <time><beats>${beats}</beats><beat-type>${beatType}</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>`
        : ''

    return `    <measure number="${i + 1}">${attributes}
      <note>
        <rest measure="yes"/>
        <duration>${barDuration}</duration>
        <voice>1</voice>
      </note>
    </measure>`
  }).join('\n')

  return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN"
  "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>${title}</work-title></work>
  <part-list>
    <score-part id="P1">
      <part-name>Мелодія</part-name>
    </score-part>
  </part-list>
  <part id="P1">
${measures}
  </part>
</score-partwise>`
}

/** Тональності для випадаючого списку: підпис і кількість знаків. */
export const KEY_OPTIONS: { label: string; fifths: number }[] = [
  { label: 'До мажор / ля мінор', fifths: 0 },
  { label: 'Соль мажор / мі мінор', fifths: 1 },
  { label: 'Ре мажор / сі мінор', fifths: 2 },
  { label: 'Ля мажор / фа-дієз мінор', fifths: 3 },
  { label: 'Мі мажор / до-дієз мінор', fifths: 4 },
  { label: 'Фа мажор / ре мінор', fifths: -1 },
  { label: 'Сі-бемоль мажор / соль мінор', fifths: -2 },
  { label: 'Мі-бемоль мажор / до мінор', fifths: -3 },
  { label: 'Ля-бемоль мажор / фа мінор', fifths: -4 },
]

export const METER_OPTIONS = ['2/4', '3/4', '4/4', '6/8', '9/8', '12/8']