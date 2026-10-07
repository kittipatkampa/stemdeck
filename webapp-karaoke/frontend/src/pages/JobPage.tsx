import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { downloadUrl, getJob, type JobStatus } from '../api';
import { ProgressStepper } from '../components/ProgressStepper';

export function JobPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;

    async function poll() {
      try {
        const data = await getJob(jobId!);
        if (cancelled) return;
        setJob(data);
        setError(null);
        if (data.status === 'failed' || data.status === 'done') return;
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Could not load job');
        }
        return;
      }
      if (!cancelled) {
        window.setTimeout(poll, 1000);
      }
    }

    poll();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  if (!jobId) {
    return <p className="error">Missing job id</p>;
  }

  const title = job?.title ?? 'Processing…';

  return (
    <main className="page">
      <Link to="/" className="back">← New video</Link>
      <h2 className="job-title">{title}</h2>
      {error && <p className="error" role="alert">{error}</p>}
      {job && job.status !== 'failed' && (
        <ProgressStepper
          stage={job.stage}
          stageProgress={job.stage_progress}
          overallProgress={job.overall_progress}
        />
      )}
      {job?.status === 'failed' && (
        <div className="failed">
          <p className="error">{job.error ?? 'Job failed'}</p>
          <Link to="/" className="button-link">Try again</Link>
        </div>
      )}
      {job?.status === 'done' && (
        <div className="done">
          <a className="button-link" href={downloadUrl(jobId)} download>
            Download MP4
          </a>
          <video
            className="preview"
            src={downloadUrl(jobId)}
            controls
            playsInline
          />
        </div>
      )}
      {job?.status === 'queued' && <p className="muted">Queued…</p>}
    </main>
  );
}
