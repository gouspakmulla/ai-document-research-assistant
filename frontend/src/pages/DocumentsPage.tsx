import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/apiClient'
import { DocumentItem } from '@/types'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { StatusBadge } from '@/components/ui/status-badge'
import { Skeleton } from '@/components/ui/skeleton'
import { UploadModal } from '@/features/documents/UploadModal'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { formatBytes, formatDate } from '@/lib/utils'
import {
  Files,
  Search,
  Upload,
  ExternalLink,
  Trash2,
  Edit2,
  FileText,
  Sparkles,
} from 'lucide-react'

export function DocumentsPage() {
  const [search, setSearch] = useState('')
  const [uploadOpen, setUploadOpen] = useState(false)
  const [deleteDoc, setDeleteDoc] = useState<DocumentItem | null>(null)
  const [renameDoc, setRenameDoc] = useState<DocumentItem | null>(null)
  const [newFilename, setNewFilename] = useState('')

  const queryClient = useQueryClient()

  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents', search],
    queryFn: () => api.getDocuments(search),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      setDeleteDoc(null)
    },
  })

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => api.renameDocument(id, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      setRenameDoc(null)
    },
  })

  const handleStartRename = (doc: DocumentItem) => {
    setRenameDoc(doc)
    setNewFilename(doc.filename)
  }

  const handleConfirmRename = () => {
    if (!renameDoc || !newFilename.trim()) return
    renameMutation.mutate({ id: renameDoc.id, name: newFilename.trim() })
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header & Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-gray-200 dark:border-gray-800">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Document Library
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Manage uploaded PDFs, inspect chunking status, and verify extracted pages
          </p>
        </div>
        <Button
          onClick={() => setUploadOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
        >
          <Upload className="mr-1.5 h-4 w-4" />
          Upload Document
        </Button>
      </div>

      {/* Filter Toolbar */}
      <div className="flex items-center space-x-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search documents by name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Documents Table / List */}
      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="p-6 space-y-4">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        ) : !documents || documents.length === 0 ? (
          <div className="p-12 text-center space-y-4">
            <div className="mx-auto w-12 h-12 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-400">
              <Files className="h-6 w-6" />
            </div>
            <div>
              <p className="text-base font-semibold text-foreground">No documents found</p>
              <p className="text-xs text-gray-500 mt-1">
                {search ? 'No documents match your query.' : 'Upload a PDF to begin grounded research.'}
              </p>
            </div>
            {!search && (
              <Button onClick={() => setUploadOpen(true)} className="bg-blue-600 text-white">
                <Upload className="mr-1.5 h-4 w-4" />
                Upload PDF
              </Button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200 dark:border-gray-800 text-xs font-semibold text-gray-500 dark:text-gray-400">
                <tr>
                  <th className="py-3 px-4">Document</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Pages</th>
                  <th className="py-3 px-4">Size</th>
                  <th className="py-3 px-4">Uploaded</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-3 max-w-sm sm:max-w-md">
                        <div className="h-9 w-9 rounded-lg bg-red-100 dark:bg-red-950/40 text-red-600 flex items-center justify-center shrink-0">
                          <FileText className="h-4 w-4" />
                        </div>
                        <div className="overflow-hidden">
                          <Link
                            to={`/documents/${doc.id}`}
                            className="font-medium text-foreground hover:text-blue-600 truncate block"
                          >
                            {doc.filename}
                          </Link>
                          {doc.error_message && (
                            <p className="text-[11px] text-red-500 truncate max-w-xs" title={doc.error_message}>
                              {doc.error_message}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={doc.processing_status} />
                    </td>
                    <td className="py-3 px-4 text-xs font-mono text-gray-600 dark:text-gray-300">
                      {doc.page_count > 0 ? `${doc.page_count} pages` : '—'}
                    </td>
                    <td className="py-3 px-4 text-xs text-gray-500">
                      {formatBytes(doc.file_size_bytes)}
                    </td>
                    <td className="py-3 px-4 text-xs text-gray-500">
                      {formatDate(doc.created_at)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end space-x-1">
                        <Link to={`/documents/${doc.id}`}>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-500 hover:text-blue-600" title="Open in PDF Viewer">
                            <ExternalLink className="h-4 w-4" />
                          </Button>
                        </Link>
                        <Link to={`/workspace?doc=${doc.id}`}>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-500 hover:text-indigo-600" title="Query in Workspace">
                            <Sparkles className="h-4 w-4" />
                          </Button>
                        </Link>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleStartRename(doc)}
                          className="h-8 w-8 text-gray-500 hover:text-foreground"
                          title="Rename"
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setDeleteDoc(doc)}
                          className="h-8 w-8 text-gray-500 hover:text-red-600"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteDoc} onOpenChange={(open) => !open && setDeleteDoc(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Document</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{deleteDoc?.filename}</strong>? This action will permanently remove the original PDF file, all extracted text chunks, embeddings, and associated citations.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDoc(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteDoc && deleteMutation.mutate(deleteDoc.id)}
              isLoading={deleteMutation.isPending}
            >
              Confirm Deletion
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Rename Dialog */}
      <Dialog open={!!renameDoc} onOpenChange={(open) => !open && setRenameDoc(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename Document</DialogTitle>
            <DialogDescription>
              Update the user-facing title for this document.
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <Input
              value={newFilename}
              onChange={(e) => setNewFilename(e.target.value)}
              placeholder="document_name.pdf"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameDoc(null)}>
              Cancel
            </Button>
            <Button
              onClick={handleConfirmRename}
              isLoading={renameMutation.isPending}
              className="bg-blue-600 text-white"
            >
              Save Name
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <UploadModal isOpen={uploadOpen} onClose={() => setUploadOpen(false)} />
    </div>
  )
}
