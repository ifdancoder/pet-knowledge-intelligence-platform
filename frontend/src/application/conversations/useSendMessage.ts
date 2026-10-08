import { useCallback, useState } from 'react'
import { streamAssistantReply } from '../../infrastructure/conversations/sseClient'
import type { Message } from '../../domain/conversations/types'

export function useSendMessage(
  workspaceId: string,
  conversationId: string,
  onMessageFinalized: (message: Message) => void,
) {
  const [pendingContent, setPendingContent] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamError, setStreamError] = useState<string | null>(null)

  const send = useCallback(
    async (content: string) => {
      setIsStreaming(true)
      setStreamError(null)
      setPendingContent('')
      let accumulated = ''

      await streamAssistantReply(workspaceId, conversationId, content, (event) => {
        if (event.type === 'delta') {
          accumulated += event.delta
          setPendingContent(accumulated)
        } else if (event.type === 'error') {
          setStreamError(event.message)
        } else if (event.type === 'done') {
          onMessageFinalized({
            id: event.messageId,
            role: 'assistant',
            content: accumulated,
            sourceChunkIds: [],
          })
          setPendingContent('')
        }
      })

      setIsStreaming(false)
    },
    [workspaceId, conversationId, onMessageFinalized],
  )

  return { send, pendingContent, isStreaming, streamError }
}
