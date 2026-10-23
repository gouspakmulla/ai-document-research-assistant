import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/apiClient'
import { CollectionItem } from '@/types'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { formatDate } from '@/lib/utils'
import {
  FolderKanban,
  Plus,
  Files,
  Sparkles,
  Trash2,
} from 'lucide-react'

export function CollectionsPage() {
  const [createOpen, setCreateOpen] = useState(false)
  const [newColName, setNewColName] = useState('')
  const [newColDesc, setNewColDesc] = useState('')
  const [deleteCol, setDeleteCol] = useState<CollectionItem | null>(null)

  const queryClient = useQueryClient()

  const { data: collections, isLoading } = useQuery({
    queryKey: ['collections'],
    queryFn: () => api.getCollections(),
  })

  const createMutation = useMutation({
    mutationFn: () => api.createCollection(newColName.trim(), newColDesc.trim()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collections'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      setCreateOpen(false)
      setNewColName('')
      setNewColDesc('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteCollection(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collections'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      setDeleteCol(null)
    },
  })

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newColName.trim()) return
    createMutation.mutate()
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-gray-200 dark:border-gray-800">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Research Collections
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Group related documents into topical subjects to perform targeted multi-document RAG queries
          </p>
        </div>
        <Button
          onClick={() => setCreateOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
        >
          <Plus className="mr-1.5 h-4 w-4" />
          Create Collection
        </Button>
      </div>

      {/* Grid of Collections */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Skeleton className="h-48 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
        </div>
      ) : !collections || collections.length === 0 ? (
        <div className="p-16 text-center space-y-4 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl">
          <div className="mx-auto w-12 h-12 rounded-full bg-blue-50 dark:bg-blue-950/40 flex items-center justify-center text-blue-600">
            <FolderKanban className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-foreground">No collections created yet</h3>
            <p className="text-xs text-gray-500 mt-1">
              Create collections to organize your documents by topic or research thesis.
            </p>
          </div>
          <Button onClick={() => setCreateOpen(true)} className="bg-blue-600 text-white">
            <Plus className="mr-1.5 h-4 w-4" />
            Create First Collection
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {collections.map((col) => (
            <Card key={col.id} className="flex flex-col justify-between hover:border-blue-400 dark:hover:border-blue-600 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="h-10 w-10 rounded-xl bg-blue-100 dark:bg-blue-950/50 text-blue-600 flex items-center justify-center mb-2">
                    <FolderKanban className="h-5 w-5" />
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setDeleteCol(col)}
                    className="h-8 w-8 text-gray-400 hover:text-red-600"
                    title="Delete collection"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                <CardTitle className="text-base font-bold text-foreground">
                  {col.name}
                </CardTitle>
                <CardDescription className="line-clamp-2 text-xs text-gray-500">
                  {col.description || 'No description provided.'}
                </CardDescription>
              </CardHeader>

              <CardContent className="pt-0 pb-4">
                <div className="flex items-center space-x-2 text-xs text-gray-500 font-medium">
                  <Files className="h-3.5 w-3.5 text-blue-500" />
                  <span>{col.document_count} Documents indexed</span>
                </div>
              </CardContent>

              <CardFooter className="pt-3 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between text-xs">
                <span className="text-[11px] text-gray-400">
                  Updated {formatDate(col.updated_at)}
                </span>
                <Link to={`/workspace?col=${col.id}`}>
                  <Button size="sm" variant="ghost" className="h-8 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-950/40">
                    <Sparkles className="mr-1 h-3.5 w-3.5" />
                    Query Collection
                  </Button>
                </Link>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      {/* Create Collection Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <form onSubmit={handleCreateSubmit}>
            <DialogHeader>
              <DialogTitle>Create Research Collection</DialogTitle>
              <DialogDescription>
                Group documents under a shared topic for targeted RAG retrieval.
              </DialogDescription>
            </DialogHeader>

            <div className="py-4 space-y-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-foreground">Collection Name</label>
                <Input
                  placeholder="e.g., Quantum Computing Benchmarks"
                  value={newColName}
                  onChange={(e) => setNewColName(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-foreground">Description (Optional)</label>
                <Input
                  placeholder="Scope and research objectives for this collection"
                  value={newColDesc}
                  onChange={(e) => setNewColDesc(e.target.value)}
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={!newColName.trim()}
                isLoading={createMutation.isPending}
                className="bg-blue-600 text-white"
              >
                Create Collection
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Collection Dialog */}
      <Dialog open={!!deleteCol} onOpenChange={(open) => !open && setDeleteCol(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Collection</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the collection <strong>{deleteCol?.name}</strong>? Documents in this collection will not be deleted from your personal library.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteCol(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteCol && deleteMutation.mutate(deleteCol.id)}
              isLoading={deleteMutation.isPending}
            >
              Confirm Deletion
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
