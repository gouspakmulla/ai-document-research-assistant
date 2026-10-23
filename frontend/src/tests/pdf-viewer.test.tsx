import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { PDFViewer } from '@/components/pdf/PDFViewer'
import { DocumentItem } from '@/types'

const mockDoc: DocumentItem = {
  id: 'doc-test-1',
  user_id: 'usr-1',
  filename: 'test_research_paper.pdf',
  file_size_bytes: 1048576,
  mime_type: 'application/pdf',
  page_count: 10,
  processing_status: 'READY',
  error_message: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
}

describe('PDFViewer Component', () => {
  it('renders document filename and initial page', () => {
    render(<PDFViewer document={mockDoc} initialPage={1} />)
    expect(screen.getAllByText(/test_research_paper.pdf/i).length).toBeGreaterThan(0)
    expect(screen.getByText('/ 10')).toBeInTheDocument()
  })

  it('allows jumping to next page on click', () => {
    const handlePageChange = vi.fn()
    render(<PDFViewer document={mockDoc} initialPage={1} onPageChange={handlePageChange} />)
    const nextBtn = screen.getByLabelText('Next page')
    fireEvent.click(nextBtn)
    expect(handlePageChange).toHaveBeenCalledWith(2)
  })

  it('displays citation excerpt banner when citation text is supplied', () => {
    const snippet = 'Attention weights demonstrate dense sub-layer correlations.'
    render(<PDFViewer document={mockDoc} initialPage={4} highlightText={snippet} />)
    expect(screen.getByText(/Cited Excerpt \(Page 4\)/i)).toBeInTheDocument()
    expect(screen.getAllByText(new RegExp(snippet, 'i')).length).toBeGreaterThan(0)
  })
})
