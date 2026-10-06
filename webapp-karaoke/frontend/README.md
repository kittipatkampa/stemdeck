# Dad's Karaoke frontend

React and Vite UI for the single-user karaoke app. The page prompts for the family access code when the API requires it, then lets the user submit a YouTube URL, follow four processing stages, preview the result, and download the MP4.

For local development, run `npm install` and `npm run dev` here, alongside the FastAPI backend. Vite proxies `/api` to the backend. For Cloud Run, the nginx image provides the same proxy so the access cookie and video requests stay on one origin. See the [root README](../README.md) and [deployment guide](../deploy/README.md).
