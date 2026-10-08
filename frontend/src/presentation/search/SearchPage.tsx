import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useDebouncedValue } from '../../application/shared/useDebouncedValue'
import { useSearch } from '../../application/search/useSearch'
import { Card } from '../shared/ui/Card'
import { Input } from '../shared/ui/Input'
import { Spinner } from '../shared/ui/Spinner'

export function SearchPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  if (!workspaceId) {
    throw new Error('SearchPage must be rendered under a /w/:workspaceId route')
  }
  const [query, setQuery] = useState('')
  const debouncedQuery = useDebouncedValue(query, 300)
  const results = useSearch(workspaceId, debouncedQuery)

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 p-6">
      <h1 className="text-xl font-semibold text-text-primary">Search</h1>
      <Input label="Search" value={query} onChange={(e) => setQuery(e.target.value)} />

      {results.isLoading && <Spinner label="Searching" />}

      {results.isSuccess && (
        <ul className="flex flex-col gap-3">
          {results.data.map((result) => (
            <Card key={result.chunkId}>
              <p className="text-text-primary">{result.text}</p>
              <p className="mt-2 text-xs text-text-secondary">
                source {result.sourceId} · score {result.score.toFixed(3)}
              </p>
            </Card>
          ))}
        </ul>
      )}
    </div>
  )
}
