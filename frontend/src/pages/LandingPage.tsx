import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Navbar } from '@/components/layout/Navbar'
import {
  FileText,
  Sparkles,
  ShieldCheck,
  ArrowRight,
  Database,
  BookOpen,
} from 'lucide-react'

export function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Navbar />

      {/* Hero Section */}
      <section className="relative px-4 pt-16 pb-20 md:pt-24 md:pb-28 lg:pt-32 max-w-6xl mx-auto text-center">
        {/* Top Announcement Pill */}
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 text-xs font-medium mb-6">
          <Sparkles className="h-3.5 w-3.5 text-blue-600" />
          <span>Next-Generation Retrieval-Augmented Generation</span>
        </div>

        <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-foreground max-w-4xl mx-auto leading-tight">
          AI Document Research with{' '}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400">
            Uncompromising Provenance
          </span>
        </h1>

        <p className="mt-6 text-lg sm:text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto leading-relaxed">
          Upload complex PDFs, academic papers, and technical whitepapers. Ask natural-language
          questions and receive verifiable answers strictly grounded in document text with exact page
          citations.
        </p>

        {/* CTA buttons */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link to="/workspace">
            <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/20 px-8 text-base">
              <span>Open Research Workspace</span>
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
          <Link to="/documents">
            <Button size="lg" variant="outline" className="border-gray-300 dark:border-gray-700">
              <FileText className="mr-2 h-4 w-4" />
              <span>Explore Sample Documents</span>
            </Button>
          </Link>
        </div>

        {/* Feature Highlights Grid */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          <div className="p-6 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white/70 dark:bg-gray-900/60 shadow-xs hover:border-blue-400/50 transition-colors">
            <div className="h-10 w-10 rounded-xl bg-blue-100 dark:bg-blue-900/40 text-blue-600 flex items-center justify-center mb-4">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <h3 className="font-bold text-base text-foreground mb-1">
              Zero Hallucination Tolerance
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 leading-normal">
              Responses are synthesized strictly from retrieved document chunks. When evidence is
              missing, the system answers with an honest declaration.
            </p>
          </div>

          <div className="p-6 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white/70 dark:bg-gray-900/60 shadow-xs hover:border-blue-400/50 transition-colors">
            <div className="h-10 w-10 rounded-xl bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 flex items-center justify-center mb-4">
              <BookOpen className="h-5 w-5" />
            </div>
            <h3 className="font-bold text-base text-foreground mb-1">
              Page-Accurate Citations
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 leading-normal">
              Every factual assertion includes clickable document and page numbers. Clicking a
              citation jumps directly to the source page in the built-in PDF viewer.
            </p>
          </div>

          <div className="p-6 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white/70 dark:bg-gray-900/60 shadow-xs hover:border-blue-400/50 transition-colors">
            <div className="h-10 w-10 rounded-xl bg-purple-100 dark:bg-purple-900/40 text-purple-600 flex items-center justify-center mb-4">
              <Database className="h-5 w-5" />
            </div>
            <h3 className="font-bold text-base text-foreground mb-1">
              pgvector Semantic Search
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 leading-normal">
              Dense vector embeddings indexed in PostgreSQL with HNSW cosine similarity ensure
              instant, high-recall retrieval across thousands of document pages.
            </p>
          </div>
        </div>

        {/* Live Interactive Preview Card */}
        <div className="mt-16 p-6 sm:p-8 rounded-2xl border border-blue-200 dark:border-blue-900/60 bg-gradient-to-b from-blue-50/50 to-white dark:from-blue-950/20 dark:to-gray-900/80 shadow-md text-left">
          <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400 mb-3">
            <Sparkles className="h-4 w-4" />
            <span>Demonstration: Grounded Answer Synthesis</span>
          </div>
          <div className="p-4 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-xs">
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">
              Query: "How does multi-head attention improve over single-head attention?"
            </p>
            <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/60 text-sm text-gray-700 dark:text-gray-300 leading-relaxed font-sans mb-3">
              Multi-head attention allows the model to jointly attend to information from different
              representation subspaces at different positions. With a single attention head, averaging
              inhibits this capability.
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-gray-500 font-medium">Verifiable Citation:</span>
              <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300 text-xs font-medium cursor-pointer border border-blue-200 dark:border-blue-800 hover:bg-blue-200 transition-colors">
                <FileText className="h-3 w-3 text-blue-600" />
                <span>Attention_Is_All_You_Need.pdf (Page 4)</span>
                <span className="text-[10px] bg-blue-600 text-white px-1 rounded">94%</span>
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-gray-200 dark:border-gray-800 py-8 px-4 text-center text-xs text-gray-500 dark:text-gray-400">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-4">
          <p>© 2026 AI Document Research Assistant. Enterprise-grade factual grounding.</p>
          <div className="flex space-x-6">
            <Link to="/workspace" className="hover:text-foreground">Workspace</Link>
            <Link to="/documents" className="hover:text-foreground">Documents</Link>
            <Link to="/collections" className="hover:text-foreground">Collections</Link>
            <Link to="/login" className="hover:text-foreground">Sign In</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
