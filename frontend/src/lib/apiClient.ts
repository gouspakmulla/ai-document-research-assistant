import type {
  User,
  DocumentItem,
  CollectionItem,
  ConversationItem,
  MessageItem,
  DashboardStats,
  LoginPayload,
  RegisterPayload,
  AskQuestionPayload,
  AskQuestionResponse,
} from '@/types'

const rawApiUrl = (import.meta.env.VITE_API_URL as string | undefined) || '/api/v1'

export function getNormalizedApiBaseUrl(raw: string): string {
  const trimmed = raw.trim().replace(/\/+$/, '')
  // If user provided host/origin without path (e.g. "https://my-backend.onrender.com"), append /api/v1
  if (/^https?:\/\/[^/]+$/.test(trimmed)) {
    return `${trimmed}/api/v1`
  }
  return trimmed || '/api/v1'
}

const API_BASE_URL = getNormalizedApiBaseUrl(rawApiUrl)

// Lightweight in-memory storage for test isolation and session state
class DevMockStorage {
  private user: User | null = null
  private documents: DocumentItem[] = []
  private collections: CollectionItem[] = []
  private conversations: ConversationItem[] = []
  private messages: Record<string, MessageItem[]> = {}

  getUser(): User | null {
    return this.user
  }
  setUser(u: User | null) {
    this.user = u
  }

  getDocuments(): DocumentItem[] {
    return this.documents
  }
  addDocument(doc: DocumentItem) {
    this.documents.unshift(doc)
  }
  deleteDocument(id: string) {
    this.documents = this.documents.filter((d) => d.id !== id)
  }
  renameDocument(id: string, name: string) {
    const doc = this.documents.find((d) => d.id === id)
    if (doc) doc.filename = name
  }

