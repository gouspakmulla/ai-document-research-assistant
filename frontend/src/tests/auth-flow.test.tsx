import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { api, devMockStorage } from '@/lib/apiClient'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import { UploadModal } from '@/features/documents/UploadModal'
import { User } from '@/types'

const mockAuthUser: User = {
  id: 'usr-auth-123',
  email: 'researcher@example.com',
  full_name: 'Dr. Jane Holloway',
  is_active: true,
  created_at: new Date().toISOString(),
}

describe('Authentication and Upload Session Flow', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    devMockStorage.setUser(null)
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('correctly returns null when no active session exists (prevents fake authentication)', async () => {
    // Mock global fetch returning 401 for /auth/me
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: any) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: false,
          status: 401,
          json: () => Promise.resolve({ detail: 'Authentication session required.' }),
        } as Response)
      }
      return Promise.resolve({ ok: false, status: 404 } as Response)
    })

    const user = await api.me()
    expect(user).toBeNull()
    expect(devMockStorage.getUser()).toBeNull()
  })

  it('restores session when valid HttpOnly session exists', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: any) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve(mockAuthUser),
        } as Response)
      }
      if (url.includes('/auth/csrf')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ csrf_token: 'mock-csrf-token-12345' }),
        } as Response)
      }
      return Promise.resolve({ ok: false, status: 404 } as Response)
    })

    const user = await api.me()
    expect(user).not.toBeNull()
    expect(user?.email).toBe('researcher@example.com')
    expect(devMockStorage.getUser()?.id).toBe(mockAuthUser.id)
  })

  it('handles unauthenticated upload rejection and dispatches auth:unauthorized', async () => {
    const unauthorizedListener = vi.fn()
    window.addEventListener('auth:unauthorized', unauthorizedListener)

    vi.spyOn(globalThis, 'fetch').mockImplementation((input: any) => {
      const url = String(input)
      if (url.includes('/documents/upload')) {
        return Promise.resolve({
          ok: false,
          status: 401,
          json: () => Promise.resolve({ detail: 'Authentication session required.' }),
        } as Response)
      }
      return Promise.resolve({ ok: false, status: 404 } as Response)
    })

    const dummyFile = new File(['%PDF-1.4 dummy content'], 'sample.pdf', { type: 'application/pdf' })

    await expect(api.uploadDocument(dummyFile)).rejects.toThrow('Authentication session required.')
    expect(unauthorizedListener).toHaveBeenCalled()

    window.removeEventListener('auth:unauthorized', unauthorizedListener)
  })

  it('displays authentication required error banner in UploadModal with direct sign-in link', async () => {
    vi.spyOn(api, 'uploadDocument').mockRejectedValue(
      new Error('Authentication session required.')
    )

    const onClose = vi.fn()

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/documents']}>
          <Routes>
            <Route
              path="/documents"
              element={<UploadModal isOpen={true} onClose={onClose} />}
            />
            <Route path="/login" element={<div>Login Page Target</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    )

    // Select file and click upload
    const dummyFile = new File(['%PDF-1.4 dummy content'], 'paper.pdf', { type: 'application/pdf' })
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    expect(fileInput).toBeInTheDocument()

    fireEvent.change(fileInput, { target: { files: [dummyFile] } })

    // File selected, click Upload & Process
    const uploadBtn = screen.getByRole('button', { name: /Upload & Process/i })
    fireEvent.click(uploadBtn)

    // Verify error and sign in link appear
    await waitFor(() => {
      expect(screen.getByText(/Authentication session required\./i)).toBeInTheDocument()
      expect(screen.getByText(/Click here to sign in/i)).toBeInTheDocument()
    })
  })

  it('AuthProvider updates state after login and clears on logout', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: any) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: false,
          status: 401,
          json: () => Promise.resolve({ detail: 'Authentication session required.' }),
        } as Response)
      }
      if (url.includes('/auth/login')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve(mockAuthUser),
        } as Response)
      }
      if (url.includes('/auth/logout')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ message: 'Logged out' }),
        } as Response)
      }
      if (url.includes('/auth/csrf')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ csrf_token: 'csrf-123' }),
        } as Response)
      }
      return Promise.resolve({ ok: false, status: 404 } as Response)
    })

    function TestConsumer() {
      const { user, isAuthenticated, login, logout, isLoading } = useAuth()
      if (isLoading) return <div>Loading...</div>
      return (
        <div>
          <span data-testid="auth-state">{isAuthenticated ? 'logged-in' : 'logged-out'}</span>
          <span data-testid="user-email">{user?.email || 'none'}</span>
          <button onClick={() => login({ email: 'researcher@example.com', password: 'password123' })}>
            Do Login
          </button>
          <button onClick={() => logout()}>Do Logout</button>
        </div>
      )
    }

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    )

    // Initially unauthenticated
    await waitFor(() => {
      expect(screen.getByTestId('auth-state').textContent).toBe('logged-out')
      expect(screen.getByTestId('user-email').textContent).toBe('none')
    })

    // Perform login
    fireEvent.click(screen.getByText('Do Login'))
    await waitFor(() => {
      expect(screen.getByTestId('auth-state').textContent).toBe('logged-in')
      expect(screen.getByTestId('user-email').textContent).toBe('researcher@example.com')
    })

    // Perform logout
    fireEvent.click(screen.getByText('Do Logout'))
    await waitFor(() => {
      expect(screen.getByTestId('auth-state').textContent).toBe('logged-out')
      expect(screen.getByTestId('user-email').textContent).toBe('none')
    })
  })
})
