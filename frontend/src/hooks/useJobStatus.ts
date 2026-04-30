"use client";

import { useEffect, useState } from "react";

export function useJobStatus(jobId?: string) {
  const [message, setMessage] = useState<string>("");

  useEffect(() => {
    if (!jobId) {
      setMessage("");
      return;
    }

    const stream = new EventSource(
      `http://127.0.0.1:8000/api/v1/stream/job-status?job_id=${encodeURIComponent(jobId)}`,
    );

    const handleMessage = (event: MessageEvent<string>) => {
      setMessage(event.data);
    };

    stream.onmessage = handleMessage;
    stream.addEventListener("progress", handleMessage);
    stream.addEventListener("done", handleMessage);

    stream.onerror = () => {
      setMessage("job stream unavailable");
      stream.close();
    };

    return () => stream.close();
  }, [jobId]);

  return message;
}
