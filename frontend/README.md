Frontend React scaffold

Quick start:

1. Install dependencies:

```bash
cd frontend
npm install
```

2. Run dev server:

```bash
npm run dev
```

Notes:
- The project links to existing CSS and static assets under `/static/dockerlabs/...` which are served by the backend.
- Endpoints to fetch machines should be provided by the backend (e.g., `/api/maquinas`).

Development notes:
- Vite is configured with a proxy so requests to `/api/*` are forwarded to `http://127.0.0.1:5000`.
- Start the backend first (see `backend/run.py`) so the proxy has a target.

Production:
- Build the frontend and serve the static output from the backend or a static host:

```bash
cd frontend
npm run build
# Copy or serve the `dist/` contents from your backend static host
```
