import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ToastProvider, useToast } from './Toast'

function TestConsumer() {
  const { showToast } = useToast()
  return <button onClick={() => showToast('Something broke', 'error')}>Trigger</button>
}

describe('ToastProvider', () => {
  it('renders a toast when showToast is called', async () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Trigger' }))

    expect(await screen.findByText('Something broke')).toBeInTheDocument()
  })
})
