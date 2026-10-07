const YOUTUBE_HOSTS = new Set([
  'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com',
  'youtu.be', 'youtube-nocookie.com', 'www.youtube-nocookie.com',
]);
const VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;

export function youtubeVideoId(value: string): string | null {
  const raw = value.trim();
  if (!raw || raw.length > 2048) return null;
  try {
    const url = new URL(raw);
    if (!['http:', 'https:'].includes(url.protocol) || !YOUTUBE_HOSTS.has(url.hostname)) return null;
    const parts = url.pathname.split('/').filter(Boolean);
    let candidate: string | null | undefined;
    if (url.hostname === 'youtu.be') {
      candidate = parts[0];
    } else if (['shorts', 'embed', 'live'].includes(parts[0] ?? '')) {
      candidate = parts[1];
    } else if (parts.length === 0 || parts[0] === 'watch') {
      candidate = url.searchParams.get('v');
    }
    return candidate && VIDEO_ID.test(candidate) ? candidate : null;
  } catch {
    return null;
  }
}
