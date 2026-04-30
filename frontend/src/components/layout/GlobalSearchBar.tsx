'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useUIStore } from '@/lib/stores/uiStore'

interface SearchResult {
  query: string
  answer?: string
  confidence_score?: number
}

export function GlobalSearchBar() {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useUIStore((s) => [s.globalSearchOpen, s.setGlobalSearchOpen])
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)

  // ⌘K / Ctrl+K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen(true)
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [setOpen])

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    router.push(`/search?q=${encodeURIComponent(query.trim())}`)
    setOpen(false)
    setQuery('')
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 rounded-lg border border-gray-300 bg-gray-50 px-3 py-1.5 text-sm text-gray-500 hover:border-blue-400 hover:text-gray-700 transition-colors"
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <span>검색</span>
        <kbd className="rounded bg-gray-200 px-1 text-xs">⌘K</kbd>
      </button>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4">
      <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
      <div className="relative w-full max-w-xl bg-white rounded-xl shadow-2xl overflow-hidden">
        <form onSubmit={handleSearch}>
          <div className="flex items-center gap-3 px-4 py-3 border-b">
            <svg className="h-5 w-5 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="전사 지식 검색... (Enter로 검색)"
              className="flex-1 bg-transparent text-base outline-none placeholder:text-gray-400"
            />
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              ESC
            </button>
          </div>
        </form>
        <div className="px-4 py-2 text-xs text-gray-400">
          Enter 키를 눌러 검색 페이지로 이동합니다
        </div>
      </div>
    </div>
  )
}
