import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { QueryProvider } from './QueryProvider'
import { RequireAuth } from './RequireAuth'
import { LoginPage } from '../auth/LoginPage'
import { RegisterPage } from '../auth/RegisterPage'
import { WorkspacePickerPage } from '../workspaces/WorkspacePickerPage'
import { SourcesPage } from '../sources/SourcesPage'
import { ToastProvider } from '../shared/ui/Toast'

function SessionExpiryListener() {
  const navigate = useNavigate()
  useEffect(() => {
    const handler = () => navigate('/login', { replace: true })
    window.addEventListener('kip:session-expired', handler)
    return () => window.removeEventListener('kip:session-expired', handler)
  }, [navigate])
  return null
}

export function App() {
  return (
    <QueryProvider>
      <ToastProvider>
        <BrowserRouter>
          <SessionExpiryListener />
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route element={<RequireAuth />}>
              <Route path="/" element={<Navigate to="/workspaces" replace />} />
              <Route path="/workspaces" element={<WorkspacePickerPage />} />
              <Route path="/w/:workspaceId" element={<SourcesPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryProvider>
  )
}
