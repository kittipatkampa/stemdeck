import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { completeUpload, createJob, createUpload, getCapabilities, uploadVideo, type Capabilities } from '../api';

const YOUTUBE_HINT =
  /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be|m\.youtube\.com)\/.+/i;

export function HomePage() {
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    getCapabilities().then(setCapabilities).catch((err) => setError(err.message));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const trimmed = url.trim();
    if (!trimmed) {
      setError('Paste a YouTube URL');
      return;
    }
    if (!YOUTUBE_HINT.test(trimmed)) {
      setError('Enter a valid YouTube URL');
      return;
    }
    setLoading(true);
    try {
      const { job_id } = await createJob(trimmed);
      navigate(`/j/${job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start job');
      setLoading(false);
    }
  }

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!file || !capabilities) return;
    if (file.size > capabilities.max_upload_bytes) {
      setError('Choose a video under 500 MB');
      return;
    }
    setLoading(true);
    setUploadProgress(0);
    try {
      const prepared = await createUpload(file);
      await uploadVideo(prepared.upload_url, file, prepared.content_type, setUploadProgress);
      setPreparing(true);
      await completeUpload(prepared.job_id, file.size);
      navigate(`/j/${prepared.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Video upload failed');
      setLoading(false);
      setPreparing(false);
      setUploadProgress(null);
    }
  }

  return (
    <main className="page">
      <h1>Karaoke Maker</h1>
      <p className="subtitle">Make a karaoke MP4 without vocals.</p>
      {capabilities?.youtube_url && <form className="url-form input-panel" onSubmit={onSubmit}>
        <h2>Paste a YouTube link</h2>
        <p className="muted">We’ll download the video in the cloud, then make your karaoke version.</p>
        <label htmlFor="url">YouTube video URL</label>
        <input
          id="url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://youtube.com/watch?v=..."
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Starting download…' : 'Download and make karaoke'}
        </button>
      </form>}
      {capabilities?.file_upload && <form className="url-form input-panel" onSubmit={onUpload}>
        <h2>Upload a video file</h2>
        <label htmlFor="video-file">Video on your laptop or phone</label>
        <input
          id="video-file"
          type="file"
          accept="video/mp4,video/quicktime,video/webm,video/x-matroska,.mp4,.m4v,.mov,.webm,.mkv"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          disabled={loading}
          required
        />
        <p className="muted">MP4, MOV, WebM, or MKV. Up to 500 MB and 10 minutes.</p>
        <button type="submit" disabled={loading || !file}>
          {preparing ? 'Preparing video…' : loading ? `Uploading ${Math.round((uploadProgress ?? 0) * 100)}%…` : 'Make karaoke video'}
        </button>
      </form>}
      {!capabilities && !error && <p className="muted">Loading…</p>}
      {error && <p className="error" role="alert">{error}</p>}
    </main>
  );
}
