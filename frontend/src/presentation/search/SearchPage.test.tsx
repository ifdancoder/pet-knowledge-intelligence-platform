import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryProvider } from '../app/QueryProvider'
import { SearchPage } from './SearchPage'
import * as searchApi from '../../infrastructure/search/api'

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/w/w1/search']}>
      <QueryProvider>
        <Routes>
          <Route path="/w/:workspaceId/search" element={<SearchPage />} />
        </Routes>
      </QueryProvider>
    </MemoryRouter>,
  )
}

describe('SearchPage', () => {
  it('shows results after typing a query', async () => {
    vi.spyOn(searchApi, 'search').mockResolvedValue([
      { chunkId: 'c1', sourceId: 's1', text: 'hello world', score: 0.9 },
    ])
    renderPage()

    await userEvent.type(screen.getByLabelText('Search'), 'hello')

    expect(await screen.findByText('hello world')).toBeInTheDocument()
  })
})
