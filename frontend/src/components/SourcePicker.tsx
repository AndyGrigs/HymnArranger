import { PenLine, Upload } from 'lucide-react'

export type SourceMode = 'upload' | 'compose'

interface Props {
  value: SourceMode
  onChange: (mode: SourceMode) => void
}

const TABS: { id: SourceMode; label: string; icon: typeof Upload }[] = [
  { id: 'upload', label: 'Завантажити файл', icon: Upload },
  { id: 'compose', label: 'Набрати ноти', icon: PenLine },
]

export function SourcePicker({ value, onChange }: Props) {
  return (
    <div className="flex gap-1 rounded-lg border border-ink/10 bg-white p-1">
      {TABS.map((tab) => {
        const Icon = tab.icon
        const active = value === tab.id
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={`flex flex-1 items-center justify-center gap-2 rounded px-3 py-2 text-sm transition ${
              active ? 'bg-accent text-white' : 'text-muted hover:bg-ink/5 hover:text-ink'
            }`}
          >
            <Icon className="h-4 w-4" />
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}