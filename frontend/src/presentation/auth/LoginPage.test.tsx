import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryProvider } from '../app/QueryProvider'
import { ToastProvider } from '../shared/ui/Toast'
import { LoginPage } from './LoginPage'
import * as authApi from '../../infrastructure/auth/api'

function renderLoginPage() {
  return render(
    <MemoryRouter>
      <QueryProvider>
        <ToastProvider>
          <LoginPage />
        </ToastProvider>
      </QueryProvider>
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  it('submits email and password to the login API', async () => {
    const loginSpy = vi.spyOn(authApi, 'login').mockResolvedValue(undefined)
    renderLoginPage()

    await userEvent.type(screen.getByLabelText('Email'), 'a@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'longenoughpassword')
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }))

    await vi.waitFor(() => expect(loginSpy).toHaveBeenCalledWith('a@example.com', 'longenoughpassword'))
  })

  it('shows an inline error message when login fails', async () => {
    const { ApiError } = await import('../../infrastructure/http/client')
    vi.spyOn(authApi, 'login').mockRejectedValue(new ApiError(401, 'invalid_credentials', 'Wrong password'))
    renderLoginPage()

    await userEvent.type(screen.getByLabelText('Email'), 'a@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'wrongpassword')
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByText('Wrong password')).toBeInTheDocument()
  })
})
