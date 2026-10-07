import type { Stage } from '../api';

const STAGES: { id: Stage; label: string }[] = [
  { id: 'download', label: 'Download' },
  { id: 'extract', label: 'Extract video & audio' },
  { id: 'stem', label: 'Stem track (remove vocals)' },
  { id: 'combine', label: 'Combine karaoke video' },
];

type Props = {
  stage: Stage;
  stageProgress: number;
  overallProgress: number;
};

function stageIndex(stage: Stage): number {
  return STAGES.findIndex((s) => s.id === stage);
}

export function ProgressStepper({ stage, stageProgress, overallProgress }: Props) {
  const current = stageIndex(stage);

  return (
    <div className="stepper">
      <div className="overall-bar" aria-label="Overall progress">
        <div
          className="overall-fill"
          style={{ width: `${Math.round(overallProgress * 100)}%` }}
        />
      </div>
      <p className="overall-label">{Math.round(overallProgress * 100)}% complete</p>
      <ol className="steps">
        {STAGES.map((s, i) => {
          const done = i < current;
          const active = i === current;
          const pct = active ? stageProgress : done ? 1 : 0;
          return (
            <li key={s.id} className={active ? 'active' : done ? 'done' : ''}>
              <span className="step-title">{s.label}</span>
              <div className="step-bar">
                <div className="step-fill" style={{ width: `${Math.round(pct * 100)}%` }} />
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
