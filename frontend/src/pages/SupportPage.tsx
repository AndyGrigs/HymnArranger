import { ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

const FAQS: { q: string; a: string }[] = [
  {
    q: 'Які формати файлів підтримуються?',
    a: 'HymnArranger приймає MusicXML (.xml, .musicxml) та стиснений MusicXML (.mxl). ' +
      'Результат можна завантажити у тих самих форматах, а також у MIDI.',
  },
  {
    q: 'Чому система не знайшла акорди у моїй партитурі?',
    a: 'Акорди потрібно записати у вигляді символів над мелодією (наприклад, «C», «Am», «G7»). ' +
      'Якщо їх немає — система автоматично розставить базові тризвуки за ключом, але якість ' +
      'аранжування може бути нижчою. Рекомендуємо додати акорди вручну у будь-якому нотному редакторі.',
  },
  {
    q: 'Що означають попередження при аналізі?',
    a: 'Попередження сигналізують про потенційні проблеми: відсутні акорди, незвичний розмір, ' +
      'надто коротка або довга мелодія тощо. Вони не блокують аранжування, але варто з ними ознайомитись.',
  },
  {
    q: 'Як зберегти аранжування?',
    a: 'Зареєстровані користувачі можуть зберігати роботи через розділ «Мої роботи». ' +
      'Без реєстрації файл можна одразу завантажити на комп\'ютер після генерації.',
  },
  {
    q: 'Чи можна редагувати результат у браузері?',
    a: 'Так. Після генерації відображається вбудований нотний редактор. ' +
      'Зміни можна застосувати до партитури перед завантаженням.',
  },
  {
    q: 'Чому сторінка не завантажує файл?',
    a: 'Перевірте формат файлу (лише .xml, .musicxml, .mxl) і розмір (рекомендовано до 2 МБ). ' +
      'Якщо проблема залишається — спробуйте інший браузер або зверніться до нас.',
  },
]

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="border-b border-ink/10 last:border-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-4 py-4 text-left text-sm font-medium text-ink transition hover:text-accent"
      >
        {q}
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-muted transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open && (
        <p className="pb-4 text-sm leading-relaxed text-muted">{a}</p>
      )}
    </div>
  )
}

export function SupportPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <header className="mb-10">
        <h1 className="font-display text-3xl text-accent">Підтримка</h1>
        <p className="mt-1 text-muted">
          Відповіді на поширені питання та контакти для зв'язку
        </p>
      </header>

      {/* FAQ */}
      <section className="mb-10">
        <h2 className="mb-4 font-display text-xl text-ink">Часті питання</h2>
        <div className="rounded-lg border border-ink/10 bg-white px-5">
          {FAQS.map((item) => (
            <FaqItem key={item.q} {...item} />
          ))}
        </div>
      </section>

      {/* Contact */}
      <section className="mb-10 rounded-lg border border-ink/10 bg-white p-6">
        <h2 className="mb-1 font-display text-xl text-ink">Зв'язатися з нами</h2>
        <p className="mb-4 text-sm text-muted">
          Не знайшли відповіді? Напишіть — відповімо якнайшвидше.
        </p>
        <a
          href="mailto:andygrigs88@gmail.com"
          className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-accent/90"
        >
          Написати листа
        </a>
      </section>

      {/* Quick links */}
      <section>
        <h2 className="mb-4 font-display text-xl text-ink">Корисні розділи</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Link
            to="/how"
            className="rounded-lg border border-ink/10 bg-white p-4 text-sm transition hover:border-accent/40"
          >
            <p className="font-medium text-ink">Як це працює</p>
            <p className="mt-0.5 text-muted">Покрокова інструкція з використання сервісу</p>
          </Link>
          <Link
            to="/examples"
            className="rounded-lg border border-ink/10 bg-white p-4 text-sm transition hover:border-accent/40"
          >
            <p className="font-medium text-ink">Приклади аранжувань</p>
            <p className="mt-0.5 text-muted">Готові партитури для ознайомлення з результатом</p>
          </Link>
        </div>
      </section>
    </div>
  )
}
