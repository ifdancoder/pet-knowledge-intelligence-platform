import { useQuery } from '@tanstack/react-query'
import * as searchApi from '../../infrastructure/search/api'

export function useSearch(workspaceId: string, query: string) {
  return useQuery({
    queryKey: ['workspaces', workspaceId, 'search', query],
    queryFn: () => searchApi.search(workspaceId, query),
    enabled: query.trim().length > 0,
  })
}
