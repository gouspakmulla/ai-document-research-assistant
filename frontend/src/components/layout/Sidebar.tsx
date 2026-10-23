import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Files,
  Sparkles,
  FolderKanban,
  History,
  Settings,
  Upload,
  ShieldCheck,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface SidebarProps {
  isOpen: boolean
  onClose?: () => void
  onOpenUpload?: () => void
}

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/documents', label: 'Document Library', icon: Files },
  { to: '/workspace', label: 'Research Workspace', icon: Sparkles },
  { to: '/collections', label: 'Collections', icon: FolderKanban },
  { to: '/history', label: 'Conversation History', icon: History },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function Sidebar({ isOpen, onClose, onOpenUpload }: SidebarProps) {
  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden backdrop-blur-xs"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          'fixed md:static inset-y-0 left-0 z-40 w-64 border-r border-gray-200 dark:border-gray-800 bg-white/95 dark:bg-gray-900/90 backdrop-blur-md flex flex-col transition-transform duration-200 ease-in-out md:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Quick action: Upload PDF */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-800">
          <Button
            onClick={onOpenUpload}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white shadow-sm flex items-center justify-center space-x-2"
          >
            <Upload className="h-4 w-4" />
            <span>Upload Document</span>
          </Button>
        </div>

        {/* Navigation list */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onClose}
                className={({ isActive }) =>
                  cn(
                    'flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/60 hover:text-foreground'
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            )
          })}
        </nav>

        {/* Provenance and Security badge at bottom of sidebar */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-800">
          <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/40 border border-gray-200/70 dark:border-gray-700/50">
            <div className="flex items-center space-x-2 text-xs font-semibold text-gray-700 dark:text-gray-300">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span>Grounded Citations</span>
            </div>
            <p className="mt-1 text-[11px] text-gray-500 dark:text-gray-400 leading-normal">
              Every AI response is strictly tied to verified PDF page excerpts.
            </p>
          </div>
        </div>
      </aside>
    </>
  )
}
