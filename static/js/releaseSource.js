// This fork must never replace itself with an upstream release.
export const REPO_URL = "https://github.com/kittipatkampa/stemdeck";
export const RELEASES_URL = `${REPO_URL}/releases`;
export const RELEASES_API = "https://api.github.com/repos/kittipatkampa/stemdeck/releases?per_page=10";

export async function fetchStableRelease(fetcher = fetch) {
  const response = await fetcher(RELEASES_API, {
    headers: { Accept: "application/vnd.github+json" },
  });
  if (!response.ok) return null;
  const releases = await response.json();
  if (!Array.isArray(releases)) return null;
  return releases.find((release) =>
    !release.draft && !release.prerelease &&
    release.html_url?.startsWith(`${RELEASES_URL}/tag/`) &&
    Array.isArray(release.assets) &&
    release.assets.every((asset) => asset.browser_download_url?.startsWith(`${RELEASES_URL}/download/`))
  ) ?? null;
}
