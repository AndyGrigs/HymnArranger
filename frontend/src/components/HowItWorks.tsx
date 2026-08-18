import { Upload, PenLine, Search, Wand2, FileOutput, ArrowRight } from 'lucide-react'

const STEPS = [
  {
    Icon: Upload,
    title: '1. Завантаж мелодію',
    text: 'Перетягни файл .mxl / .musicxml / .xml — або натисни «Написати мелодію» ' +
      'й введи ноти прямо в редакторі: клік у такт, цифра — тривалість, буква A–G — назва ноти.',
  },
  {
    Icon: Search,
    title: '2. Система аналізує ноти',
    text: 'HymnArranger визначає розмір і тональність, знаходить акорди над мелодією ' +
      'та показує попередження, якщо щось виглядає підозріло — до того, як щось генерувати.',
  },
  {
    Icon: Wand2,
    title: '3. Обери спосіб аранжування',
    text: '«Тема з варіаціями» — готова п\'єса з кількох розділів; «Одна фактура» — конкретний ' +
      'пресет на весь гімн; «Порівняння» — всі пресети підряд; «Стиль Сакали» — строфи з хроматичними ' +
      'зв\'язками і кодою. Налаштуй чергування баса, зерно генерації чи кількість строф — і натисни «Аранжувати».',
  },
  {
    Icon: FileOutput,
    title: '4. Переглянь і забери результат',
    text: 'Партитура зʼявляється одразу: можна прослухати MIDI, відредагувати ноти прямо в браузері ' +
      'й застосувати зміни, переглянути акорди по розділах, а тоді завантажити MusicXML, стиснений .mxl або MIDI.',
  },
]

interface Props {
  onStart: () => void
}

export function HowItWorks({ onStart }: Props) {
  return (
    <div className="mx-auto max-w-5xl px-4 pb-16 pt-10 sm:px-6 sm:pt-14">
      <div className="max-w-2xl">
        <h1 className="font-display text-3xl font-bold leading-tight text-ink sm:text-4xl">
          Як це працює
        </h1>
        <p className="mt-4 text-base leading-relaxed text-muted">
          Від мелодії до готової партитури для баяна — чотири кроки, без ручного набору
          акомпанементу.
        </p>
      </div>

      <div className="mt-10 grid gap-4 sm:grid-cols-2">
        {STEPS.map(({ Icon, title, text }) => (
          <div
            key={title}
            className="rounded-2xl border border-ink/10 bg-white p-5 shadow-sm sm:p-6"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/10">
              <Icon className="h-5 w-5 text-accent" />
            </div>
            <h2 className="mt-4 font-display text-lg text-ink">{title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">{text}</p>
          </div>
        ))}
      </div>

      <div className="mt-10 flex items-center gap-3 rounded-2xl border border-ink/10 bg-white/60 px-5 py-4 backdrop-blur-sm sm:px-6">
        <PenLine className="h-5 w-5 shrink-0 text-accent" />
        <p className="flex-1 text-sm text-ink/70">
          Немає готового файлу з нотами? Онлайн-редактор дозволяє написати мелодію з нуля.
        </p>
        <button
          type="button"
          onClick={onStart}
          className="flex shrink-0 items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
        >
          Спробувати
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
