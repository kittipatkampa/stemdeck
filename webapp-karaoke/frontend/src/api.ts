const API_BASE = import.meta.env.VITE_API_BASE ?? '';

export type Stage = 'download' | 'extract' | 'stem' | 'combine';

export type JobStatus = {
  job_id: string;
  status: 'queued' | 'running' | 'done' | 'failed';
  stage: Stage;
  stage_progress: number;
  overall_progress: number;
  title: string | null;
  error: string | null;
};

export async function createJob(url: string): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}/api/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export async function getJob(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export function downloadUrl(jobId: string): string {
  return `${API_BASE}/api/jobs/${jobId}/download`;
}
