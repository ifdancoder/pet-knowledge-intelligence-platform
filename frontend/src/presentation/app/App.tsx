import { ToastProvider } from '../shared/ui/Toast'

export function App() {
  return (
    <ToastProvider>
      <div className="flex min-h-screen items-center justify-center bg-background text-text-primary">
        <h1 className="text-xl font-semibold">Knowledge Intelligence Platform</h1>
      </div>
    </ToastProvider>
  )
}
