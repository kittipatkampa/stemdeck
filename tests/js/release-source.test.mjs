import assert from "node:assert/strict";
import { fetchStableRelease, RELEASES_API, RELEASES_URL } from "../../static/js/releaseSource.js";
const stable = { tag_name: "v1.0.0", html_url: `${RELEASES_URL}/tag/v1.0.0`, assets: [
  { browser_download_url: `${RELEASES_URL}/download/v1.0.0/StemDeck-Windows-x64.zip` },
] };
let requested;
const fetcher = (data, ok = true) => async (url) => {
  requested = url;
  return { ok, json: async () => data };
};
assert.deepEqual(await fetchStableRelease(fetcher([
  { ...stable, draft: true }, { ...stable, prerelease: true }, stable,
])), stable);
assert.equal(requested, RELEASES_API);
assert.equal(new URL(requested).pathname, "/repos/kittipatkampa/stemdeck/releases");
assert.equal(await fetchStableRelease(fetcher([])), null);
assert.equal(await fetchStableRelease(fetcher({}, false)), null);
assert.equal(await fetchStableRelease(fetcher({})), null);
assert.equal(await fetchStableRelease(fetcher([{ ...stable, html_url: "https://github.com/stemdeckapp/stemdeck/releases/tag/v1.0.0" }])), null);
assert.equal(await fetchStableRelease(fetcher([{ ...stable, assets: [{ browser_download_url: "https://github.com/stemdeckapp/stemdeck/releases/download/v1.0.0/app.zip" }] }])), null);
await assert.rejects(fetchStableRelease(async () => { throw new TypeError("offline"); }), /offline/);
console.log("Release discovery: fork-only, drafts, prereleases, empty/error responses passed");
