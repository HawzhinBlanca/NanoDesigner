"use client";
import { useCallback, useMemo, useState } from "react";
import { track } from "@/lib/analytics";

type FileState = {
  file: File;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
};

function uploadWithProgress(url: string, projectId: string, file: File, onProgress: (pct: number) => void): Promise<any> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.set("project_id", projectId);
    form.set("file", file);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        onProgress(pct);
      }
    };
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch {
            resolve({});
          }
        } else {
          reject(new Error(xhr.responseText || `HTTP ${xhr.status}`));
        }
      }
    };
    xhr.send(form);
  });
}

export function AssetDropzone({ projectId }: { projectId: string }) {
  const [items, setItems] = useState<FileState[]>([]);
  const [summary, setSummary] = useState<string>("");
  const endpoint = useMemo(() => (process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000") + "/ingest/file", []);

  const onChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = Array.from(e.target.files || []);
    setItems(f.map((file) => ({ file, progress: 0, status: "pending" })));
  }, []);

  const onUpload = useCallback(async () => {
    const maxConcurrent = 10;
    let processedTotal = 0;
    const queue = [...items];
    const running: Promise<void>[] = [];

    async function runOne(item: FileState) {
      setItems((prev) => prev.map((it) => (it.file === item.file ? { ...it, status: "uploading" } : it)));
      try {
        const data = await uploadWithProgress(endpoint, projectId, item.file, (pct) => {
          setItems((prev) => prev.map((it) => (it.file === item.file ? { ...it, progress: pct } : it)));
        });
        processedTotal += data?.processed ?? 0;
        setItems((prev) => prev.map((it) => (it.file === item.file ? { ...it, progress: 100, status: "done" } : it)));
      } catch (e: any) {
        setItems((prev) => prev.map((it) => (it.file === item.file ? { ...it, status: "error", error: String(e?.message || e) } : it)));
      }
    }

    while (queue.length > 0 || running.length > 0) {
      while (queue.length > 0 && running.length < maxConcurrent) {
        const next = queue.shift()!;
        const p = runOne(next).finally(() => {
          const idx = running.indexOf(p as any);
          if (idx >= 0) running.splice(idx, 1);
        });
        running.push(p);
      }
      if (running.length > 0) {
        await Promise.race(running);
      }
    }
    setSummary(`Processed ${processedTotal} asset(s)`);
    track.assetUploaded(projectId, processedTotal);
  }, [endpoint, items, projectId]);

  return (
    <div className="space-y-4">
      <input type="file" multiple onChange={onChange} />
      <button onClick={onUpload} className="rounded bg-black text-white px-3 py-2 text-sm">Upload</button>
      <ul className="text-sm space-y-1">
        {items.map((it) => (
          <li key={it.file.name} className="flex items-center justify-between">
            <span className="truncate mr-2">{it.file.name}</span>
            <span>{it.progress}% {it.status === "error" ? `— ${it.error}` : ""}</span>
          </li>
        ))}
      </ul>
      {summary && <div className="text-sm text-green-600">{summary}</div>}
    </div>
  );
}

