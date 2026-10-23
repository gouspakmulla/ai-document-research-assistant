import { ProcessingStatus } from '@/types'
import { Badge } from './badge'
import { CheckCircle2, Clock, Loader2, AlertCircle, ScanEye } from 'lucide-react'

interface StatusBadgeProps {
  status: ProcessingStatus
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  switch (status) {
    case 'READY':
      return (
        <Badge variant="success" className={className}>
          <CheckCircle2 className="mr-1 h-3 w-3" />
          Ready
        </Badge>
      )
    case 'EXTRACTING':
      return (
        <Badge variant="secondary" className={`animate-pulse ${className}`}>
          <Loader2 className="mr-1 h-3 w-3 animate-spin text-blue-500" />
          Extracting text...
        </Badge>
      )
    case 'CHUNKING':
      return (
        <Badge variant="secondary" className={`animate-pulse ${className}`}>
          <Loader2 className="mr-1 h-3 w-3 animate-spin text-indigo-500" />
          Chunking...
        </Badge>
      )
    case 'EMBEDDING':
      return (
        <Badge variant="secondary" className={`animate-pulse ${className}`}>
          <Loader2 className="mr-1 h-3 w-3 animate-spin text-purple-500" />
          Embedding vectors...
        </Badge>
      )
    case 'PENDING':
      return (
        <Badge variant="secondary" className={className}>
          <Clock className="mr-1 h-3 w-3 text-gray-500" />
          Queued
        </Badge>
      )
    case 'OCR_REQUIRED':
      return (
        <Badge variant="warning" className={className}>
          <ScanEye className="mr-1 h-3 w-3" />
          OCR Required
        </Badge>
      )
    case 'FAILED':
      return (
        <Badge variant="destructive" className={className}>
          <AlertCircle className="mr-1 h-3 w-3" />
          Failed
        </Badge>
      )
    default:
      return <Badge variant="secondary">{status}</Badge>
  }
}
