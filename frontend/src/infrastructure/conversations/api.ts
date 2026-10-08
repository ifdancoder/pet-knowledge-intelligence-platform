import { apiRequest } from '../http/client'
import type { Conversation, Message } from '../../domain/conversations/types'

interface ConversationDto {
  id: string
}

interface MessageDto {
  id: string
  role: string
  content: string
  source_chunk_ids: string[]
}

function toMessage(dto: MessageDto): Message {
  return {
    id: dto.id,
    role: dto.role === 'assistant' ? 'assistant' : 'user',
    content: dto.content,
    sourceChunkIds: dto.source_chunk_ids,
  }
}

export async function listConversations(workspaceId: string): Promise<Conversation[]> {
  const dtos = await apiRequest<ConversationDto[]>(`/api/v1/workspaces/${workspaceId}/conversations`)
  return dtos.map((dto) => ({ id: dto.id }))
}

export async function createConversation(workspaceId: string): Promise<Conversation> {
  const dto = await apiRequest<ConversationDto>(`/api/v1/workspaces/${workspaceId}/conversations`, {
    method: 'POST',
  })
  return { id: dto.id }
}

export async function getMessages(workspaceId: string, conversationId: string): Promise<Message[]> {
  const dtos = await apiRequest<MessageDto[]>(
    `/api/v1/workspaces/${workspaceId}/conversations/${conversationId}/messages`,
  )
  return dtos.map(toMessage)
}
