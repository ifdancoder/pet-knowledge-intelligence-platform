import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as conversationsApi from '../../infrastructure/conversations/api'

function conversationsKey(workspaceId: string) {
  return ['workspaces', workspaceId, 'conversations'] as const
}

export function useConversations(workspaceId: string) {
  return useQuery({
    queryKey: conversationsKey(workspaceId),
    queryFn: () => conversationsApi.listConversations(workspaceId),
  })
}

export function useCreateConversation(workspaceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => conversationsApi.createConversation(workspaceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: conversationsKey(workspaceId) })
    },
  })
}

export function useMessages(workspaceId: string, conversationId: string) {
  return useQuery({
    queryKey: ['workspaces', workspaceId, 'conversations', conversationId, 'messages'],
    queryFn: () => conversationsApi.getMessages(workspaceId, conversationId),
    enabled: conversationId.length > 0,
  })
}
