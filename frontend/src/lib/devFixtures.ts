import type {
  User,
  DocumentItem,
  CollectionItem,
  ConversationItem,
  MessageItem,
  DashboardStats,
} from '@/types'

export const DEV_CURRENT_USER: User = {
  id: 'usr-92847120-f13b-4899-b1d5-86f7842c12a1',
  email: 'researcher@example.com',
  full_name: 'Dr. Jane Holloway',
  is_active: true,
  created_at: new Date(Date.now() - 30 * 86400000).toISOString(),
}

export const DEV_DOCUMENTS: DocumentItem[] = [
  {
    id: 'doc-a1111111-2222-3333-4444-555555555555',
    user_id: DEV_CURRENT_USER.id,
    filename: 'Attention_Is_All_You_Need_Transformer_Paper.pdf',
    file_size_bytes: 2215840,
    mime_type: 'application/pdf',
    page_count: 15,
    processing_status: 'READY',
    error_message: null,
    checksum_sha256: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
    created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 86400000).toISOString(),
  },
  {
    id: 'doc-b2222222-3333-4444-5555-666666666666',
    user_id: DEV_CURRENT_USER.id,
    filename: 'RAG_Architecture_and_Retrieval_Benchmark_2025.pdf',
    file_size_bytes: 4892110,
    mime_type: 'application/pdf',
    page_count: 28,
    processing_status: 'READY',
    error_message: null,
    checksum_sha256: '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
    created_at: new Date(Date.now() - 5 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 5 * 86400000).toISOString(),
  },
  {
    id: 'doc-c3333333-4444-5555-6666-777777777777',
    user_id: DEV_CURRENT_USER.id,
    filename: 'Multi_Agent_Autonomous_Systems_Whitepaper.pdf',
    file_size_bytes: 1450230,
    mime_type: 'application/pdf',
    page_count: 12,
    processing_status: 'EMBEDDING',
    error_message: null,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    updated_at: new Date(Date.now() - 600000).toISOString(),
  },
  {
    id: 'doc-d4444444-5555-6666-7777-888888888888',
    user_id: DEV_CURRENT_USER.id,
    filename: 'Scanned_Laboratory_Notes_Historical_1984.pdf',
    file_size_bytes: 8710290,
    mime_type: 'application/pdf',
    page_count: 6,
    processing_status: 'OCR_REQUIRED',
    error_message: 'No digital text found. Document consists of raster images and requires OCR processing.',
    created_at: new Date(Date.now() - 12 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 12 * 86400000).toISOString(),
  },
]

export const DEV_COLLECTIONS: CollectionItem[] = [
  {
    id: 'col-11111111-aaaa-bbbb-cccc-dddddddddddd',
    user_id: DEV_CURRENT_USER.id,
    name: 'Foundation Models & Transformers',
    description: 'Seminal papers on deep learning architectures, attention mechanisms, and scaling laws.',
    document_count: 2,
    created_at: new Date(Date.now() - 10 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 86400000).toISOString(),
  },
  {
    id: 'col-22222222-bbbb-cccc-dddd-eeeeeeeeeeee',
    user_id: DEV_CURRENT_USER.id,
    name: 'Retrieval Augmented Generation',
    description: 'Dense passage retrieval, vector databases, reranking, and citation grounding benchmarks.',
    document_count: 1,
    created_at: new Date(Date.now() - 7 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 1 * 86400000).toISOString(),
  },
]

export const DEV_CONVERSATIONS: ConversationItem[] = [
  {
    id: 'conv-11111111-9999-8888-7777-666666666666',
    user_id: DEV_CURRENT_USER.id,
    title: 'Multi-Head Attention vs Self-Attention Mechanics',
    collection_id: DEV_COLLECTIONS[0].id,
    collection_name: DEV_COLLECTIONS[0].name,
    message_count: 4,
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 1800000).toISOString(),
  },
  {
    id: 'conv-22222222-8888-7777-6666-555555555555',
    user_id: DEV_CURRENT_USER.id,
    title: 'Vector Indexing and Latency Bounds in RAG',
    collection_id: DEV_COLLECTIONS[1].id,
    collection_name: DEV_COLLECTIONS[1].name,
    message_count: 2,
    created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 86400000).toISOString(),
  },
]

