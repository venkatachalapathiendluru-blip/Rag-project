# Frontend Setup

Needs Node 22 or later.

```bash
# Terminal 1: backend, from the repository root
venv/bin/python -m backend.migrate
venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8020

# Terminal 2: frontend
cd frontend
npm ci
npm run dev        # http://127.0.0.1:5173
```

Vite proxies `/api` to `http://127.0.0.1:8020`. Change it with `VITE_API_PROXY`. Set `VITE_API_BASE` only if the API is on another origin, and then also set `RAG_CORS_ORIGINS` on the backend.

Production build: `npx vite build` writes to `frontend/dist`, which `frontend/Dockerfile` serves with nginx.
