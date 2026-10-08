import type { ButtonHTMLAttributes } from 'react'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary'
}

export function Button({ variant = 'primary', className = '', ...rest }: ButtonProps) {
  const base =
    'rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50'
  const variantClass =
    variant === 'primary'
      ? 'bg-accent text-background hover:bg-accent/90'
      : 'bg-surface text-text-primary border border-border hover:bg-surface/80'

  return <button className={`${base} ${variantClass} ${className}`} {...rest} />
}
