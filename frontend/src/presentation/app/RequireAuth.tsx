import { useEffect, useState } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { refreshSession } from '../../infrastructure/http/client'
import { getAccessToken } from '../../infrastructure/http/tokenStore'
import { Spinner } from '../shared/ui/Spinner'

type Status = 'checking' | 'authenticated' | 'unauthenticated'

export function RequireAuth() {
  const [status, setStatus] = useState<Status>(getAccessToken() ? 'authenticated' : 'checking')

  useEffect(() => {
    if (status !== 'checking') {
      return
    }
    refreshSession().then((ok) => setStatus(ok ? 'authenticated' : 'unauthenticated'))
  }, [status])

  if (status === 'checking') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Spinner label="Checking session" />
      </div>
    )
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
