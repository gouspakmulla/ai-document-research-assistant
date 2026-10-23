import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/apiClient'
import { useAuth } from '@/context/AuthContext'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/ui/status-badge'
import { Skeleton } from '@/components/ui/skeleton'
import { UploadModal } from '@/features/documents/UploadModal'
import { formatDate, formatBytes } from '@/lib/utils'
import {
  Files,
  FolderKanban,
  MessageSquare,
  BookOpen,
  Upload,
  Sparkles,
  ArrowRight,
  ExternalLink,
} from 'lucide-react'

export function DashboardPage() {
  const { user } = useAuth()
  const [uploadOpen, setUploadOpen] = useState(false)

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.getStats(),
  })

  const { data: documents, isLoading: docsLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: () => api.getDocuments(),
  })

  const { data: collections, isLoading: colsLoading } = useQuery({
    queryKey: ['collections'],
    queryFn: () => api.getCollections(),
  })

  const { data: conversations, isLoading: convsLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => api.getConversations(),
  })

  const recentDocs = documents?.slice(0, 4) || []
  const recentConvs = conversations?.slice(0, 3) || []

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Welcome Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-gray-200 dark:border-gray-800">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Welcome back, {user?.full_name || 'Researcher'}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Research dashboard & document index status
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            onClick={() => setUploadOpen(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
          >
            <Upload className="mr-1.5 h-4 w-4" />
            Upload PDF
          </Button>
          <Link to="/workspace">
            <Button variant="outline" className="border-gray-300 dark:border-gray-700">
              <Sparkles className="mr-1.5 h-4 w-4 text-blue-600" />
              Workspace
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
              Total Documents
            </span>
            <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600">
              <Files className="h-4 w-4" />
            </div>
          </div>
          {statsLoading ? (
            <Skeleton className="h-8 w-16 mt-2" />
          ) : (
            <p className="text-2xl font-bold text-foreground mt-2">
              {stats?.total_documents ?? 0}
            </p>
          )}
          <p className="text-[11px] text-gray-400 mt-1">Indexed in personal library</p>
        </Card>

        <Card className="p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
              Pages Indexed
            </span>
            <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600">
              <BookOpen className="h-4 w-4" />
            </div>
          </div>
          {statsLoading ? (
            <Skeleton className="h-8 w-16 mt-2" />
          ) : (
            <p className="text-2xl font-bold text-foreground mt-2">
              {stats?.total_pages_indexed ?? 0}
            </p>
          )}
          <p className="text-[11px] text-gray-400 mt-1">Ready for pgvector RAG</p>
        </Card>

        <Card className="p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
              Collections
            </span>
            <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600">
              <FolderKanban className="h-4 w-4" />
            </div>
          </div>
          {statsLoading ? (
            <Skeleton className="h-8 w-16 mt-2" />
          ) : (
            <p className="text-2xl font-bold text-foreground mt-2">
              {stats?.total_collections ?? 0}
            </p>
          )}
          <p className="text-[11px] text-gray-400 mt-1">Organized study topics</p>
        </Card>

        <Card className="p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
              Research Sessions
            </span>
            <div className="p-2 rounded-lg bg-purple-50 dark:bg-purple-950/40 text-purple-600">
              <MessageSquare className="h-4 w-4" />
            </div>
          </div>
          {statsLoading ? (
            <Skeleton className="h-8 w-16 mt-2" />
          ) : (
            <p className="text-2xl font-bold text-foreground mt-2">
              {stats?.total_conversations ?? 0}
            </p>
          )}
          <p className="text-[11px] text-gray-400 mt-1">Persistent grounded chats</p>
        </Card>
      </div>

      {/* Main Dashboard Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Recent Documents */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-foreground">Recent Documents</h2>
            <Link to="/documents" className="text-xs text-blue-600 hover:underline flex items-center">
              <span>View all documents</span>
              <ArrowRight className="ml-1 h-3 w-3" />
            </Link>
          </div>

          <Card className="divide-y divide-gray-100 dark:divide-gray-800">
            {docsLoading ? (
              <div className="p-6 space-y-4">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : recentDocs.length === 0 ? (
              <div className="p-8 text-center text-sm text-gray-500">
                No documents uploaded yet. Upload your first PDF to begin.
              </div>
            ) : (
              recentDocs.map((doc) => (
                <div
                  key={doc.id}
                  className="p-4 flex items-center justify-between hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
                >
                  <div className="flex items-center space-x-3 overflow-hidden pr-4">
                    <div className="h-9 w-9 rounded-lg bg-red-100 dark:bg-red-950/40 text-red-600 flex items-center justify-center shrink-0">
                      <Files className="h-4 w-4" />
                    </div>
                    <div className="overflow-hidden">
                      <Link
                        to={`/documents/${doc.id}`}
                        className="text-sm font-medium text-foreground hover:text-blue-600 truncate block max-w-sm"
                      >
                        {doc.filename}
                      </Link>
                      <div className="flex items-center space-x-2 text-[11px] text-gray-500 mt-0.5">
                        <span>{formatBytes(doc.file_size_bytes)}</span>
                        <span>•</span>
                        <span>{doc.page_count} pages</span>
                        <span>•</span>
                        <span>{formatDate(doc.created_at)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3 shrink-0">
                    <StatusBadge status={doc.processing_status} />
                    <Link to={`/documents/${doc.id}`}>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:text-foreground">
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </Link>
                  </div>
                </div>
              ))
            )}
          </Card>

          {/* Quick Research Query Prompt */}
          <Card className="p-6 bg-gradient-to-r from-blue-500/10 via-indigo-500/10 to-transparent border-blue-200/60 dark:border-blue-900/40">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-bold text-base text-foreground flex items-center space-x-2">
                  <Sparkles className="h-4 w-4 text-blue-600" />
                  <span>Start Grounded Research Session</span>
                </h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 max-w-xl">
                  Ask cross-document questions against your library or target a specific collection.
                  Every answer includes exact page citations.
                </p>
              </div>
              <Link to="/workspace">
                <Button className="bg-blue-600 hover:bg-blue-700 text-white shrink-0 ml-4">
                  Open Workspace
                </Button>
              </Link>
            </div>
          </Card>
        </div>

        {/* Right Column: Recent Research Sessions & Collections */}
        <div className="space-y-6">
          {/* Recent Conversations */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-foreground">Recent Sessions</h2>
              <Link to="/history" className="text-xs text-blue-600 hover:underline">
                History
              </Link>
            </div>
            <Card className="divide-y divide-gray-100 dark:divide-gray-800">
              {convsLoading ? (
                <div className="p-4 space-y-3">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ) : recentConvs.length === 0 ? (
                <div className="p-6 text-center text-xs text-gray-500">
                  No research conversations yet.
                </div>
              ) : (
                recentConvs.map((conv) => (
                  <Link
                    key={conv.id}
                    to={`/workspace?conv=${conv.id}`}
                    className="p-3.5 block hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors"
                  >
                    <p className="text-xs font-semibold text-foreground truncate">
                      {conv.title}
                    </p>
                    <div className="flex items-center justify-between text-[11px] text-gray-400 mt-1">
                      <span>{conv.message_count} messages</span>
                      <span>{formatDate(conv.updated_at)}</span>
                    </div>
                  </Link>
                ))
              )}
            </Card>
          </div>

          {/* Collections Shortcut */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-foreground">Collections</h2>
              <Link to="/collections" className="text-xs text-blue-600 hover:underline">
                Manage
              </Link>
            </div>
            <div className="space-y-2">
              {colsLoading ? (
                <Skeleton className="h-16 w-full" />
              ) : (
                collections?.map((col) => (
                  <Link
                    key={col.id}
                    to={`/workspace?col=${col.id}`}
                    className="p-3.5 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/60 block hover:border-blue-400 dark:hover:border-blue-600 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-semibold text-foreground truncate">
                        {col.name}
                      </p>
                      <span className="text-[10px] bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-full text-gray-500">
                        {col.document_count} docs
                      </span>
                    </div>
                    {col.description && (
                      <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1 line-clamp-1">
                        {col.description}
                      </p>
                    )}
                  </Link>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      <UploadModal isOpen={uploadOpen} onClose={() => setUploadOpen(false)} />
    </div>
  )
}
