export type JobUpdate = {
  status?: string;
  preview_url?: string;
  url?: string;
  r2_key?: string;
  progress?: number;
  error?: string;
};

export function connectJobWS(jobId: string, onMessage: (u: JobUpdate) => void, onError?: (e: Event) => void) {
  const base = process.env.NEXT_PUBLIC_API_BASE?.replace(/^http/, "ws") ?? "ws://localhost:8000";
  const ws = new WebSocket(`${base}/ws/jobs/${jobId}`);
  ws.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data);
      onMessage(data);
    } catch {
      // ignore
    }
  };
  if (onError) ws.onerror = onError;
  return ws;
}

export async function pollJob(jobId: string, onMessage: (u: JobUpdate) => void, abort: AbortSignal) {
  const base = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
  // simple long-poll every 2s
  while (!abort.aborted) {
    try {
      const res = await fetch(`${base}/render/jobs/${jobId}`);
      if (res.ok) {
        const data = await res.json();
        onMessage(data);
        if (data.status === "completed" || data.status === "failed") return;
      }
    } catch {
      // ignore
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
}

