// Demo mode types
type RenderRequest = any;
type RenderResponse = any;
type AsyncRenderResponse = any;
type JobStatusResponse = any;
type IngestRequest = any;
type IngestResponse = any;
type CanonDeriveRequest = any;
type CanonDeriveResponse = any;

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`HTTP ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

let authTokenProvider: (() => Promise<string | null>) | null = null;
export function setAuthTokenProvider(fn: () => Promise<string | null>) {
  authTokenProvider = fn;
}

async function withAuth(init: RequestInit = {}): Promise<RequestInit> {
  if (!authTokenProvider) return init;
  try {
    const token = await authTokenProvider();
    if (token) {
      return {
        ...init,
        headers: {
          ...(init.headers || {}),
          authorization: `Bearer ${token}`,
        },
      } as RequestInit;
    }
  } catch {}
  return init;
}

export const api = {
  async render(req: RenderRequest): Promise<RenderResponse> {
    const res = await fetch(`${API_BASE}/render`, await withAuth({
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req)
    }));
    return json<RenderResponse>(res);
  },
  async renderAsync(req: RenderRequest): Promise<AsyncRenderResponse> {
    const res = await fetch(`${API_BASE}/render/async`, await withAuth({
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req)
    }));
    return json<AsyncRenderResponse>(res);
  },
  async jobStatus(jobId: string): Promise<JobStatusResponse> {
    const res = await fetch(`${API_BASE}/render/jobs/${jobId}`, await withAuth());
    return json<JobStatusResponse>(res);
  },
  async ingest(req: IngestRequest): Promise<IngestResponse> {
    const res = await fetch(`${API_BASE}/ingest`, await withAuth({
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req)
    }));
    return json<IngestResponse>(res);
  },
  async canonDerive(req: CanonDeriveRequest): Promise<CanonDeriveResponse> {
    const res = await fetch(`${API_BASE}/canon/derive`, await withAuth({
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req)
    }));
    return json<CanonDeriveResponse>(res);
  }
};

export type { RenderRequest, RenderResponse, AsyncRenderResponse, JobStatusResponse, IngestRequest, IngestResponse, CanonDeriveRequest, CanonDeriveResponse };

