# Windows CPU preview acceptance

This unsigned preview targets Windows 10/11 x64. Desktop acceptance is **pending** until a tester records the results below. Automated checks do not prove desktop behavior. Do not publish the draft release before these pass.

Record Windows version, ZIP SHA-256, build version and commit from `build-metadata.json`, and pass/fail notes for every step. Do not include personal track names or credentials in shared logs.

1. On a Windows computer without developer tools, extract the whole ZIP to a writable folder (for example, a folder under your user profile). Double-click `StemDeck.exe`. Record any Windows reputation warning; do not disable security protection.
2. Complete first-run downloads. Import a short local MP4 and wait for separation to finish.
3. Check playback, vocal mute, seeking, video resizing, and fullscreen. Confirm the video stays aligned with the stem mix.
4. Close and reopen the app. Confirm the track remains in the library and no backend or separation process remains after closing.
5. Close the app, move the entire extracted folder to another writable path containing spaces, and relaunch. Confirm playback and library access. A previously configured external library should remain at its configured location.
6. In a separate fresh extraction, disconnect the network before first-run setup. Confirm a useful error appears, reconnect, and retry successfully. Do not delete the original `data` folder to simulate this.

Send failures with the relevant `data/logs` files, step number, and observed behavior. Keep the release a draft if a check fails or remains untested.
