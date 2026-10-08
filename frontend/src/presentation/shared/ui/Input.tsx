import type { InputHTMLAttributes } from 'react'

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string
}

export function Input({ label, id, className = '', ...rest }: InputProps) {
  const inputId = id ?? label.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={inputId} className="text-sm text-text-secondary">
        {label}
      </label>
      <input
        id={inputId}
        className={`rounded-lg border border-border bg-surface px-3 py-2 text-text-primary outline-none transition-colors focus:border-accent ${className}`}
        {...rest}
      />
    </div>
  )
}
