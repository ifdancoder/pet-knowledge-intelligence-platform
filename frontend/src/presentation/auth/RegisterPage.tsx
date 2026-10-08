import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useRegister, useVerifyEmail } from '../../application/auth/useAuth'
import { ApiError } from '../../infrastructure/http/client'
import { Button } from '../shared/ui/Button'
import { Card } from '../shared/ui/Card'
import { Input } from '../shared/ui/Input'

export function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [token, setToken] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [verified, setVerified] = useState(false)
  const register = useRegister()
  const verifyEmail = useVerifyEmail()

  async function handleRegister(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await register.mutateAsync({ email, password })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    }
  }

  async function handleVerify(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await verifyEmail.mutateAsync(token)
      setVerified(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    }
  }

  if (verified) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-sm">
          <p className="text-text-primary">Email verified.</p>
          <Link to="/login" className="mt-4 inline-block text-accent">
            Log in
          </Link>
        </Card>
      </div>
    )
  }

  if (register.isSuccess) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-sm">
          <h1 className="mb-2 text-lg font-semibold text-text-primary">Verify your email</h1>
          <p className="mb-4 text-sm text-text-secondary">
            In development the verification token is printed to the API server logs. Paste it below.
          </p>
          <form onSubmit={handleVerify} className="flex flex-col gap-4">
            <Input
              label="Verification token"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              required
            />
            {error && <p className="text-sm text-red-400">{error}</p>}
            <Button type="submit" disabled={verifyEmail.isPending}>
              Verify
            </Button>
          </form>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <h1 className="mb-6 text-lg font-semibold text-text-primary">Register</h1>
        <form onSubmit={handleRegister} className="flex flex-col gap-4">
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
            minLength={8}
            required
          />
          {error && <p className="text-sm text-red-400">{error}</p>}
          <Button type="submit" disabled={register.isPending}>
            Register
          </Button>
        </form>
        <p className="mt-4 text-sm text-text-secondary">
          Already have an account? <Link to="/login" className="text-accent">Log in</Link>
        </p>
      </Card>
    </div>
  )
}
