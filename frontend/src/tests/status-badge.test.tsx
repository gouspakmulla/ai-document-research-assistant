import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusBadge } from '@/components/ui/status-badge'

describe('StatusBadge Component', () => {
  it('renders Ready status with check icon', () => {
    render(<StatusBadge status="READY" />)
    expect(screen.getByText('Ready')).toBeInTheDocument()
  })

  it('renders Extracting status with animation', () => {
    render(<StatusBadge status="EXTRACTING" />)
    expect(screen.getByText('Extracting text...')).toBeInTheDocument()
  })

  it('renders OCR Required status for scanned documents', () => {
    render(<StatusBadge status="OCR_REQUIRED" />)
    expect(screen.getByText('OCR Required')).toBeInTheDocument()
  })

  it('renders Failed status for failed indexing', () => {
    render(<StatusBadge status="FAILED" />)
    expect(screen.getByText('Failed')).toBeInTheDocument()
  })
})
