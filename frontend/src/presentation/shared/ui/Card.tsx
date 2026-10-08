import type { ReactNode } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-border bg-surface p-6 shadow-lg shadow-black/20 ${className}`}>
      {children}
    </div>
  )
}
