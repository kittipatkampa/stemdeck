import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { createJob } from '../api';

const YOUTUBE_HINT =
  /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be|m\.youtube\.com)\/.+/i;

export function HomePage() {
  const [url, setUrl] = useState('https://youtube.com/shorts/senFAeo0RQM');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

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

  return (
    <main className="page">
      <h1>Karaoke Maker</h1>
      <p className="subtitle">Paste a YouTube link and get an MP4 without vocals.</p>
      <form className="url-form" onSubmit={onSubmit}>
        <label htmlFor="url">YouTube URL</label>
        <input
          id="url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://youtube.com/watch?v=..."
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Starting…' : 'Make it'}
        </button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
    </main>
  );
}
