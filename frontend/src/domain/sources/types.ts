export type SourceStatus =
  | 'queued'
  | 'extracting'
  | 'normalizing'
  | 'chunking'
  | 'embedding'
  | 'indexing'
  | 'indexed'
  | 'failed'

export interface Source {
  sourceId: string
  status: SourceStatus
  error: string | null
}

export function isTerminalStatus(status: SourceStatus): boolean {
  return status === 'indexed' || status === 'failed'
}
