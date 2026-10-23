import React, { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/apiClient'
import { useQueryClient } from '@tanstack/react-query'
import { UploadCloud, FileText, AlertCircle, X } from 'lucide-react'
import { formatBytes } from '@/lib/utils'

interface UploadModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
}

export function UploadModal({ isOpen, onClose, onSuccess }: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const validateAndSetFile = (selectedFile: File) => {
    setError(null)
    if (!selectedFile.name.toLowerCase().endsWith('.pdf') && selectedFile.type !== 'application/pdf') {
      setError('Only PDF documents (.pdf) are supported.')
      return
    }
    const maxBytes = 25 * 1024 * 1024 // 25 MB
    if (selectedFile.size > maxBytes) {
      setError(`File size exceeds 25 MB limit (${formatBytes(selectedFile.size)}).`)
      return
    }
    setFile(selectedFile)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) return
    setIsUploading(true)
    setError(null)
    setUploadProgress(20)

    try {
      const interval = setInterval(() => {
        setUploadProgress((prev) => (prev < 90 ? prev + 25 : prev))
      }, 200)

      await api.uploadDocument(file)
      clearInterval(interval)
      setUploadProgress(100)

      // Invalidate React Query caches
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })

      setTimeout(() => {
        setIsUploading(false)
        setFile(null)
        setUploadProgress(0)
        onClose()
        if (onSuccess) onSuccess()
      }, 600)
    } catch (err: any) {
      setIsUploading(false)
      setError(err.message || 'Failed to upload document. Please check the file and try again.')
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && !isUploading && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Upload Research Document</DialogTitle>
          <DialogDescription>
            Upload a PDF document to extract text, calculate vector embeddings, and enable grounded Q&A.
          </DialogDescription>
        </DialogHeader>

        <div className="py-2">
          {!file ? (
            <div
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                dragActive
                  ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-950/20'
                  : 'border-gray-200 dark:border-gray-800 hover:border-blue-400 dark:hover:border-blue-600 bg-gray-50/50 dark:bg-gray-800/20'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                onChange={handleFileChange}
              />
              <div className="mx-auto w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center text-blue-600 dark:text-blue-400 mb-3">
                <UploadCloud className="h-6 w-6" />
              </div>
              <p className="text-sm font-medium text-foreground">
                Click to browse or drag and drop your PDF
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Standard PDF files up to 25 MB
              </p>
            </div>
          ) : (
            <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/40 flex items-center justify-between">
              <div className="flex items-center space-x-3 overflow-hidden">
                <div className="h-10 w-10 shrink-0 rounded-lg bg-red-100 dark:bg-red-950/40 text-red-600 flex items-center justify-center">
                  <FileText className="h-5 w-5" />
                </div>
                <div className="overflow-hidden">
                  <p className="text-sm font-medium text-foreground truncate max-w-[260px]">
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {formatBytes(file.size)}
                  </p>
                </div>
              </div>
              {!isUploading && (
                <button
                  onClick={() => setFile(null)}
                  className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400 hover:text-foreground cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          )}

          {isUploading && (
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-xs font-medium">
                <span className="text-gray-600 dark:text-gray-300">
                  {uploadProgress === 100 ? 'Indexing complete' : 'Uploading & verifying structure...'}
                </span>
                <span className="text-blue-600 dark:text-blue-400">{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-blue-600 h-2 transition-all duration-300 rounded-full"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {error && (
            <div className="mt-3 p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 flex flex-col space-y-1.5 text-red-700 dark:text-red-300 text-xs">
              <div className="flex items-start space-x-2">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
              {error.toLowerCase().includes('authentication') && (
                <div className="pl-6">
                  <Link
                    to="/login"
                    onClick={onClose}
                    className="text-blue-600 dark:text-blue-400 font-medium hover:underline inline-flex items-center"
                  >
                    Click here to sign in &rarr;
                  </Link>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isUploading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleUpload}
            disabled={!file || isUploading}
            isLoading={isUploading}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            {isUploading ? 'Processing...' : 'Upload & Process'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
