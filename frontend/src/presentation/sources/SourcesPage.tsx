import { useRef } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useSources, useSourceStatus, useUploadSource } from '../../application/sources/useSources'
import { Card } from '../shared/ui/Card'
import { Spinner } from '../shared/ui/Spinner'
import { useToast } from '../shared/ui/Toast'
import type { Source } from '../../domain/sources/types'

function SourceRow({ workspaceId, source }: { workspaceId: string; source: Source }) {
  const liveStatus = useSourceStatus(workspaceId, source.sourceId)
  const current = liveStatus.data ?? source

  return (
    <li className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3">
      <span className="text-text-primary">{current.sourceId}</span>
      <span className="text-sm text-text-secondary">{current.status}</span>
    </li>
  )
}

export function SourcesPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  if (!workspaceId) {
    throw new Error('SourcesPage must be rendered under a /w/:workspaceId route')
  }
  const sources = useSources(workspaceId)
  const uploadSource = useUploadSource(workspaceId)
  const { showToast } = useToast()
  const fileInputRef = useRef<HTMLInputElement>(null)

  async function handleFileChange() {
    const file = fileInputRef.current?.files?.[0]
    if (!file) {
      return
    }
    try {
      await uploadSource.mutateAsync(file)
    } catch {
      showToast('Upload failed, please try again', 'error')
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-primary">Sources</h1>
        <div className="flex gap-4 text-sm text-accent">
          <Link to={`/w/${workspaceId}/search`}>Search</Link>
          <Link to={`/w/${workspaceId}/chat`}>Chat</Link>
        </div>
      </div>

      <Card>
        <label htmlFor="source-upload" className="mb-2 block text-sm text-text-secondary">
          Upload a document
        </label>
        <input
          id="source-upload"
          ref={fileInputRef}
          type="file"
          accept=".pdf,.md,.markdown"
          onChange={handleFileChange}
          className="text-sm text-text-primary"
        />
      </Card>

      {sources.isLoading && <Spinner label="Loading sources" />}

      {sources.isSuccess && (
        <ul className="flex flex-col gap-2">
          {sources.data.map((source) => (
            <SourceRow key={source.sourceId} workspaceId={workspaceId} source={source} />
          ))}
        </ul>
      )}
    </div>
  )
}
