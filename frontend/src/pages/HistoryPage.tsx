import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/apiClient'
import { ConversationItem } from '@/types'
import { Card } from '@/components/ui/card'
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
  History,
  MessageSquare,
  Search,
  Trash2,
  ExternalLink,
  Plus,
  Sparkles,
} from 'lucide-react'

export function HistoryPage() {
  const [search, setSearch] = useState('')
  const [deleteConv, setDeleteConv] = useState<ConversationItem | null>(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: conversations, isLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => api.getConversations(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteConversation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      setDeleteConv(null)
    },
  })

  const filtered = conversations?.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase())
  )

  const handleStartNew = async () => {
    const conv = await api.createConversation('New Research Inquiry')
    queryClient.invalidateQueries({ queryKey: ['conversations'] })
    navigate(`/workspace?conv=${conv.id}`)
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-gray-200 dark:border-gray-800">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Conversation History
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Browse and resume previous research inquiries and citation audits
          </p>
        </div>
        <Button
          onClick={handleStartNew}
          className="bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
        >
          <Plus className="mr-1.5 h-4 w-4" />
          New Research Chat
        </Button>
      </div>

      {/* Search Toolbar */}
      <div className="flex items-center space-x-3 max-w-md">
        <div className="relative w-full">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search conversation titles..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Conversations List */}
      <Card className="divide-y divide-gray-100 dark:divide-gray-800">
        {isLoading ? (
          <div className="p-6 space-y-4">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        ) : !filtered || filtered.length === 0 ? (
          <div className="p-12 text-center space-y-4">
            <div className="mx-auto w-12 h-12 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-400">
              <History className="h-6 w-6" />
            </div>
            <div>
              <p className="text-base font-semibold text-foreground">No conversations found</p>
              <p className="text-xs text-gray-500 mt-1">
                {search ? 'No sessions match your search.' : 'Start your first research inquiry.'}
              </p>
            </div>
            {!search && (
              <Button onClick={handleStartNew} className="bg-blue-600 text-white">
                <Sparkles className="mr-1.5 h-4 w-4" />
                Start Research
              </Button>
            )}
          </div>
        ) : (
          filtered.map((conv) => (
            <div
              key={conv.id}
              className="p-4 flex items-center justify-between hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
            >
              <div className="flex items-center space-x-3 overflow-hidden pr-4">
                <div className="h-10 w-10 rounded-xl bg-purple-100 dark:bg-purple-950/40 text-purple-600 flex items-center justify-center shrink-0">
                  <MessageSquare className="h-5 w-5" />
                </div>
                <div className="overflow-hidden">
                  <Link
                    to={`/workspace?conv=${conv.id}`}
                    className="font-medium text-foreground hover:text-blue-600 truncate block text-sm sm:text-base"
                  >
                    {conv.title}
                  </Link>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500 mt-1">
                    <span className="font-medium">{conv.message_count} messages</span>
                    {conv.collection_name && (
                      <>
                        <span>•</span>
                        <span className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded text-[11px] text-gray-600 dark:text-gray-300">
                          {conv.collection_name}
                        </span>
                      </>
                    )}
                    <span>•</span>
                    <span>Updated {formatDate(conv.updated_at)}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2 shrink-0">
                <Link to={`/workspace?conv=${conv.id}`}>
                  <Button variant="outline" size="sm" className="hidden sm:inline-flex text-xs">
                    <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                    Open
                  </Button>
                </Link>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setDeleteConv(conv)}
                  className="h-8 w-8 text-gray-400 hover:text-red-600"
                  title="Delete conversation"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))
        )}
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteConv} onOpenChange={(open) => !open && setDeleteConv(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Research Conversation</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{deleteConv?.title}</strong>? All messages and citations in this session will be permanently deleted.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConv(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteConv && deleteMutation.mutate(deleteConv.id)}
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
