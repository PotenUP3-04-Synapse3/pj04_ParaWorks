'use client'

import { useEffect, useRef, useState } from 'react'
import { getAccessToken } from '@/lib/api'

export type JobStatus = 'PENDING' | 'STARTED' | 'PROGRESS' | 'SUCCESS' | 'FAILURE' | 'done' | 'timeout' | 'error'

export interface JobStatusData {
  task_id: string
  status: JobStatus
  progress?: number
  result?: string
  error?: string
}

export function useJobStatus(taskId: string | null) {
  const [data, setData] = useState<JobStatusData | null>(null)
  const [isComplete, setIsComplete] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!taskId) return

    const token = getAccessToken()
    const url = `/api/v1/stream/job-status?task_id=${taskId}${token ? `&token=${token}` : ''}`

    esRef.current = new EventSource(url)

    esRef.current.onmessage = (event) => {
      try {
        const parsed: JobStatusData = JSON.parse(event.data)
        setData(parsed)
        if (['SUCCESS', 'FAILURE', 'done', 'timeout', 'error'].includes(parsed.status)) {
          setIsComplete(true)
          esRef.current?.close()
        }
      } catch {
        // ignore parse errors
      }
    }

    esRef.current.onerror = () => {
      setIsComplete(true)
      esRef.current?.close()
    }

    return () => {
      esRef.current?.close()
    }
  }, [taskId])

  return { data, isComplete }
}
