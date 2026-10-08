import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useCreateWorkspace, useWorkspaces } from '../../application/workspaces/useWorkspaces'
import { Button } from '../shared/ui/Button'
import { Card } from '../shared/ui/Card'
import { Input } from '../shared/ui/Input'
import { Spinner } from '../shared/ui/Spinner'

export function WorkspacePickerPage() {
  const [name, setName] = useState('')
  const workspaces = useWorkspaces()
  const createWorkspace = useCreateWorkspace()

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    await createWorkspace.mutateAsync(name)
    setName('')
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 p-6">
      <h1 className="text-xl font-semibold text-text-primary">Your workspaces</h1>

      {workspaces.isLoading && <Spinner label="Loading workspaces" />}

      {workspaces.isSuccess && (
        <ul className="flex flex-col gap-2">
          {workspaces.data.map((workspace) => (
            <li key={workspace.id}>
              <Link
                to={`/w/${workspace.id}`}
                className="block rounded-lg border border-border bg-surface px-4 py-3 text-text-primary hover:border-accent"
              >
                {workspace.name}
              </Link>
            </li>
          ))}
        </ul>
      )}

      <Card>
        <form onSubmit={handleCreate} className="flex items-end gap-3">
          <div className="flex-1">
            <Input label="Workspace name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <Button type="submit" disabled={createWorkspace.isPending}>
            Create workspace
          </Button>
        </form>
      </Card>
    </div>
  )
}
