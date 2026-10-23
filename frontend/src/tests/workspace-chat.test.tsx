import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { WorkspacePage } from '@/pages/WorkspacePage'
import { api } from '@/lib/apiClient'
import { MessageItem, DocumentItem, ConversationItem } from '@/types'

const mockDoc: DocumentItem = {
  id: 'doc-1',
  user_id: 'usr-1',
  filename: 'quantum_algorithms.pdf',
  file_size_bytes: 2048,
  mime_type: 'application/pdf',
  page_count: 5,
  processing_status: 'READY',
  error_message: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
}

const mockConv: ConversationItem = {
  id: 'conv-1',
  user_id: 'usr-1',
  title: 'Quantum Inquiry',
  collection_id: null,
  message_count: 2,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
}

const mockMessages: MessageItem[] = [
  {
    id: 'msg-1',
    conversation_id: 'conv-1',
    role: 'user',
    content: 'What is Grover algorithm?',
    created_at: new Date().toISOString(),
  },
  {
    id: 'msg-2',
    conversation_id: 'conv-1',
    role: 'assistant',
    content: 'Grover algorithm provides quadratic speedup for unstructured database search [Source 1].',
    created_at: new Date().toISOString(),
    citations: [
      {
        id: 'cit-1',
        message_id: 'msg-2',
        document_id: 'doc-1',
        chunk_id: 'chk-1',
        document_name: 'quantum_algorithms.pdf',
        page_number: 3,
        snippet: 'Grover algorithm provides quadratic speedup over classical brute-force search.',
        relevance_score: 0.94,
        created_at: new Date().toISOString(),
      },
    ],
  },
]

describe('WorkspacePage Chat and Citations', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
    vi.spyOn(api, 'getDocuments').mockResolvedValue([mockDoc])
    vi.spyOn(api, 'getCollections').mockResolvedValue([])
    vi.spyOn(api, 'getConversations').mockResolvedValue([mockConv])
    vi.spyOn(api, 'getMessages').mockResolvedValue(mockMessages)
  })

  it('renders grounded message history and verifiable citations', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/workspace?conv=conv-1']}>
          <WorkspacePage />
        </MemoryRouter>
      </QueryClientProvider>
    )

    // User message
    await waitFor(() => {
      expect(screen.getByText('What is Grover algorithm?')).toBeInTheDocument()
    })

    // Assistant grounded answer
    expect(
      screen.getByText(/Grover algorithm provides quadratic speedup for unstructured database search/i)
    ).toBeInTheDocument()

    // Verifiable Citation badge
    expect(screen.getByText('quantum_algorithms.pdf')).toBeInTheDocument()
    expect(screen.getByText('P. 3')).toBeInTheDocument()
    expect(screen.getByText('94%')).toBeInTheDocument()
  })

  it('opens split PDF viewer on page 3 when clicking citation badge', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/workspace?conv=conv-1']}>
          <WorkspacePage />
        </MemoryRouter>
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('quantum_algorithms.pdf')).toBeInTheDocument()
    })

    // Click citation badge
    const citationBtn = screen.getByRole('button', { name: /quantum_algorithms\.pdf/i })
    fireEvent.click(citationBtn)

    // PDF viewer opens with cited excerpt and page
    await waitFor(() => {
      expect(screen.getByText(/Cited Excerpt \(Page 3\)/i)).toBeInTheDocument()
    })
  })

  it('displays error banner and does not show fabricated message when inquiry fails', async () => {
    vi.spyOn(api, 'askQuestion').mockRejectedValue(
      new Error('Backend server is offline or unreachable. Please verify the backend service is running.')
    )

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/workspace?conv=conv-1']}>
          <WorkspacePage />
        </MemoryRouter>
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('What is Grover algorithm?')).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText(/Ask a question grounded in your documents/i)
    fireEvent.change(input, { target: { value: 'What are three examples of renewable energy?' } })

    const form = input.closest('form')
    fireEvent.submit(form!)

    await waitFor(() => {
      expect(
        screen.getByText(/Backend server is offline or unreachable\. Please verify the backend service is running\./i)
      ).toBeInTheDocument()
    })

    // Must NOT display fabricated mock response or transformer paper citation
    expect(screen.queryByText(/Attention_Is_All_You_Need_Transformer_Paper\.pdf/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/\[Mock AI Response - Backend Offline\]/i)).not.toBeInTheDocument()
  })

  it('renders renewable energy answer with renewable_energy_handbook.pdf page 2 citation and no transformer citation', async () => {
    const renewableMsg: MessageItem = {
      id: 'msg-ren-1',
      conversation_id: 'conv-1',
      role: 'assistant',
      content: 'Based on the verified document evidence, three examples of renewable energy are solar, wind, and hydro power [Source 1].',
      created_at: new Date().toISOString(),
      citations: [
        {
          id: 'cit-ren-1',
          message_id: 'msg-ren-1',
          document_id: 'doc-ren-1',
          chunk_id: 'chk-ren-1',
          document_name: 'renewable_energy_handbook.pdf',
          page_number: 2,
          snippet: 'Three prominent examples of renewable energy are solar photovoltaic energy, wind power generation, and hydroelectric energy.',
          relevance_score: 0.96,
          created_at: new Date().toISOString(),
        },
      ],
    }

    vi.spyOn(api, 'getMessages').mockResolvedValue([renewableMsg])

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/workspace?conv=conv-1']}>
          <WorkspacePage />
        </MemoryRouter>
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('renewable_energy_handbook.pdf')).toBeInTheDocument()
    })
    expect(screen.getByText('P. 2')).toBeInTheDocument()
    expect(screen.getByText('96%')).toBeInTheDocument()
    expect(screen.queryByText(/Attention_Is_All_You_Need_Transformer_Paper/i)).not.toBeInTheDocument()
  })

  it('renders insufficient evidence response cleanly without citation badges', async () => {
    const insufficientMsg: MessageItem = {
      id: 'msg-insuf-1',
      conversation_id: 'conv-1',
      role: 'assistant',
      content: 'I do not have sufficient evidence in the uploaded documents to answer this question.',
      created_at: new Date().toISOString(),
      citations: [],
    }

    vi.spyOn(api, 'getMessages').mockResolvedValue([insufficientMsg])

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/workspace?conv=conv-1']}>
          <WorkspacePage />
        </MemoryRouter>
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(
        screen.getByText('I do not have sufficient evidence in the uploaded documents to answer this question.')
      ).toBeInTheDocument()
    })

    // Zero verifiable citations or badges
    expect(screen.queryByText(/Verifiable Sources & Citations:/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Attention_Is_All_You_Need/i)).not.toBeInTheDocument()
  })
})

