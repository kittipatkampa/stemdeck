const API_BASE = import.meta.env.VITE_API_BASE ?? '';

export type AccessStatus = { required: boolean; authorized: boolean };
export type Capabilities = { youtube_url: boolean; file_upload: boolean; max_upload_bytes: number };

export async function getCapabilities(): Promise<Capabilities> {
  const res = await fetch(`${API_BASE}/api/capabilities`);
  if (!res.ok) throw new Error(`Could not check app capabilities (${res.status})`);
  return res.json();
}

export async function getAccessStatus(): Promise<AccessStatus> {
  const res = await fetch(`${API_BASE}/api/access`);
  if (!res.ok) throw new Error(`Could not check access (${res.status})`);
  return res.json();
}

export async function enterAccessCode(code: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/access`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Could not unlock app (${res.status})`);
  }
}

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
    if (res.status === 401) window.location.reload();
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export async function createUpload(file: File): Promise<{ job_id: string; upload_url: string; content_type: string }> {
  const res = await fetch(`${API_BASE}/api/uploads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename: file.name, size: file.size }),
  });
  if (!res.ok) {
    if (res.status === 401) window.location.reload();
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Could not prepare upload (${res.status})`);
  }
  return res.json();
}

export function uploadVideo(url: string, file: File, contentType: string, onProgress: (fraction: number) => void): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', url);
    xhr.setRequestHeader('Content-Type', contentType);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total);
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`Video upload failed (${xhr.status})`));
    };
    xhr.onerror = () => reject(new Error('Video upload failed. Check your connection and try again.'));
    xhr.send(file);
  });
}

export async function completeUpload(jobId: string, size: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/uploads/${jobId}/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ size }),
  });
  if (!res.ok) {
    if (res.status === 401) window.location.reload();
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Could not start job (${res.status})`);
  }
}

export async function getJob(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  if (!res.ok) {
    if (res.status === 401) window.location.reload();
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export function downloadUrl(jobId: string): string {
  return `${API_BASE}/api/jobs/${jobId}/download`;
}
