import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryProvider } from '../app/QueryProvider'
import { ChatPage } from './ChatPage'
import * as conversationsApi from '../../infrastructure/conversations/api'
import * as sseClient from '../../infrastructure/conversations/sseClient'

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/w/w1/chat']}>
      <QueryProvider>
        <Routes>
          <Route path="/w/:workspaceId/chat" element={<ChatPage />} />
          <Route path="/w/:workspaceId/chat/:conversationId" element={<ChatPage />} />
        </Routes>
      </QueryProvider>
    </MemoryRouter>,
  )
}

describe('ChatPage', () => {
  it('creates a conversation when there are none, then sends a message and streams the reply', async () => {
    vi.spyOn(conversationsApi, 'listConversations').mockResolvedValue([])
    vi.spyOn(conversationsApi, 'createConversation').mockResolvedValue({ id: 'c1' })
    vi.spyOn(conversationsApi, 'getMessages').mockResolvedValue([])
    vi.spyOn(sseClient, 'streamAssistantReply').mockImplementation(
      async (_workspaceId, _conversationId, _content, onEvent) => {
        onEvent({ type: 'delta', delta: 'Hi there' })
        onEvent({ type: 'done', messageId: 'm1' })
      },
    )

    renderPage()

    const input = await screen.findByLabelText('Message')
    await vi.waitFor(() => expect(input).not.toBeDisabled())
    await userEvent.type(input, 'hello')
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText('hello')).toBeInTheDocument()
    expect(await screen.findByText('Hi there')).toBeInTheDocument()
  })
})
