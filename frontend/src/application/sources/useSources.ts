import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as sourcesApi from '../../infrastructure/sources/api'
import { isTerminalStatus } from '../../domain/sources/types'

function sourcesKey(workspaceId: string) {
  return ['workspaces', workspaceId, 'sources'] as const
}

export function useSources(workspaceId: string) {
  return useQuery({
    queryKey: sourcesKey(workspaceId),
    queryFn: () => sourcesApi.listSources(workspaceId),
  })
}

export function useUploadSource(workspaceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => sourcesApi.uploadSource(workspaceId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sourcesKey(workspaceId) })
    },
  })
}

export function useSourceStatus(workspaceId: string, sourceId: string) {
  return useQuery({
    queryKey: ['workspaces', workspaceId, 'sources', sourceId],
    queryFn: () => sourcesApi.getSourceStatus(workspaceId, sourceId),
    refetchInterval: (query) => {
      const data = query.state.data
      if (data === undefined || isTerminalStatus(data.status)) {
        return false
      }
      return 2000
    },
  })
}
