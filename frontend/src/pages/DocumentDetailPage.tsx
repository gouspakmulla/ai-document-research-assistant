import { useParams, useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/apiClient'
import { PDFViewer } from '@/components/pdf/PDFViewer'
import { StatusBadge } from '@/components/ui/status-badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { formatBytes, formatDate } from '@/lib/utils'
import {
  ArrowLeft,
  Sparkles,
  Info,
  ShieldCheck,
  AlertTriangle,
  Download,
  AlertCircle,
} from 'lucide-react'

export function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams, setSearchParams] = useSearchParams()

  const initialPage = parseInt(searchParams.get('page') || '1', 10)
  const initialSnippet = searchParams.get('snippet') || undefined

  const { data: doc, isLoading, error } = useQuery({
    queryKey: ['document', id],
    queryFn: () => (id ? api.getDocument(id) : Promise.reject('No ID')),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-7xl mx-auto">
        <Skeleton className="h-10 w-48" />
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3">
            <Skeleton className="h-[700px] w-full rounded-xl" />
          </div>
          <div>
            <Skeleton className="h-[400px] w-full rounded-xl" />
          </div>
        </div>
      </div>
    )
  }

  if (error || !doc) {
    return (
      <div className="max-w-md mx-auto text-center py-16 space-y-4">
        <AlertTriangle className="h-12 w-12 text-amber-500 mx-auto" />
        <h2 className="text-xl font-bold text-foreground">Document not found</h2>
        <p className="text-sm text-gray-500">
          The requested document could not be located or you do not have permission to view it.
        </p>
        <Link to="/documents">
          <Button variant="outline">Back to Library</Button>
        </Link>
      </div>
    )
  }

  const isReady = doc.processing_status === 'READY'
  const isOCRRequired = doc.processing_status === 'OCR_REQUIRED'
  const isFailed = doc.processing_status === 'FAILED'

  return (
    <div className="space-y-4 max-w-7xl mx-auto h-[calc(100vh-8.5rem)] flex flex-col">
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-gray-200 dark:border-gray-800 shrink-0">
        <div className="flex items-center space-x-3 overflow-hidden">
          <Link to="/documents">
            <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-500">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div className="overflow-hidden">
            <h1 className="text-lg font-bold text-foreground truncate max-w-md sm:max-w-xl">
              {doc.filename}
            </h1>
            <div className="flex items-center space-x-2 text-xs text-gray-500">
              <StatusBadge status={doc.processing_status} />
              <span>•</span>
              <span>{doc.page_count} Pages</span>
              <span>•</span>
              <span>{formatBytes(doc.file_size_bytes)}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <a
            href={api.getDocumentContentUrl(doc.id)}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="outline" size="sm" className="text-xs sm:text-sm">
              <Download className="mr-1.5 h-3.5 w-3.5" />
              View / Download PDF
            </Button>
          </a>
          {isReady ? (
            <Link to={`/workspace?doc=${doc.id}`}>
              <Button className="bg-blue-600 hover:bg-blue-700 text-white shadow-xs text-xs sm:text-sm">
                <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                Ask Document Questions
              </Button>
            </Link>
          ) : (
            <Button
              disabled
              variant="secondary"
              className="opacity-60 cursor-not-allowed text-xs sm:text-sm"
              title="Document processing must succeed before asking questions."
            >
              <Sparkles className="mr-1.5 h-3.5 w-3.5" />
              Querying Locked
            </Button>
          )}
        </div>
      </div>

      {/* Processing Status Banner if not READY */}
      {isOCRRequired && (
        <div className="p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 rounded-lg flex items-start space-x-3 text-xs text-amber-800 dark:text-amber-300">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
          <div>
            <span className="font-semibold block">Scanned PDF Detected (OCR Required)</span>
            <span>
              This document consists of scanned pages or image layers with insufficient digital text.
              Optical Character Recognition (OCR) is required before its content can be indexed for question answering.
            </span>
          </div>
        </div>
      )}

      {isFailed && (
        <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-lg flex items-start space-x-3 text-xs text-red-800 dark:text-red-300">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-red-600 dark:text-red-400" />
          <div>
            <span className="font-semibold block">Processing Failed</span>
            <span>{doc.error_message || 'Document extraction or chunking encountered an unrecoverable error.'}</span>
          </div>
        </div>
      )}

      {/* Main Grid: Viewer + Metadata Panel */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6 overflow-hidden">
        {/* PDF Viewer Canvas (3 Columns) */}
        <div className="lg:col-span-3 h-full overflow-hidden">
          <PDFViewer
            document={doc}
            initialPage={initialPage}
            highlightText={initialSnippet}
            onPageChange={(p) => {
              const next = new URLSearchParams(searchParams)
              next.set('page', String(p))
              setSearchParams(next, { replace: true })
            }}
          />
        </div>

        {/* Metadata Sidebar (1 Column) */}
        <div className="space-y-4 overflow-y-auto">
          <Card className="p-4 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 flex items-center space-x-1.5">
              <Info className="h-3.5 w-3.5 text-blue-500" />
              <span>Document Metadata</span>
            </h3>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-gray-400 block mb-0.5">Ingestion Status</span>
                <StatusBadge status={doc.processing_status} />
              </div>

              <div>
                <span className="text-gray-400 block mb-0.5">Total Pages</span>
                <span className="font-semibold text-foreground">{doc.page_count} pages extracted</span>
              </div>

              <div>
                <span className="text-gray-400 block mb-0.5">MIME Type</span>
                <span className="font-mono text-foreground">{doc.mime_type}</span>
              </div>

              <div>
                <span className="text-gray-400 block mb-0.5">File Size</span>
                <span className="text-foreground">{formatBytes(doc.file_size_bytes)}</span>
              </div>

              <div>
                <span className="text-gray-400 block mb-0.5">Upload Date</span>
                <span className="text-foreground">{formatDate(doc.created_at)}</span>
              </div>

              {doc.checksum_sha256 && (
                <div>
                  <span className="text-gray-400 block mb-0.5">SHA-256 Checksum</span>
                  <span className="font-mono text-[10px] text-gray-500 truncate block bg-gray-50 dark:bg-gray-800 p-1.5 rounded">
                    {doc.checksum_sha256}
                  </span>
                </div>
              )}
            </div>

            <div className="pt-2 border-t border-gray-100 dark:border-gray-800">
              <div className="p-2.5 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 text-xs flex items-start space-x-2">
                <ShieldCheck className="h-4 w-4 shrink-0 mt-0.5 text-blue-500" />
                <span>
                  Exact page numbers are preserved and cross-referenced with all generated RAG citations.
                </span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
