import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useLogin } from '../../application/auth/useAuth'
import { ApiError } from '../../infrastructure/http/client'
import { Button } from '../shared/ui/Button'
import { Card } from '../shared/ui/Card'
import { Input } from '../shared/ui/Input'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const login = useLogin()
  const navigate = useNavigate()

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await login.mutateAsync({ email, password })
      navigate('/workspaces')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <h1 className="mb-6 text-lg font-semibold text-text-primary">Log in</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <p className="text-sm text-red-400">{error}</p>}
          <Button type="submit" disabled={login.isPending}>
            Log in
          </Button>
        </form>
        <p className="mt-4 text-sm text-text-secondary">
          No account yet? <Link to="/register" className="text-accent">Register</Link>
        </p>
      </Card>
    </div>
  )
}
