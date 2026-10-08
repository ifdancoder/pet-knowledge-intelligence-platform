import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryProvider } from '../app/QueryProvider'
import { ToastProvider } from '../shared/ui/Toast'
import { WorkspacePickerPage } from './WorkspacePickerPage'
import * as workspacesApi from '../../infrastructure/workspaces/api'

function renderPage() {
  return render(
    <MemoryRouter>
      <QueryProvider>
        <ToastProvider>
          <WorkspacePickerPage />
        </ToastProvider>
      </QueryProvider>
    </MemoryRouter>,
  )
}

describe('WorkspacePickerPage', () => {
  it('lists the workspaces as links', async () => {
    vi.spyOn(workspacesApi, 'listWorkspaces').mockResolvedValue([
      { id: 'w1', name: 'Acme', slug: 'acme' },
    ])
    renderPage()

    expect(await screen.findByRole('link', { name: 'Acme' })).toHaveAttribute('href', '/w/w1')
  })

  it('creates a new workspace from the form', async () => {
    vi.spyOn(workspacesApi, 'listWorkspaces').mockResolvedValue([])
    const createSpy = vi
      .spyOn(workspacesApi, 'createWorkspace')
      .mockResolvedValue({ id: 'w2', name: 'Beta', slug: 'beta' })
    renderPage()

    await userEvent.type(await screen.findByLabelText('Workspace name'), 'Beta')
    await userEvent.click(screen.getByRole('button', { name: 'Create workspace' }))

    await vi.waitFor(() => expect(createSpy).toHaveBeenCalledWith('Beta'))
  })
})
