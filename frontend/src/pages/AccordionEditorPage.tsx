import { useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { AccordionEditor } from '../components/AccordionEditor'
import type { AccordionHands } from '../api'

interface ResumeState {
  resumeTitle?: string
  resumeParams?: Partial<AccordionHands>
}

export function AccordionEditorPage() {
  const location = useLocation()
  // Стан з «Мої роботи» читаємо один раз: далі редактор живе власним станом.
  const resume = useRef(location.state as ResumeState | null)
  const [title, setTitle] = useState(resume.current?.resumeTitle ?? '')

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-12">
      <h1 className="font-display text-2xl font-bold text-ink">Редактор для баяна</h1>
      <p className="mt-1.5 max-w-2xl text-sm text-[#767c86]">
        Два нотні стани: права рука у скрипковому ключі, ліва — у басовому. Набирайте ноти кнопками або
        прямо в ABC-полі кожної руки, а готову партитуру збережіть у «Мої роботи» чи завантажте на комп'ютер.
      </p>
      <div className="mt-6">
        <AccordionEditor initial={resume.current?.resumeParams} title={title} onTitleChange={setTitle} />
      </div>
    </div>
  )
}
