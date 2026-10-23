import React, { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/apiClient'
import { MessageCitation } from '@/types'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { PDFViewer } from '@/components/pdf/PDFViewer'
import {
  Send,
  Sparkles,
  Bot,
  User as UserIcon,
  FileText,
  ExternalLink,
  ShieldCheck,
  Plus,
  Split,
  X,
  AlertCircle,
} from 'lucide-react'

export function WorkspacePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()

  const selectedConvId = searchParams.get('conv') || undefined
  const selectedDocId = searchParams.get('doc') || undefined
  const selectedColId = searchParams.get('col') || undefined

  const [inputQuery, setInputQuery] = useState('')
  const [activeCitation, setActiveCitation] = useState<MessageCitation | null>(null)
  const [showSplitViewer, setShowSplitViewer] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Fetch collections & documents for context scoping selector
  const { data: documents } = useQuery({
    queryKey: ['documents'],
    queryFn: () => api.getDocuments(),
  })

  const { data: collections } = useQuery({
    queryKey: ['collections'],
    queryFn: () => api.getCollections(),
  })

  const { data: conversations } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => api.getConversations(),
  })

  // Selected conversation ID fallback
  const currentConvId =
    selectedConvId || (conversations && conversations.length > 0 ? conversations[0].id : '')

  const { data: messages, isLoading: messagesLoading } = useQuery({
    queryKey: ['messages', currentConvId],
    queryFn: () => (currentConvId ? api.getMessages(currentConvId) : Promise.resolve([])),
    enabled: !!currentConvId,
  })

  const activeDoc = documents?.find((d) => d.id === selectedDocId)

  // Query mutation for asking questions
  const askMutation = useMutation({
    mutationFn: (question: string) =>
      api.askQuestion({
        question,
        conversation_id: currentConvId || undefined,
        document_id: selectedDocId,
        collection_id: selectedColId,
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['messages', data.conversation_id] })
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      if (!selectedConvId) {
        const next = new URLSearchParams(searchParams)
        next.set('conv', data.conversation_id)
        setSearchParams(next)
      }
      setInputQuery('')
    },
  })

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation('New Research Inquiry', selectedColId)
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      const next = new URLSearchParams(searchParams)
      next.set('conv', newConv.id)
      setSearchParams(next)
    } catch {
      // Backend error will be caught
    }
  }

  const handleSendMessage = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!inputQuery.trim() || askMutation.isPending) return
    askMutation.mutate(inputQuery.trim())
  }

  const handleCitationClick = (cit: MessageCitation) => {
    setActiveCitation(cit)
    setShowSplitViewer(true)
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, askMutation.isPending])

  // Active document for split-screen viewer
  const citationDoc = activeCitation
    ? documents?.find((d) => d.id === activeCitation.document_id) || activeDoc
    : activeDoc

  return (
    <div className="h-[calc(100vh-8.5rem)] flex flex-col max-w-7xl mx-auto space-y-3">
      {/* Workspace Context Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-xs shrink-0 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-gray-500 uppercase tracking-wider text-[11px] flex items-center space-x-1">
            <Sparkles className="h-3.5 w-3.5 text-blue-600" />
            <span>Research Scope:</span>
          </span>

          {/* Collection / Document scope pill */}
          <select
            value={selectedDocId ? `doc:${selectedDocId}` : selectedColId ? `col:${selectedColId}` : 'all'}
            onChange={(e) => {
              const val = e.target.value
              const next = new URLSearchParams(searchParams)
              if (val.startsWith('doc:')) {
                next.set('doc', val.replace('doc:', ''))
                next.delete('col')
              } else if (val.startsWith('col:')) {
                next.set('col', val.replace('col:', ''))
                next.delete('doc')
              } else {
                next.delete('doc')
                next.delete('col')
              }
              setSearchParams(next)
            }}
            className="px-2.5 py-1 rounded-md border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-foreground font-medium focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer"
          >
            <option value="all">Entire Library (All Verified Documents)</option>
            {collections && collections.length > 0 && (
              <optgroup label="Collections">
                {collections.map((col) => (
                  <option key={col.id} value={`col:${col.id}`}>
                    Collection: {col.name} ({col.document_count} docs)
                  </option>
                ))}
              </optgroup>
            )}
            {documents && documents.length > 0 && (
              <optgroup label="Individual Documents">
                {documents.map((d) => (
                  <option key={d.id} value={`doc:${d.id}`}>
                    Document: {d.filename}
                  </option>
                ))}
              </optgroup>
            )}
          </select>

          {/* Conversation Selector */}
          {conversations && conversations.length > 0 && (
            <select
              value={currentConvId}
              onChange={(e) => {
                const next = new URLSearchParams(searchParams)
                next.set('conv', e.target.value)
                setSearchParams(next)
              }}
              className="px-2.5 py-1 rounded-md border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-foreground font-medium focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer max-w-[200px] truncate"
            >
              {conversations.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
          )}

          <Button
            size="sm"
            variant="ghost"
            onClick={handleNewConversation}
            className="h-7 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-950/40"
          >
            <Plus className="mr-1 h-3 w-3" />
            New Inquiry
          </Button>
        </div>

        <div className="flex items-center space-x-2">
          {citationDoc && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowSplitViewer((v) => !v)}
              className="h-7 text-xs border-gray-200 dark:border-gray-700"
            >
              <Split className="mr-1.5 h-3.5 w-3.5 text-blue-600" />
              <span>{showSplitViewer ? 'Hide PDF Viewer' : 'View PDF Source'}</span>
            </Button>
          )}
        </div>
      </div>

      {/* Main Content Area: Split View or Full Chat */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 overflow-hidden">
        {/* Chat Conversation Column */}
        <div
          className={`${
            showSplitViewer && citationDoc ? 'lg:col-span-6' : 'lg:col-span-12'
          } flex flex-col h-full bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-xs`}
        >
          {/* Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
            {messagesLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-16 w-3/4 ml-auto rounded-xl" />
                <Skeleton className="h-28 w-5/6 rounded-xl" />
              </div>
            ) : !messages || messages.length === 0 ? (
              <div className="text-center py-16 space-y-3">
                <div className="h-12 w-12 rounded-2xl bg-blue-50 dark:bg-blue-950/40 text-blue-600 flex items-center justify-center mx-auto">
                  <Bot className="h-6 w-6" />
                </div>
                <h3 className="font-bold text-base text-foreground">
                  Ready for Grounded Document Research
                </h3>
                <p className="text-xs text-gray-500 max-w-md mx-auto">
                  Ask any question regarding your study materials. The assistant will retrieve
                  relevant text chunks and synthesize an evidence-backed answer with source citations.
                </p>
                <div className="pt-4 flex flex-wrap justify-center gap-2 max-w-lg mx-auto">
                  <button
                    onClick={() => setInputQuery('What are the primary theoretical contributions presented in this document?')}
                    className="p-2 rounded-lg bg-gray-50 dark:bg-gray-800/60 hover:bg-blue-50 dark:hover:bg-blue-950/40 border border-gray-200 dark:border-gray-700 text-left text-xs text-gray-700 dark:text-gray-300 transition-colors"
                  >
                    "What are the primary theoretical contributions presented in this document?"
                  </button>
                  <button
                    onClick={() => setInputQuery('Summarize the methodology and experimental setup with exact page citations.')}
                    className="p-2 rounded-lg bg-gray-50 dark:bg-gray-800/60 hover:bg-blue-50 dark:hover:bg-blue-950/40 border border-gray-200 dark:border-gray-700 text-left text-xs text-gray-700 dark:text-gray-300 transition-colors"
                  >
                    "Summarize the methodology and experimental setup with exact page citations."
                  </button>
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${
                    msg.role === 'user' ? 'items-end' : 'items-start'
                  }`}
                >
                  <div className="flex items-center space-x-1.5 text-xs text-gray-400 mb-1 px-1">
                    {msg.role === 'user' ? (
                      <>
                        <span>You</span>
                        <UserIcon className="h-3 w-3" />
                      </>
                    ) : (
                      <>
                        <Bot className="h-3.5 w-3.5 text-blue-600" />
                        <span className="font-semibold text-blue-600 dark:text-blue-400">
                          AI Research Assistant
                        </span>
                      </>
                    )}
                  </div>

                  <div
                    className={`p-4 rounded-2xl max-w-2xl text-sm leading-relaxed shadow-xs ${
                      msg.role === 'user'
                        ? 'bg-blue-600 text-white rounded-br-xs'
                        : 'bg-gray-50 dark:bg-gray-800/70 border border-gray-200 dark:border-gray-700/60 text-foreground rounded-bl-xs'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{msg.content}</div>

                    {/* Grounded Citation Badges */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-gray-200/60 dark:border-gray-700/60">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-gray-500 block mb-2 flex items-center space-x-1">
                          <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
                          <span>Verifiable Sources & Citations:</span>
                        </span>
                        <div className="flex flex-wrap gap-2">
                          {msg.citations.map((cit) => (
                            <button
                              key={cit.id}
                              onClick={() => handleCitationClick(cit)}
                              className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-white dark:bg-gray-900 border border-blue-200 dark:border-blue-800/80 hover:border-blue-400 text-left text-xs text-foreground hover:bg-blue-50/50 dark:hover:bg-blue-950/40 transition-colors shadow-2xs cursor-pointer group"
                            >
                              <FileText className="h-3.5 w-3.5 text-blue-600 shrink-0" />
                              <span className="font-medium truncate max-w-[160px]">
                                {cit.document_name}
                              </span>
                              <span className="font-semibold text-blue-600 bg-blue-50 dark:bg-blue-950 px-1 rounded">
                                P. {cit.page_number}
                              </span>
                              <span className="text-[10px] text-gray-400 font-mono">
                                {Math.round(cit.relevance_score * 100)}%
                              </span>
                              <ExternalLink className="h-3 w-3 text-gray-400 group-hover:text-blue-600 ml-0.5" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}

            {/* Waiting for response state */}
            {askMutation.isPending && (
              <div className="flex flex-col items-start space-y-2">
                <div className="flex items-center space-x-1.5 text-xs text-blue-600">
                  <Bot className="h-3.5 w-3.5" />
                  <span className="font-medium animate-pulse">
                    Retrieving vector chunks and synthesizing grounded answer...
                  </span>
                </div>
                <div className="p-4 rounded-2xl bg-gray-50 dark:bg-gray-800/70 border border-gray-200 dark:border-gray-700/60 w-80 space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-4/5" />
                </div>
              </div>
            )}

            {/* Error State Banner */}
            {askMutation.isError && (
              <div className="p-3.5 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-xs text-red-700 dark:text-red-300 flex items-center justify-between shadow-2xs">
                <div className="flex items-center space-x-2">
                  <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
                  <span>
                    {(askMutation.error as Error)?.message || 'Failed to generate answer. Please try again.'}
                  </span>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => askMutation.reset()}
                  className="h-6 px-2 text-[11px] border-red-300 dark:border-red-700 hover:bg-red-100 dark:hover:bg-red-900"
                >
                  Dismiss
                </Button>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Question Input Box */}
          <div className="p-3 sm:p-4 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800">
            <form onSubmit={handleSendMessage} className="flex items-center space-x-2">
              <input
                type="text"
                placeholder="Ask a question grounded in your documents (e.g. 'Summarize Section 3 findings')..."
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                disabled={askMutation.isPending}
                className="flex-1 px-4 py-2.5 text-sm rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 text-foreground placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <Button
                type="submit"
                disabled={!inputQuery.trim() || askMutation.isPending}
                className="h-10 px-5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white shadow-xs shrink-0"
              >
                <Send className="h-4 w-4" />
                <span className="sr-only">Send query</span>
              </Button>
            </form>
            <p className="mt-1.5 text-[11px] text-gray-400 text-center">
              Strict factual grounding: Claims without retrieved document support will be flagged as insufficient evidence.
            </p>
          </div>
        </div>

        {/* Split Screen PDF Viewer (Opened when clicking citation or toggle) */}
        {showSplitViewer && citationDoc && (
          <div className="lg:col-span-6 h-full flex flex-col relative">
            <div className="absolute right-3 top-3 z-10">
              <Button
                variant="secondary"
                size="icon"
                onClick={() => setShowSplitViewer(false)}
                className="h-7 w-7 rounded-full shadow-md bg-white dark:bg-gray-800"
                title="Close PDF view"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
            <PDFViewer
              document={citationDoc}
              initialPage={activeCitation ? activeCitation.page_number : 1}
              highlightText={activeCitation ? activeCitation.snippet : undefined}
            />
          </div>
        )}
      </div>
    </div>
  )
}
