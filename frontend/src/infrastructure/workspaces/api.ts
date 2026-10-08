import { apiRequest } from '../http/client'
import type { Workspace } from '../../domain/workspaces/types'

interface WorkspaceDto {
  id: string
  name: string
  slug: string
}

function toWorkspace(dto: WorkspaceDto): Workspace {
  return { id: dto.id, name: dto.name, slug: dto.slug }
}

export async function listWorkspaces(): Promise<Workspace[]> {
  const dtos = await apiRequest<WorkspaceDto[]>('/api/v1/workspaces')
  return dtos.map(toWorkspace)
}

export async function createWorkspace(name: string): Promise<Workspace> {
  const dto = await apiRequest<WorkspaceDto>('/api/v1/workspaces', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
  return toWorkspace(dto)
}
