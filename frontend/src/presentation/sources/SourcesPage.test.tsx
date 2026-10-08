import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryProvider } from '../app/QueryProvider'
import { ToastProvider } from '../shared/ui/Toast'
import { SourcesPage } from './SourcesPage'
import * as sourcesApi from '../../infrastructure/sources/api'

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/w/w1']}>
      <QueryProvider>
        <ToastProvider>
          <Routes>
            <Route path="/w/:workspaceId" element={<SourcesPage />} />
          </Routes>
        </ToastProvider>
      </QueryProvider>
    </MemoryRouter>,
  )
}

describe('SourcesPage', () => {
  it('lists sources with their status', async () => {
    vi.spyOn(sourcesApi, 'listSources').mockResolvedValue([
      { sourceId: 's1', status: 'indexed', error: null },
    ])
    vi.spyOn(sourcesApi, 'getSourceStatus').mockResolvedValue({
      sourceId: 's1',
      status: 'indexed',
      error: null,
    })
    renderPage()

    expect(await screen.findByText('indexed')).toBeInTheDocument()
  })

  it('uploads a file and shows it in the list', async () => {
    vi.spyOn(sourcesApi, 'listSources')
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ sourceId: 's2', status: 'queued', error: null }])
    vi.spyOn(sourcesApi, 'uploadSource').mockResolvedValue({
      sourceId: 's2',
      status: 'queued',
      error: null,
    })
    vi.spyOn(sourcesApi, 'getSourceStatus').mockResolvedValue({
      sourceId: 's2',
      status: 'queued',
      error: null,
    })
    renderPage()

    const file = new File(['# hello'], 'notes.md', { type: 'text/markdown' })
    const input = await screen.findByLabelText('Upload a document')
    await userEvent.upload(input, file)

    expect(await screen.findByText('queued')).toBeInTheDocument()
    expect(sourcesApi.uploadSource).toHaveBeenCalledWith('w1', file)
  })
})
