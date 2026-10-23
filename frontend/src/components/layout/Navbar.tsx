import { Link } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { Button } from '@/components/ui/button'
import {
  FileText,
  Sun,
  Moon,
  LogOut,
  Menu,
  Sparkles,
} from 'lucide-react'

interface NavbarProps {
  onToggleSidebar?: () => void
}

export function Navbar({ onToggleSidebar }: NavbarProps) {
  const { user, isAuthenticated, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="sticky top-0 z-40 w-full glass-nav px-4 lg:px-6 h-16 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        {isAuthenticated && onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="md:hidden p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 text-foreground cursor-pointer"
            aria-label="Toggle navigation"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}
        <Link to="/" className="flex items-center space-x-2.5 group">
          <div className="h-9 w-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-sm shadow-blue-500/30 group-hover:scale-105 transition-transform">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <span className="font-bold text-base tracking-tight text-foreground block">
              DocAssistant
            </span>
            <span className="text-[10px] text-gray-500 dark:text-gray-400 font-medium block leading-none -mt-0.5">
              Research & Provenance
            </span>
          </div>
        </Link>
      </div>

      <div className="flex items-center space-x-2">
        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          aria-label="Toggle theme"
          className="text-gray-600 dark:text-gray-300"
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>

        {isAuthenticated ? (
          <div className="flex items-center space-x-3">
            <Link to="/workspace">
              <Button size="sm" className="hidden sm:inline-flex bg-blue-600 hover:bg-blue-700">
                <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                Research Workspace
              </Button>
            </Link>
            <div className="flex items-center space-x-2 pl-2 border-l border-gray-200 dark:border-gray-800">
              <div className="hidden md:block text-right">
                <p className="text-xs font-semibold text-foreground leading-tight">
                  {user?.full_name || user?.email.split('@')[0]}
                </p>
                <p className="text-[10px] text-gray-400 leading-tight truncate max-w-[140px]">
                  {user?.email}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => logout()}
                title="Log out"
                aria-label="Log out"
                className="text-gray-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex items-center space-x-2">
            <Link to="/login">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link to="/register">
              <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
                Get Started
              </Button>
            </Link>
          </div>
        )}
      </div>
    </header>
  )
}
