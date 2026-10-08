import { apiRequest } from '../http/client'
import type { SearchResult } from '../../domain/search/types'

interface SearchResultDto {
  chunk_id: string
  source_id: string
  text: string
  score: number
}

export async function search(workspaceId: string, query: string): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q: query })
  const dtos = await apiRequest<SearchResultDto[]>(
    `/api/v1/workspaces/${workspaceId}/search?${params.toString()}`,
  )
  return dtos.map((dto) => ({
    chunkId: dto.chunk_id,
    sourceId: dto.source_id,
    text: dto.text,
    score: dto.score,
  }))
}
