import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as workspacesApi from '../../infrastructure/workspaces/api'

const WORKSPACES_KEY = ['workspaces'] as const

export function useWorkspaces() {
  return useQuery({
    queryKey: WORKSPACES_KEY,
    queryFn: workspacesApi.listWorkspaces,
  })
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => workspacesApi.createWorkspace(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WORKSPACES_KEY })
    },
  })
}
