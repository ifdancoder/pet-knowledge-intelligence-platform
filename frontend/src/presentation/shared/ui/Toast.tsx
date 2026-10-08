import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'

type ToastKind = 'error' | 'info'

interface ToastMessage {
  id: number
  text: string
  kind: ToastKind
}

interface ToastContextValue {
  showToast: (text: string, kind?: ToastKind) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

let nextId = 0

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const showToast = useCallback((text: string, kind: ToastKind = 'info') => {
    const id = nextId++
    setToasts((current) => [...current, { id, text, kind }])
    setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id))
    }, 5000)
  }, [])

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-4 right-4 flex flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="alert"
            className={`rounded-lg border px-4 py-2 text-sm shadow-lg ${
              toast.kind === 'error'
                ? 'border-red-500/40 bg-red-500/10 text-red-200'
                : 'border-border bg-surface text-text-primary'
            }`}
          >
            {toast.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (context === null) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}
