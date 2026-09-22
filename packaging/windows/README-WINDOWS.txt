StemDeck fork - Windows CPU Portable Preview
===========================================

For Windows 10/11 x64. This preview includes synced video playback from the
kittipatkampa/stemdeck fork. No Git, Python installation, PowerShell commands,
or NVIDIA GPU is required. CPU separation can take several minutes.

First launch
------------
1. Extract the ENTIRE ZIP to a writable folder under your user profile.
   Do not run StemDeck.exe from inside the ZIP or extract into Program Files.
2. Double-click StemDeck.exe in the extracted folder.
3. Keep internet access available for first-run FFmpeg and model downloads.
4. Import a local MP4 or a supported URL and wait for separation. Use the
   mixer controls to play the stems with the video.

Later launches: double-click StemDeck.exe again. Close the app window to stop.
Move the entire folder together; keep python/, backend/, data/, portable.txt,
and cpu-only beside the executable. This is a portable app, not an installer;
it creates no Start menu shortcut. The preview is unsigned, so Windows may
show reputation warnings. Do not disable Windows security protections.

Your files
----------
Runtime downloads, settings, models and logs are stored under data/.
A fresh portable installation stores its library under data/jobs. An existing
Documents/StemDeck/jobs library or a location chosen in Settings may remain
there. Check Settings -> StemData location before moving or backing up tracks.
Do not delete data/ as a troubleshooting step: it can contain your library.
Back up the whole portable folder and any configured external library.

Troubleshooting
---------------
If setup fails, check internet access, free disk space, and write permission
for the extracted folder, then retry. Logs are in data/logs/.
If the app fails after being moved, verify that the whole folder was moved.
This preview uses CPU only; do not install CUDA packages into its Python folder.
Preview updates use a new full ZIP. Keep the old folder and library backed up;
do not replace data/ with the empty folder from a fresh download.
Fork downloads: https://github.com/kittipatkampa/stemdeck/releases
