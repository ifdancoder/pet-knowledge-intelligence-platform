import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryProvider } from '../app/QueryProvider'
import { ToastProvider } from '../shared/ui/Toast'
import { RegisterPage } from './RegisterPage'
import * as authApi from '../../infrastructure/auth/api'

function renderRegisterPage() {
  return render(
    <MemoryRouter>
      <QueryProvider>
        <ToastProvider>
          <RegisterPage />
        </ToastProvider>
      </QueryProvider>
    </MemoryRouter>,
  )
}

describe('RegisterPage', () => {
  it('registers, then shows a verification token form', async () => {
    vi.spyOn(authApi, 'register').mockResolvedValue('user-1')
    renderRegisterPage()

    await userEvent.type(screen.getByLabelText('Email'), 'a@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'longenoughpassword')
    await userEvent.click(screen.getByRole('button', { name: 'Register' }))

    expect(await screen.findByLabelText('Verification token')).toBeInTheDocument()
  })

  it('verifies the email and links to login', async () => {
    vi.spyOn(authApi, 'register').mockResolvedValue('user-1')
    const verifySpy = vi.spyOn(authApi, 'verifyEmail').mockResolvedValue(undefined)
    renderRegisterPage()

    await userEvent.type(screen.getByLabelText('Email'), 'a@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'longenoughpassword')
    await userEvent.click(screen.getByRole('button', { name: 'Register' }))

    await userEvent.type(await screen.findByLabelText('Verification token'), 'token-123')
    await userEvent.click(screen.getByRole('button', { name: 'Verify' }))

    await vi.waitFor(() => expect(verifySpy).toHaveBeenCalledWith('token-123'))
    expect(await screen.findByRole('link', { name: 'Log in' })).toBeInTheDocument()
  })
})
