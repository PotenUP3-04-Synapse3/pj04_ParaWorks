'use client'

import { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'

interface SourceEvidenceDrawerProps {
  open: boolean
  onClose: () => void
  snippets: Array<{
    id: string
    text: string
    source_url: string
    source_type: string
    author?: string | null
    similarity?: number
    permission_level?: string
  }>
  title?: string
}

export function SourceEvidenceDrawer({
  open,
  onClose,
  snippets,
  title = '출처 및 근거',
}: SourceEvidenceDrawerProps) {
  const overlayRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (open) document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Overlay */}
      <div
        ref={overlayRef}
        className="absolute inset-0 bg-black/30 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <aside className="relative z-10 w-full max-w-md bg-white shadow-2xl flex flex-col h-full">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="font-semibold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="rounded p-1 hover:bg-gray-100 text-gray-500"
            aria-label="닫기"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {snippets.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-8">출처가 없습니다.</p>
          )}
          {snippets.map((s) => (
            <div key={s.id} className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm">
              <div className="flex items-start justify-between gap-2 mb-2">
                <a
                  href={s.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline truncate text-xs font-medium"
                >
                  {s.source_url}
                </a>
                <span className="shrink-0 rounded bg-gray-200 px-1.5 py-0.5 text-xs text-gray-600">
                  {s.source_type}
                </span>
              </div>
              <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{s.text}</p>
              <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                {s.author && <span>작성자: {s.author}</span>}
                {typeof s.similarity === 'number' && (
                  <span>유사도: {Math.round(s.similarity * 100)}%</span>
                )}
                {s.permission_level && <span className="capitalize">{s.permission_level}</span>}
              </div>
            </div>
          ))}
        </div>
      </aside>
    </div>
  )
}
