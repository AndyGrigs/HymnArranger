import type { SectionRow } from '../hooks/useArrangement'

export function SectionList({ sections }: { sections: SectionRow[] }) {
  if (sections.length <= 1) return null

  return (
    <ol className="divide-y divide-ink/5 rounded-lg border border-ink/10 bg-white">
      {sections.map((section, i) => (
        <li key={i} className="flex items-baseline justify-between px-4 py-2.5">
          <span className="text-sm">{section.label}</span>
          <span className="font-mono text-xs text-muted">{section.detail}</span>
        </li>
      ))}
    </ol>
  )
}