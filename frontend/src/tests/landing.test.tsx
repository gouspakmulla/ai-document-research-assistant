import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { LandingPage } from '@/pages/LandingPage'
import { AuthProvider } from '@/context/AuthContext'
import { ThemeProvider } from '@/context/ThemeContext'

describe('LandingPage Component', () => {
  it('renders title and primary CTA button', async () => {
    render(
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <LandingPage />
          </BrowserRouter>
        </AuthProvider>
      </ThemeProvider>
    )

    await waitFor(() => {
      expect(screen.getByText(/AI Document Research with/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/Uncompromising Provenance/i)).toBeInTheDocument()
    expect(screen.getByText(/Open Research Workspace/i)).toBeInTheDocument()
    expect(screen.getByText(/Zero Hallucination Tolerance/i)).toBeInTheDocument()
  })
})
