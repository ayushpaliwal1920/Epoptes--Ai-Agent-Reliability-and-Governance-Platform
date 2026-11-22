# AgentGuard frontend

The frontend is a React application powered by Vite. It includes workspace
sign-in and registration, agent credential management, observability, run
history, and organization security events.

## Local development

1. Install Node.js 18.18 or newer.
2. From this directory, install dependencies and start Vite:

   ```powershell
   npm ci
   npm run dev
   ```

3. In a separate terminal at the project root, start the API:

   ```powershell
   uvicorn app.main:app --app-dir backend --reload
   ```

Vite proxies `/api` requests to `http://127.0.0.1:8000` during development.
Set `VITE_API_BASE_URL` when the API is hosted at a different origin; that
origin must permit browser requests from the frontend.

Agent API keys are held in browser session storage and removed when you sign
out or close the browser session. Newly created and rotated keys are shown
once, so copy them before dismissing the dialog.
