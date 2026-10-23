import { describe, it, expect } from 'vitest'
import { formatBytes, formatDate, cn } from '@/lib/utils'

describe('Utility Functions', () => {
  it('formats bytes into human-readable strings correctly', () => {
    expect(formatBytes(0)).toBe('0 Bytes')
    expect(formatBytes(1024)).toBe('1 KB')
    expect(formatBytes(1024 * 1024 * 5)).toBe('5 MB')
    expect(formatBytes(2215840)).toBe('2.1 MB')
  })

  it('formats date strings reliably', () => {
    const iso = '2026-03-15T12:00:00Z'
    const formatted = formatDate(iso)
    expect(formatted).toContain('2026')
    expect(formatted).toContain('Mar')
  })

  it('merges tailwind class names properly using cn', () => {
    const merged = cn('px-4 py-2', 'px-6', { 'text-red-500': true, 'hidden': false })
    expect(merged).toContain('px-6')
    expect(merged).toContain('py-2')
    expect(merged).toContain('text-red-500')
    expect(merged).not.toContain('px-4')
  })
})