  getCollections(): CollectionItem[] {
    return this.collections
  }
  createCollection(name: string, description?: string): CollectionItem {
    const newCol: CollectionItem = {
      id: `col-${Date.now()}`,
      user_id: this.user?.id || 'usr-1',
      name,
      description: description || null,
      document_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    this.collections.unshift(newCol)
    return newCol
  }
  deleteCollection(id: string) {
    this.collections = this.collections.filter((c) => c.id !== id)
  }

  getConversations(): ConversationItem[] {
    return this.conversations
  }
  createConversation(title: string, collection_id?: string): ConversationItem {
    const newConv: ConversationItem = {
      id: `conv-${Date.now()}`,
      user_id: this.user?.id || 'usr-1',
      title,
      collection_id: collection_id || null,
      message_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    this.conversations.unshift(newConv)
    this.messages[newConv.id] = []
    return newConv
  }
  deleteConversation(id: string) {
    this.conversations = this.conversations.filter((c) => c.id !== id)
    delete this.messages[id]
  }

  getMessages(conversationId: string): MessageItem[] {
    return this.messages[conversationId] || []
  }
  addMessage(conversationId: string, message: MessageItem) {
    if (!this.messages[conversationId]) {
      this.messages[conversationId] = []
    }
    this.messages[conversationId].push(message)
    const conv = this.conversations.find((c) => c.id === conversationId)
    if (conv) {
      conv.message_count = this.messages[conversationId].length
      conv.updated_at = new Date().toISOString()
    }
  }

  getStats(): DashboardStats {
    return {
      total_documents: this.documents.length,
      total_collections: this.collections.length,
      total_conversations: this.conversations.length,
      total_pages_indexed: this.documents.reduce(
        (acc, d) => acc + (d.processing_status === 'READY' ? d.page_count : 0),
        0
      ),
    }
  }

  reset() {
    this.user = null
    this.documents = []
    this.collections = []
    this.conversations = []
    this.messages = {}
  }
}

export const devMockStorage = new DevMockStorage()

const TOKEN_STORAGE_KEY = 'doc_assistant_token'

class ApiClient {
  private csrfToken: string | null = null
  private authToken: string | null = null
  public isDevFallbackActive = false

  constructor() {
    if (typeof window !== 'undefined') {
      try {
        this.authToken = localStorage.getItem(TOKEN_STORAGE_KEY)
      } catch {
        // ignore
      }
    }
  }

  getAuthToken(): string | null {
    if (!this.authToken && typeof window !== 'undefined') {
      try {
        this.authToken = localStorage.getItem(TOKEN_STORAGE_KEY)
      } catch {
        // ignore
      }
    }
    return this.authToken
  }

  setAuthToken(token: string | null) {
    this.authToken = token
    if (typeof window !== 'undefined') {
      try {
        if (token) {
          localStorage.setItem(TOKEN_STORAGE_KEY, token)
        } else {
          localStorage.removeItem(TOKEN_STORAGE_KEY)
        }
      } catch {
        // ignore
      }
    }
  }

  private buildUrl(path: string, params?: Record<string, string>): string {
    const isAbsolute = API_BASE_URL.startsWith('http://') || API_BASE_URL.startsWith('https://')
    const origin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5173'
    const fullBase = isAbsolute ? API_BASE_URL : `${origin}${API_BASE_URL.startsWith('/') ? '' : '/'}${API_BASE_URL}`
    const normalizedBase = fullBase.replace(/\/+$/, '')
    const cleanPath = path.startsWith('/') ? path : `/${path}`
    const url = new URL(`${normalizedBase}${cleanPath}`)
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined && v !== null && v !== '') {
          url.searchParams.set(k, v)
        }
      }
    }
    return url.toString()
  }

  private handleUnauthorized() {
    this.csrfToken = null
    this.setAuthToken(null)
    devMockStorage.setUser(null)
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('auth:unauthorized'))
    }
  }

  private handleNetworkError(e: unknown, customMessage?: string): never {
    if (e instanceof Error && (e.name === 'TypeError' || e.message === 'Failed to fetch')) {
      throw new Error(
        customMessage || 'Backend server is offline or unreachable. Please verify the backend service is running.'
      )
    }
    throw e
  }

  async fetchCsrfToken(): Promise<string | null> {
    try {
      const headers: Record<string, string> = {}
      const token = this.getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      const res = await fetch(this.buildUrl('/auth/csrf'), {
        headers,
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        this.csrfToken = data.csrf_token
        return this.csrfToken
      }
      if (res.status === 401 || res.status === 403) {
        this.csrfToken = null
      }
    } catch {
      // Backend not running or auth required
    }
    return null
  }

  private async getHeaders(customHeaders: Record<string, string> = {}, requireCsrf = false): Promise<HeadersInit> {
    const headers: Record<string, string> = {
      ...customHeaders,
    }
    const token = this.getAuthToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    // Only fetch/attach CSRF token if mutating request requires it AND no Bearer token is present
    if (requireCsrf && !token) {
      if (!this.csrfToken) {
        await this.fetchCsrfToken()
      }
      if (this.csrfToken) {
        headers['X-CSRF-Token'] = this.csrfToken
      }
    }
    return headers
  }

  // --- Auth endpoints ---
  async me(): Promise<User | null> {
    try {
      const res = await fetch(this.buildUrl('/auth/me'), {
        headers: await this.getHeaders(),
        credentials: 'include',
      })
      if (res.ok) {
        const u = (await res.json()) as User
        const headerToken = res.headers?.get ? res.headers.get('Authorization')?.replace(/^Bearer\s+/i, '') : null
        const effectiveToken = u.token || headerToken || null
        if (effectiveToken) {
          this.setAuthToken(effectiveToken)
          u.token = effectiveToken
        }
        devMockStorage.setUser(u)
        return u
      }
      if (res.status === 401 || res.status === 403) {
        this.handleUnauthorized()
        return null
      }
    } catch {
      this.isDevFallbackActive = true
    }
    return null
  }

  async login(payload: LoginPayload): Promise<User> {
    try {
      const res = await fetch(this.buildUrl('/auth/login'), {
        method: 'POST',
        headers: await this.getHeaders({ 'Content-Type': 'application/json' }),
        credentials: 'include',
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        const u = (await res.json()) as User
        const headerToken = res.headers?.get ? res.headers.get('Authorization')?.replace(/^Bearer\s+/i, '') : null
        const effectiveToken = u.token || headerToken || null
        if (effectiveToken) {
          this.setAuthToken(effectiveToken)
          u.token = effectiveToken
        }
        devMockStorage.setUser(u)
        return u
      }
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Login failed')
    } catch (e: any) {
      this.handleNetworkError(e)
    }
  }

  async register(payload: RegisterPayload): Promise<User> {
    try {
      const res = await fetch(this.buildUrl('/auth/register'), {
        method: 'POST',
        headers: await this.getHeaders({ 'Content-Type': 'application/json' }),
        credentials: 'include',
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        const u = (await res.json()) as User
        const headerToken = res.headers?.get ? res.headers.get('Authorization')?.replace(/^Bearer\s+/i, '') : null
        const effectiveToken = u.token || headerToken || null
        if (effectiveToken) {
          this.setAuthToken(effectiveToken)
          u.token = effectiveToken
        }
        devMockStorage.setUser(u)
        return u
      }
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Registration failed')
    } catch (e: any) {
      this.handleNetworkError(e)
    }
  }

  async logout(): Promise<void> {
    try {
      await fetch(this.buildUrl('/auth/logout'), {
        method: 'POST',
        headers: await this.getHeaders(),
        credentials: 'include',
      })
    } catch {
      // ignore
    }
    this.handleUnauthorized()
  }

  // --- Document endpoints ---
  async getDocuments(search?: string): Promise<DocumentItem[]> {
    try {
      const url = this.buildUrl('/documents', search ? { search } : undefined)
      const res = await fetch(url, {
        headers: await this.getHeaders(),
        credentials: 'include',
      })
      if (res.ok) return await res.json()
      if (res.status === 401 || res.status === 403) {
        this.handleUnauthorized()
        return []
      }
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `Failed to fetch documents (${res.status})`)
    } catch (e: any) {
      if (e.message && e.message !== 'Failed to fetch' && !e.message.includes('offline or unreachable')) {
        throw e
      }
      return []
    }
  }

  async getDocument(id: string): Promise<DocumentItem> {
    try {
      const res = await fetch(this.buildUrl(`/documents/${id}`), {
        headers: await this.getHeaders(),
        credentials: 'include',
      })
      if (res.ok) return await res.json()
      if (res.status === 401 || res.status === 403) {
        this.handleUnauthorized()
      }
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `Document ${id} not found`)
    } catch (e: any) {
      this.handleNetworkError(e)
    }
  }

  getDocumentContentUrl(id: string): string {
    const token = this.getAuthToken()
    return this.buildUrl(`/documents/${id}/content`, token ? { token } : undefined)
  }

  async getDocumentChunks(id: string): Promise<any[]> {
    try {
      const res = await fetch(this.buildUrl(`/documents/${id}/chunks`), {
        headers: await this.getHeaders(),
        credentials: 'include',
      })
      if (res.ok) return await res.json()
      if (res.status === 401 || res.status === 403) {
        this.handleUnauthorized()
      }
      return []
    } catch {
      return []
    }
  }

  async uploadDocument(file: File): Promise<DocumentItem> {
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch(this.buildUrl('/documents/upload'), {
        method: 'POST',
        headers: await this.getHeaders(),
        credentials: 'include',
        body: formData,
      })
      if (res.ok) return await res.json()
      if (res.status === 401) {
        this.handleUnauthorized()
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Authentication session required.')
      }
      const err = await res.json().catch(() => ({}))
      if (err.detail) throw new Error(err.detail)
      throw new Error(`Upload failed (${res.status})`)
    } catch (e: any) {
      this.handleNetworkError(e, 'Backend server is offline or unreachable. Upload failed.')
    }
  }

  async deleteDocument(id: string): Promise<void> {
    try {
      const res = await fetch(this.buildUrl(`/documents/${id}`), {
        method: 'DELETE',
        headers: await this.getHeaders(),
        credentials: 'include',
      })
      if (res.ok) return
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `Failed to delete document (${res.status})`)
    } catch (e: any) {
      this.handleNetworkError(e)
    }
  }

  async renameDocument(id: string, name: string): Promise<void> {
    try {
      const res = await fetch(this.buildUrl(`/documents/${id}/rename`), {
        method: 'PATCH',
        headers: await this.getHeaders({ 'Content-Type': 'application/json' }),
        credentials: 'include',
        body: JSON.stringify({ filename: name }),
      })
      if (res.ok) return
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `Failed to rename document (${res.status})`)
    } catch (e: any) {
      this.handleNetworkError(e)
    }
  }

  // --- Collection endpoints ---
  async getCollections(): Promise<CollectionItem[]> {
    try {
      const res = await fetch(this.buildUrl('/collections'), {
        headers: await this.getHeaders(),
        credentials: 'include',
      })
      if (res.ok) return await res.json()
      if (res.status === 401 || res.status === 403) {
        this.handleUnauthorized()
        return []
      }
    } catch {
      // ignore
    }
    return []
  }

  async createCollection(name: string, description?: string): Promise<CollectionItem> {
    try {
      const res = await fetch(this.buildUrl('/collections'), {
        method: 'POST',
        headers: await this.getHeaders({ 'Content-Type': 'application/json' }),
        credentials: 'include',
        body: JSON.stringify({ name, description }),
      })
      if (res.ok) return await res.json()
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to create collection')
    } catch (e: any) {
      this.handleNetworkError(e)
    }
  }

  async deleteCollection(id: string): Promise<void> {
    try {
      const res = await fetch(this.buildUrl(`/collections/${id}`), {
        method: 'DELETE',
        headers: await this.getHeaders(),
        credentials: 'include',
      })
      if (res.ok) return
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to delete collection')
    } catch (e: any) {
      this.handleNetworkError(e)
    }
  }

  // --- Conversation & Chat endpoints ---
  async getConversations(): Promise<ConversationItem[]> {
    try {
      const res = await fetch(this.buildUrl('/chat/conversations'), {
        headers: await this.getHeaders(),
        credentials: 'include',
      })
      if (res.ok) return await res.json()
      if (res.status === 401 || res.status === 403) {
        this.handleUnauthorized()
        return []
      }
    } catch {
      // ignore
    }
    return []
  }

  async createConversation(title: string, collectionId?: string): Promise<ConversationItem> {
    try {
      const res = await fetch(this.buildUrl('/chat/conversations'), {
        method: 'POST',
        headers: await this.getHeaders({ 'Content-Type': 'application/json' }),
        credentials: 'include',
        body: JSON.stringify({ title, collection_id: collectionId }),
      })
      if (res.ok) return await res.json()
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to create conversation')
    } catch (e: any) {
      this.handleNetworkError(e)
    }
  }

  async deleteConversation(id: string): Promise<void> {
    try {
      const res = await fetch(this.buildUrl(`/chat/conversations/${id}`), {
        method: 'DELETE',
        headers: await this.getHeaders(),
        credentials: 'include',
      })
      if (res.ok) return
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to delete conversation')
    } catch (e: any) {
      this.handleNetworkError(e)
    }
  }

  async getMessages(conversationId: string): Promise<MessageItem[]> {
    try {
      const res = await fetch(this.buildUrl(`/chat/conversations/${conversationId}/messages`), {
        headers: await this.getHeaders(),
        credentials: 'include',
      })
      if (res.ok) return await res.json()
      if (res.status === 401 || res.status === 403) {
        this.handleUnauthorized()
        return []
      }
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to retrieve messages')
    } catch (e: any) {
      this.handleNetworkError(e)
    }
  }

  async askQuestion(payload: AskQuestionPayload): Promise<AskQuestionResponse> {
    try {
      const res = await fetch(this.buildUrl('/chat/ask'), {
        method: 'POST',
        headers: await this.getHeaders({ 'Content-Type': 'application/json' }),
        credentials: 'include',
        body: JSON.stringify(payload),
      })
      if (res.ok) return await res.json()

      const err = await res.json().catch(() => ({}))
      if (res.status === 401) {
        this.handleUnauthorized()
        throw new Error(err.detail || 'Authentication required. Please sign in to ask questions.')
      }
      if (res.status === 404) {
        throw new Error(err.detail || 'The specified document or conversation was not found.')
      }
      if (res.status === 503) {
        throw new Error(err.detail || 'AI research service is currently unavailable.')
      }
      throw new Error(err.detail || `Question inquiry failed (${res.status})`)
    } catch (e: any) {
      this.handleNetworkError(e)
    }
  }

  // --- Semantic Search endpoint ---
  async semanticSearch(payload: {
    query: string
    document_id?: string
    collection_id?: string
    top_k?: number
    similarity_threshold?: number
  }): Promise<{ query: string; total_results: number; results: any[] }> {
    try {
      const res = await fetch(this.buildUrl('/search'), {
        method: 'POST',
        headers: await this.getHeaders({ 'Content-Type': 'application/json' }),
        credentials: 'include',
        body: JSON.stringify(payload),
      })
      if (res.ok) return await res.json()
    } catch {
      // ignore
    }
    return {
      query: payload.query,
      total_results: 0,
      results: [],
    }
  }

  // --- Stats endpoint ---
  async getStats(): Promise<DashboardStats> {
    try {
      const res = await fetch(this.buildUrl('/stats'), {
        headers: await this.getHeaders(),
        credentials: 'include',
      })
      if (res.ok) return await res.json()
    } catch {
      // ignore
    }
    return {
      total_documents: 0,
      total_collections: 0,
      total_conversations: 0,
      total_pages_indexed: 0,
    }
  }
}

export const api = new ApiClient()
