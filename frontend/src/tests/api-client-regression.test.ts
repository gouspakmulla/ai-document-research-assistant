import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { api, devMockStorage, getNormalizedApiBaseUrl } from '@/lib/apiClient'

describe('ApiClient Backend Offline & Error Handling Regression Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    devMockStorage.reset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('askQuestion throws honest offline error on network failure instead of returning fake mock response', async () => {
    // Mock network failure (Failed to fetch)
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(
      api.askQuestion({
        question: 'What are three examples of renewable energy?',
      })
    ).rejects.toThrow(/Backend server is offline or unreachable/i)

    // devMockStorage must NOT have messages created
    expect(devMockStorage.getMessages('conv-1')).toEqual([])
  })

  it('askQuestion does not return fabricated Attention_Is_All_You_Need citations on server 500', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ detail: 'Database connection failed during vector retrieval' }),
    } as Response)

    await expect(
      api.askQuestion({
        question: 'What are three examples of renewable energy?',
      })
    ).rejects.toThrow('Database connection failed during vector retrieval')
  })

  it('askQuestion rejects with 401 on unauthenticated request and resets auth', async () => {
    const unauthorizedListener = vi.fn()
    window.addEventListener('auth:unauthorized', unauthorizedListener)

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: 'Authentication session required.' }),
    } as Response)

    await expect(
      api.askQuestion({
        question: 'What are three examples of renewable energy?',
      })
    ).rejects.toThrow('Authentication session required.')

    expect(unauthorizedListener).toHaveBeenCalled()
    window.removeEventListener('auth:unauthorized', unauthorizedListener)
  })

  it('uploadDocument rejects with clear error on network failure instead of creating fake mock document', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

    const dummyFile = new File(['%PDF-1.4 renewable energy content'], 'renewable_energy.pdf', {
      type: 'application/pdf',
    })

    await expect(api.uploadDocument(dummyFile)).rejects.toThrow(/Backend server is offline or unreachable/i)

    // devMockStorage must NOT contain fake documents
    expect(devMockStorage.getDocuments()).toEqual([])
  })

  it('getDocuments returns empty array and never exposes fabricated Attention_Is_All_You_Need fixture', async () => {
    // When backend returns empty list
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
    } as Response)

    const docs = await api.getDocuments()
    expect(docs).toEqual([])
    expect(docs.find((d) => d.filename.includes('Attention_Is_All_You_Need'))).toBeUndefined()
  })

  it('getDocuments returns empty array on network failure without falling back to fake dev fixtures', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

    const docs = await api.getDocuments()
    expect(docs).toEqual([])
    expect(docs.find((d) => d.filename.includes('Attention_Is_All_You_Need'))).toBeUndefined()
  })

  it('normalizes VITE_API_URL so host without /api/v1 automatically appends /api/v1', () => {
    expect(getNormalizedApiBaseUrl('https://ai-document-research-assistant.onrender.com')).toBe(
      'https://ai-document-research-assistant.onrender.com/api/v1'
    )
    expect(getNormalizedApiBaseUrl('https://ai-document-research-assistant.onrender.com/')).toBe(
      'https://ai-document-research-assistant.onrender.com/api/v1'
    )
    expect(getNormalizedApiBaseUrl('https://ai-document-research-assistant.onrender.com/api/v1')).toBe(
      'https://ai-document-research-assistant.onrender.com/api/v1'
    )
    expect(getNormalizedApiBaseUrl('/api/v1')).toBe('/api/v1')
    expect(getNormalizedApiBaseUrl('')).toBe('/api/v1')
  })
})
