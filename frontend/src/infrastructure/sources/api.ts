import { apiRequest } from '../http/client'
import type { Source } from '../../domain/sources/types'

interface SourceDto {
  source_id: string
  status: Source['status']
  error: string | null
}

function toSource(dto: SourceDto): Source {
  return { sourceId: dto.source_id, status: dto.status, error: dto.error }
}

export async function listSources(workspaceId: string): Promise<Source[]> {
  const dtos = await apiRequest<SourceDto[]>(`/api/v1/workspaces/${workspaceId}/sources`)
  return dtos.map(toSource)
}

export async function getSourceStatus(workspaceId: string, sourceId: string): Promise<Source> {
  const dto = await apiRequest<SourceDto>(`/api/v1/workspaces/${workspaceId}/sources/${sourceId}`)
  return toSource(dto)
}

export async function uploadSource(workspaceId: string, file: File): Promise<Source> {
  const formData = new FormData()
  formData.append('file', file)
  const dto = await apiRequest<SourceDto>(`/api/v1/workspaces/${workspaceId}/sources`, {
    method: 'POST',
    body: formData,
    headers: {},
  })
  return toSource(dto)
}
