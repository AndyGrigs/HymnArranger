import type { ReactNode } from 'react'

interface CardProps {
  title?: string
  children: ReactNode
  className?: string
}

export function Card({ title, children, className = '' }: CardProps) {
  return (
    <section
      className={`rounded-lg border border-ink/10 bg-white p-5 shadow-sm ${className}`}
    >
      {title && (
        <h2 className="mb-4 font-display text-lg text-ink">{title}</h2>
      )}
      {children}
    </section>
  )
}