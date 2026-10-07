import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { enterAccessCode, getAccessStatus, type AccessStatus } from './api';
import { HomePage } from './pages/HomePage';
import { JobPage } from './pages/JobPage';

export default function App() {
  const [access, setAccess] = useState<AccessStatus | null>(null);
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getAccessStatus().then(setAccess).catch((err) => setError(err.message));
  }, []);

  async function unlock(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await enterAccessCode(code);
      setCode('');
      setAccess({ required: true, authorized: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not unlock app');
    } finally {
      setBusy(false);
    }
  }

  if (!access) {
    return <main className="page"><p>{error ?? 'Loading…'}</p></main>;
  }

  if (access.required && !access.authorized) {
    return (
      <main className="page">
        <p className="subtitle">Enter the family access code to continue.</p>
        <form className="url-form" onSubmit={unlock}>
          <label htmlFor="access-code">Access code</label>
          <input id="access-code" type="password" value={code} onChange={(e) => setCode(e.target.value)} autoComplete="off" required />
          <button type="submit" disabled={busy}>{busy ? 'Checking…' : 'Continue'}</button>
        </form>
        {error && <p className="error" role="alert">{error}</p>}
      </main>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/j/:jobId" element={<JobPage />} />
      </Routes>
    </BrowserRouter>
  );
}
