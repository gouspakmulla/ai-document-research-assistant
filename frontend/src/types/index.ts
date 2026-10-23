export type ProcessingStatus =
  | 'PENDING'
  | 'EXTRACTING'
  | 'CHUNKING'
  | 'EMBEDDING'
  | 'READY'
  | 'FAILED'
  | 'OCR_REQUIRED'

export interface User {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  created_at: string
}

export interface DocumentItem {
  id: string
  user_id: string
  filename: string
  file_size_bytes: number
  mime_type: string
  page_count: number
  processing_status: ProcessingStatus
  error_message: string | null
  checksum_sha256?: string | null
  created_at: string
  updated_at: string
}

export interface CollectionItem {
  id: string
  user_id: string
  name: string
  description: string | null
  document_count: number
  documents?: DocumentItem[]
  created_at: string
  updated_at: string
}

export interface MessageCitation {
  id: string
  message_id: string
  document_id: string
  chunk_id: string | null
  document_name: string
  page_number: number
  snippet: string
  relevance_score: number
  created_at: string
}

export interface MessageItem {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  citations?: MessageCitation[]
}

export interface ConversationItem {
  id: string
  user_id: string
  title: string
  collection_id: string | null
  collection_name?: string | null
  message_count: number
  created_at: string
  updated_at: string
}

export interface DashboardStats {
  total_documents: number
  total_collections: number
  total_conversations: number
  total_pages_indexed: number
}

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  email: string
  password: string
  full_name?: string
}

export interface AskQuestionPayload {
  question: string
  conversation_id?: string
  document_id?: string
  collection_id?: string
}

export interface AskQuestionResponse {
  conversation_id: string
  user_message: MessageItem
  assistant_message: MessageItem
}

export interface ApiErrorResponse {
  detail: string | { msg: string; loc: string[] }[]
}