export const DEV_MESSAGES: Record<string, MessageItem[]> = {
  [DEV_CONVERSATIONS[0].id]: [
    {
      id: 'msg-01',
      conversation_id: DEV_CONVERSATIONS[0].id,
      role: 'user',
      content: 'How does Multi-Head Attention differ from single-head dot-product attention in terms of representation subspaces?',
      created_at: new Date(Date.now() - 1800000).toISOString(),
    },
    {
      id: 'msg-02',
      conversation_id: DEV_CONVERSATIONS[0].id,
      role: 'assistant',
      content: `According to Section 3.2.2 of the Transformer paper, instead of performing a single attention function with $d_{model}$-dimensional queries, keys, and values, the authors found it beneficial to linearly project the queries, keys, and values $h$ times with different, learned linear projections to $d_k$, $d_k$, and $d_v$ dimensions respectively.\n\nMulti-head attention allows the model to jointly attend to information from different representation subspaces at different positions. With a single attention head, averaging inhibits this capacity.`,
      created_at: new Date(Date.now() - 1750000).toISOString(),
      citations: [
        {
          id: 'cit-01',
          message_id: 'msg-02',
          document_id: DEV_DOCUMENTS[0].id,
          chunk_id: 'chk-01',
          document_name: DEV_DOCUMENTS[0].filename,
          page_number: 4,
          snippet: 'Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions. With a single attention head, averaging inhibits this.',
          relevance_score: 0.94,
          created_at: new Date(Date.now() - 1750000).toISOString(),
        },
        {
          id: 'cit-02',
          message_id: 'msg-02',
          document_id: DEV_DOCUMENTS[0].id,
          chunk_id: 'chk-02',
          document_name: DEV_DOCUMENTS[0].filename,
          page_number: 5,
          snippet: 'In this work we employ h = 8 parallel attention layers, or heads. For each of these we use dk = dv = dmodel/h = 64.',
          relevance_score: 0.88,
          created_at: new Date(Date.now() - 1750000).toISOString(),
        },
      ],
    },
    {
      id: 'msg-03',
      conversation_id: DEV_CONVERSATIONS[0].id,
      role: 'user',
      content: 'What are the computational complexity differences per layer compared to recurrent layers?',
      created_at: new Date(Date.now() - 1200000).toISOString(),
    },
    {
      id: 'msg-04',
      conversation_id: DEV_CONVERSATIONS[0].id,
      role: 'assistant',
      content: `Table 1 compares self-attention layers to recurrent and convolutional layers across three dimensions:\n\n1. **Complexity per layer**: A self-attention layer connects all positions with $O(n^2 \\cdot d)$ operations, whereas recurrent layers require $O(n \\cdot d^2)$ operations.\n2. **Sequential operations**: Self-attention requires $O(1)$ sequential operations, enabling maximum parallelization, whereas recurrent layers require $O(n)$ sequential operations.\n3. **Maximum path length**: Self-attention has a path length of $O(1)$ between any two positions, whereas recurrent networks have $O(n)$, making long-range dependencies substantially easier to learn.`,
      created_at: new Date(Date.now() - 1150000).toISOString(),
      citations: [
        {
          id: 'cit-03',
          message_id: 'msg-04',
          document_id: DEV_DOCUMENTS[0].id,
          chunk_id: 'chk-03',
          document_name: DEV_DOCUMENTS[0].filename,
          page_number: 6,
          snippet: 'Table 1: Maximum path lengths, per-layer complexity and minimum number of sequential operations for different layer types. n is the sequence length, d is the representation dimension.',
          relevance_score: 0.96,
          created_at: new Date(Date.now() - 1150000).toISOString(),
        },
      ],
    },
  ],
  [DEV_CONVERSATIONS[1].id]: [
    {
      id: 'msg-11',
      conversation_id: DEV_CONVERSATIONS[1].id,
      role: 'user',
      content: 'What retrieval latency trade-offs are reported for HNSW vs IVFFlat indexes in pgvector?',
      created_at: new Date(Date.now() - 7200000).toISOString(),
    },
    {
      id: 'msg-12',
      conversation_id: DEV_CONVERSATIONS[1].id,
      role: 'assistant',
      content: `The benchmark documents that HNSW (Hierarchical Navigable Small World) indexes provide sub-5ms query latency at 99% recall for 1536-dimensional vectors, but require more memory and longer build times. Conversely, IVFFlat requires an initial training step with lists and yields higher throughput at the cost of lower recall under dynamic insertions.`,
      created_at: new Date(Date.now() - 7150000).toISOString(),
      citations: [
        {
          id: 'cit-11',
          message_id: 'msg-12',
          document_id: DEV_DOCUMENTS[1].id,
          chunk_id: 'chk-11',
          document_name: DEV_DOCUMENTS[1].filename,
          page_number: 14,
          snippet: 'HNSW maintains high recall (>98.5%) with p95 query times under 4.2ms across 500,000 embedded chunks. Memory footprint is approximately 1.4x larger than unindexed vectors.',
          relevance_score: 0.91,
          created_at: new Date(Date.now() - 7150000).toISOString(),
        },
      ],
    },
  ],
}

export const DEV_STATS: DashboardStats = {
  total_documents: DEV_DOCUMENTS.length,
  total_collections: DEV_COLLECTIONS.length,
  total_conversations: DEV_CONVERSATIONS.length,
  total_pages_indexed: DEV_DOCUMENTS.reduce((acc, d) => acc + (d.processing_status === 'READY' ? d.page_count : 0), 0),
}
