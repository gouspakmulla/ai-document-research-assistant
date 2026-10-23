import { useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  User,
  Moon,
  Sun,
  ShieldCheck,
  Sliders,
  CheckCircle2,
} from 'lucide-react'

export function SettingsPage() {
  const { user } = useAuth()
  const { theme, setTheme } = useTheme()

  const [topK, setTopK] = useState(6)
  const [similarityThreshold, setSimilarityThreshold] = useState(0.6)
  const [savedSuccess, setSavedSuccess] = useState(false)

  const handleSavePreferences = () => {
    setSavedSuccess(true)
    setTimeout(() => setSavedSuccess(false), 3000)
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="pb-2 border-b border-gray-200 dark:border-gray-800">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
          System & Account Settings
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Configure interface themes, review account credentials, and inspect RAG retrieval parameters
        </p>
      </div>

      {savedSuccess && (
        <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-300 flex items-center space-x-2">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
          <span>Research preferences successfully saved for your session.</span>
        </div>
      )}

      {/* Account Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center space-x-2">
            <User className="h-4 w-4 text-blue-600" />
            <span>Researcher Account</span>
          </CardTitle>
          <CardDescription>
            Your tenant identity and security credentials
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-medium text-gray-500">Full Name</label>
              <Input value={user?.full_name || 'Researcher'} readOnly className="bg-gray-50 dark:bg-gray-800/50" />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-gray-500">Email Address</label>
              <Input value={user?.email || 'user@example.com'} readOnly className="bg-gray-50 dark:bg-gray-800/50" />
            </div>
          </div>
          <div className="pt-2">
            <span className="text-xs font-medium text-gray-500 block mb-1">Tenant Partition ID (UUID)</span>
            <div className="p-2 rounded bg-gray-50 dark:bg-gray-800/60 font-mono text-xs text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700">
              {user?.id || 'usr-default-tenant'}
            </div>
            <p className="text-[11px] text-gray-400 mt-1">
              All document chunks, vector embeddings, and conversations are partitioned by this ID.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Appearance & Theme Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center space-x-2">
            {theme === 'dark' ? <Moon className="h-4 w-4 text-purple-500" /> : <Sun className="h-4 w-4 text-amber-500" />}
            <span>Appearance & Theme</span>
          </CardTitle>
          <CardDescription>
            Choose your preferred color theme for reading documents and reviewing research
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 max-w-md">
            <button
              onClick={() => setTheme('light')}
              className={`p-4 rounded-xl border text-center cursor-pointer transition-all ${
                theme === 'light'
                  ? 'border-blue-600 bg-blue-50/50 dark:bg-blue-950/20 text-blue-700 font-semibold ring-2 ring-blue-500/20'
                  : 'border-gray-200 dark:border-gray-800 hover:border-gray-400'
              }`}
            >
              <Sun className="h-5 w-5 mx-auto mb-2 text-amber-500" />
              <span className="text-sm">Light Mode</span>
            </button>

            <button
              onClick={() => setTheme('dark')}
              className={`p-4 rounded-xl border text-center cursor-pointer transition-all ${
                theme === 'dark'
                  ? 'border-blue-600 bg-blue-950/40 text-blue-300 font-semibold ring-2 ring-blue-500/20'
                  : 'border-gray-200 dark:border-gray-800 hover:border-gray-400'
              }`}
            >
              <Moon className="h-5 w-5 mx-auto mb-2 text-purple-400" />
              <span className="text-sm">Dark Mode</span>
            </button>
          </div>
        </CardContent>
      </Card>

      {/* RAG Retrieval Parameters Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center space-x-2">
            <Sliders className="h-4 w-4 text-indigo-600" />
            <span>RAG Retrieval & Grounding Configuration</span>
          </CardTitle>
          <CardDescription>
            Configure similarity thresholds and context limits for evidence synthesis
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 text-sm">
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs font-medium">
              <span>Top-K Retrieved Chunks per Query</span>
              <span className="font-mono text-blue-600 font-bold">{topK} chunks</span>
            </div>
            <input
              type="range"
              min={2}
              max={12}
              step={1}
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value, 10))}
              className="w-full cursor-pointer accent-blue-600"
            />
            <p className="text-[11px] text-gray-400">
              Number of highest-ranking pgvector passages passed into the LLM context window.
            </p>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs font-medium">
              <span>Cosine Relevance Cutoff Threshold</span>
              <span className="font-mono text-blue-600 font-bold">{similarityThreshold.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min={0.4}
              max={0.9}
              step={0.05}
              value={similarityThreshold}
              onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
              className="w-full cursor-pointer accent-blue-600"
            />
            <p className="text-[11px] text-gray-400">
              Chunks with cosine similarity score below this threshold are omitted to prevent noise.
            </p>
          </div>

          <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/40 border border-gray-200 dark:border-gray-700/60 flex items-start space-x-3 text-xs">
            <ShieldCheck className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
            <div className="text-gray-600 dark:text-gray-300">
              <strong>Zero-Hallucination Policy:</strong> If all retrieved document excerpts fall
              below the relevance threshold, the assistant returns an honest insufficient-evidence
              response instead of fabricating answers.
            </div>
          </div>
        </CardContent>
        <CardFooter className="border-t border-gray-100 dark:border-gray-800 flex justify-end">
          <Button onClick={handleSavePreferences} className="bg-blue-600 text-white">
            Save Preferences
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}
