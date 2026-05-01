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
      `/api/v1/stream/job-status?job_id=${encodeURIComponent(jobId)}`,
    );

    let completed = false;

    const handleMessage = (event: MessageEvent<string>) => {
      setMessage(event.data);
    };

    const handleDone = (event: MessageEvent<string>) => {
      completed = true;
      setMessage(event.data);
      stream.close();
    };

    stream.onmessage = handleMessage;
    stream.addEventListener("progress", handleMessage);
    stream.addEventListener("done", handleDone);

    stream.onerror = () => {
      if (completed) return;
      setMessage("job stream unavailable");
      stream.close();
    };

    return () => stream.close();
  }, [jobId]);

  return message;
}
