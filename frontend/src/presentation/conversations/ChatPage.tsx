import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  useConversations,
  useCreateConversation,
  useMessages,
} from '../../application/conversations/useConversations'
import { useSendMessage } from '../../application/conversations/useSendMessage'
import type { Message } from '../../domain/conversations/types'
import { Button } from '../shared/ui/Button'
import { Input } from '../shared/ui/Input'
import { Spinner } from '../shared/ui/Spinner'
import { ConversationList } from './ConversationList'

export function ChatPage() {
  const { workspaceId, conversationId } = useParams<{ workspaceId: string; conversationId?: string }>()
  if (!workspaceId) {
    throw new Error('ChatPage must be rendered under a /w/:workspaceId route')
  }
  const navigate = useNavigate()
  const conversations = useConversations(workspaceId)
  const createConversation = useCreateConversation(workspaceId)
  const [draft, setDraft] = useState('')
  const [localMessages, setLocalMessages] = useState<Message[]>([])

  useEffect(() => {
    if (!conversationId && conversations.isSuccess && conversations.data.length === 0) {
      createConversation.mutate(undefined, {
        onSuccess: (conversation) => navigate(`/w/${workspaceId}/chat/${conversation.id}`, { replace: true }),
      })
    } else if (!conversationId && conversations.isSuccess && conversations.data.length > 0) {
      navigate(`/w/${workspaceId}/chat/${conversations.data[0].id}`, { replace: true })
    }
  }, [conversationId, conversations.isSuccess, conversations.data, workspaceId, navigate, createConversation])

  const history = useMessages(workspaceId, conversationId ?? '')

  useEffect(() => {
    if (history.isSuccess) {
      setLocalMessages(history.data)
    }
  }, [history.isSuccess, history.data])

  const { send, pendingContent, isStreaming, streamError } = useSendMessage(
    workspaceId,
    conversationId ?? '',
    (finalMessage) => setLocalMessages((current) => [...current, finalMessage]),
  )

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!draft.trim() || !conversationId) {
      return
    }
    const content = draft
    setDraft('')
    setLocalMessages((current) => [
      ...current,
      { id: `local-${Date.now()}`, role: 'user', content, sourceChunkIds: [] },
    ])
    await send(content)
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-4xl gap-6 p-6">
      <aside className="w-48 shrink-0">
        <ConversationList
          conversations={conversations.data ?? []}
          activeConversationId={conversationId ?? null}
          onSelect={(id) => navigate(`/w/${workspaceId}/chat/${id}`)}
        />
      </aside>

      <div className="flex flex-1 flex-col gap-4">
        {!conversationId && <Spinner label="Starting conversation" />}

        <div className="flex flex-1 flex-col gap-3 overflow-y-auto">
          {localMessages.map((message) => (
            <div
              key={message.id}
              className={`max-w-lg rounded-lg px-4 py-2 ${
                message.role === 'user'
                  ? 'self-end bg-accent text-background'
                  : 'self-start bg-surface text-text-primary'
              }`}
            >
              {message.content}
            </div>
          ))}
          {isStreaming && pendingContent.length > 0 && (
            <div className="max-w-lg self-start rounded-lg bg-surface px-4 py-2 text-text-primary">
              {pendingContent}
            </div>
          )}
          {streamError && <p className="text-sm text-red-400">{streamError}</p>}
        </div>

        <form onSubmit={handleSubmit} className="flex gap-3">
          <div className="flex-1">
            <Input
              label="Message"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              disabled={!conversationId || isStreaming}
            />
          </div>
          <Button type="submit" disabled={!conversationId || isStreaming}>
            Send
          </Button>
        </form>
      </div>
    </div>
  )
}
