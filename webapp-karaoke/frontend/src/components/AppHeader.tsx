import { useLayoutEffect, useState } from 'react';

type Theme = 'light' | 'dark';

function initialTheme(): Theme {
  try {
    const saved = localStorage.getItem('karaoke-theme');
    if (saved === 'light' || saved === 'dark') return saved;
  } catch { /* Storage can be unavailable in private browsers. */ }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function AppHeader() {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useLayoutEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('karaoke-theme', theme); } catch { /* Keep the switch usable without storage. */ }
  }, [theme]);

  return (
    <header className="app-header">
      <h1>Karaoke Maker</h1>
      <div className="theme-switch" role="group" aria-label="Color theme">
        {(['light', 'dark'] as const).map((option) => (
          <button key={option} type="button" aria-pressed={theme === option} onClick={() => setTheme(option)}>
            {option === 'light' ? 'Light' : 'Dark'}
          </button>
        ))}
      </div>
    </header>
  );
}
