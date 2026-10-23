import React, { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Navbar } from './Navbar'
import { Sidebar } from './Sidebar'
import { UploadModal } from '@/features/documents/UploadModal'
import { Info } from 'lucide-react'

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Navbar onToggleSidebar={() => setSidebarOpen((prev) => !prev)} />

      {/* Dev Fixture Boundary Banner */}
      <div className="bg-blue-600/10 dark:bg-blue-950/30 border-b border-blue-200 dark:border-blue-900/40 px-4 py-1.5 text-xs text-blue-700 dark:text-blue-300 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Info className="h-3.5 w-3.5 shrink-0" />
          <span>
            <strong>Interactive Mode:</strong> Connected to typed API client. Standalone local development fixtures active until Backend Phase is started.
          </span>
        </div>
        <button
          onClick={() => setUploadOpen(true)}
          className="text-blue-700 dark:text-blue-300 font-semibold underline hover:no-underline cursor-pointer"
        >
          + Quick Upload
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onOpenUpload={() => setUploadOpen(true)}
        />

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 bg-gray-50/50 dark:bg-gray-950/50">
          <Outlet />
        </main>
      </div>

      <UploadModal
        isOpen={uploadOpen}
        onClose={() => setUploadOpen(false)}
      />
    </div>
  )
}
