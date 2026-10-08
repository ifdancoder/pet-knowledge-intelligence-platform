import { getAccessToken } from '../http/tokenStore'

const BASE_URL = import.meta.env.VITE_API_URL

export type StreamEvent =
  | { type: 'delta'; delta: string }
  | { type: 'done'; messageId: string }
  | { type: 'error'; message: string }

interface StreamPayload {
  delta?: string
  done?: boolean
  message_id?: string
  error?: string
}

export async function streamAssistantReply(
  workspaceId: string,
  conversationId: string,
  content: string,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const response = await fetch(
    `${BASE_URL}/api/v1/workspaces/${workspaceId}/conversations/${conversationId}/messages`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getAccessToken() ?? ''}`,
      },
      body: JSON.stringify({ content }),
    },
  )

  if (!response.ok || !response.body) {
    onEvent({ type: 'error', message: `Request failed with status ${response.status}` })
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }
    buffer += decoder.decode(value, { stream: true })

    let separatorIndex = buffer.indexOf('\n\n')
    while (separatorIndex !== -1) {
      const rawEvent = buffer.slice(0, separatorIndex)
      buffer = buffer.slice(separatorIndex + 2)
      const payloadText = rawEvent.replace(/^data: /, '').trim()

      if (payloadText.length > 0) {
        const payload = JSON.parse(payloadText) as StreamPayload
        if (payload.error !== undefined) {
          onEvent({ type: 'error', message: payload.error })
        } else if (payload.done === true) {
          onEvent({ type: 'done', messageId: payload.message_id ?? '' })
        } else if (payload.delta !== undefined) {
          onEvent({ type: 'delta', delta: payload.delta })
        }
      }

      separatorIndex = buffer.indexOf('\n\n')
    }
  }
}
