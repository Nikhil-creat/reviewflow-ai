# ⚡ ReviewFlow AI

**An autonomous reputation and local-marketing engine.** A multi-agent LangGraph loop syncs
customer reviews, scores sentiment, drafts replies in your real brand voice using RAG over
your own past replies (pgvector), auto-posts the safe ones, escalates the risky ones to a
human, and turns your best 5-star reviews into shareable social quote cards with a
convolutional vision pipeline — all on free-tier, sub-second Groq inference.

## Designed and Developed by 
# **NIKHIL CHARY SRIRAMOJU**
BTech CSE (Final Year)

- GitHub: [Nikhil-creat](https://github.com/Nikhil-creat)
- LinkedIn: [nikhil-chary-sriramoju](https://in.linkedin.com/in/nikhil-chary-sriramoju-95041b38a)
- Email: sriramojunikhil66@gmail.com
- Instagram: [@nikhil__sriramoju](https://www.instagram.com/nikhil__sriramoju)
- Facebook: [Profile](https://www.facebook.com/profile.php?id=100079201124141)

---

## 🧠 Architecture

```
┌──────────────┐      WebSocket telemetry      ┌───────────────────┐
│  Next.js 14   │◄──────────────────────────────│   FastAPI + WS     │
│  Dashboard    │  ───────────────────────────► │   Gateway           │
│ (Framer Motion)│         REST /api/*           └─────────┬──────────┘
└──────────────┘                                          │
                                                            ▼
                                                  ┌───────────────────┐
                                                  │  LangGraph Agent    │
                                                  │  State Machine       │
                                                  │                       │
                                                  │  sync → sentiment →   │
                                                  │  rag_voice →          │
                                                  │  dispatcher → vision  │
                                                  └───┬──────┬──────┬────┘
                                                      │      │      │
                                          ┌───────────┘      │      └───────────┐
                                          ▼                  ▼                  ▼
                                 ┌────────────────┐ ┌────────────────┐ ┌─────────────────┐
                                 │ Groq (Llama)     │ │ Supabase        │ │ Vision service    │
                                 │ chat inference    │ │ Postgres+pgvector│ │ Pillow/OpenCV CNN │
                                 └────────────────┘ └────────────────┘ └─────────────────┘
```

**The four agents** (`backend/agents/nodes.py`):
1. **Scraper / Sync Agent** — pulls new reviews from a connector (demo generator, Google
   Places, or manual entry) and queues the unprocessed ones.
2. **Sentiment Evaluation Agent** — classifies `positive / neutral / negative / volatile`,
   extracts intent tags, risk flags (legal threats, safety issues, profanity…) and quotable
   key phrases, via Groq JSON-mode with a heuristic fallback if no key is set.
3. **RAG Brand-Voice Agent** — embeds the review locally (free, `fastembed`/`bge-small`,
   384-d), runs a cosine similarity search over `pgvector` (HNSW-indexed), and drafts a
   reply that mirrors your real tone, grounded only in facts you've actually provided.
4. **Action Dispatcher Agent** — auto-posts the reply when it's safe (high confidence, no
   risk flags, above your star threshold) or flags it for a human, and — for 5-star,
   positive reviews — hands off to the **Vision Agent**, which calls a small computer-vision
   service that runs a convolutional filter bank (Sobel/Laplacian → ReLU → max-pool) to find
   the calmest region of a generated background and render a glass-morphic quote card there.

Every step is written to `agent_events` and published on Redis pub/sub, so the dashboard's
WebSocket feed shows it in real time — the same "Vector search complete (12ms)" style log
you asked for.

## 📂 Project layout

```
reviewflow-ai/
├── docker-compose.yml         # frontend + backend + worker + vision + redis + db
├── .env.example
├── backend/                   # FastAPI + LangGraph
│   ├── main.py                 # REST + WebSocket gateway
│   ├── agents/                 # graph.py, nodes.py, runner.py, autopilot_worker.py
│   ├── core/                   # config, db, embeddings, llm (Groq), telemetry, auth
│   └── connectors/              # demo, google_places
├── vision/                    # Pillow/OpenCV quote-card microservice
├── frontend/                  # Next.js 14 dashboard (App Router, Tailwind, Framer Motion)
├── supabase/migrations/       # SQL schema (pgvector, RLS, HNSW index)
├── db/local-init/             # local-only Postgres bootstrap (mirrors Supabase for `docker compose up`)
└── .github/workflows/         # GitHub Pages deploy action
```

## 🚀 Run it locally (Docker)

```bash
cp .env.example .env
# edit .env and paste a free key from https://console.groq.com/keys
docker compose up --build
```

- Dashboard → http://localhost:3000/dashboard
- API docs → http://localhost:8000/docs
- A demo business ("Blue Lotus Café") is auto-seeded with real brand-voice examples so the
  RAG agent has something to retrieve from on first run.
- No Groq key yet? Everything still runs — sentiment and replies fall back to fast
  heuristics/templates so you can see the whole pipeline before signing up for a key.

## 🔑 Getting a free Groq key

1. Go to <https://console.groq.com/keys> and sign up (free).
2. Create an API key, paste it into `.env` as `GROQ_API_KEY`.
3. Groq's free tier serves Llama 3.1/3.3 models with generous rate limits and no card
   required — that's what gives the "sub-second, zero-cost" inference.

## ☁️ Deploying for real

| Piece | Where | Notes |
|---|---|---|
| Dashboard | **Vercel** or **Netlify** (recommended) or **GitHub Pages** | Vercel/Netlify run the full Next.js server — no code changes needed, just set `NEXT_PUBLIC_API_URL`/`NEXT_PUBLIC_WS_URL`. |
| Backend + worker + vision | **Render**, **Fly.io**, or **Hugging Face Spaces (Docker)** | All three ship a `Dockerfile`; point them at your Supabase and Redis (Upstash free tier works). |
| Database | **Supabase** (hosted, free tier) | Run `supabase/migrations/001_reviewflow_schema.sql` then `002_connectors.sql` in the SQL editor. Skip `db/local-init/*` — that's for local Docker only. |

### Vercel / Netlify (recommended for the dashboard)
```bash
cd frontend
vercel            # or: netlify deploy
```
Set `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` to your deployed backend's URL in the
project's environment variables. No `next.config.mjs` changes needed — `NEXT_EXPORT` is
only set for the Pages build.

### GitHub Pages (static, dashboard only)
Pages serves static files, so it **cannot run FastAPI, Redis or the vision service**. The
included workflow (`.github/workflows/deploy-pages.yml`) builds the dashboard as a static
export and deploys it automatically on every push to `main`. With no backend URL configured
it runs the built-in **offline demo mode** (simulated agent run, same UI and telemetry
style) — perfect for a portfolio link. See the step-by-step guide below to also wire it up
to a real backend.

## 🧭 Step-by-step: upload to GitHub & publish on GitHub Pages

1. **Create the repo** — on GitHub, click *New repository*, name it (e.g. `reviewflow-ai`),
   leave it empty (no README/license), and create it.
2. **Push this project:**
   ```bash
   cd reviewflow-ai
   git init
   git add .
   git commit -m "ReviewFlow AI - autonomous reputation engine"
   git branch -M main
   git remote add origin https://github.com/<your-username>/reviewflow-ai.git
   git push -u origin main
   ```
   (`.env` is already in `.gitignore`, so your Groq key is never pushed.)
3. **Enable Pages** — in the repo, go to *Settings → Pages → Build and deployment → Source*
   and choose **GitHub Actions**. That's it; the included workflow takes over.
4. **Watch it deploy** — open the *Actions* tab; the `Deploy dashboard to GitHub Pages` run
   builds `frontend/` as a static export and publishes it. When it finishes, your dashboard
   is live at:
   ```
   https://<your-username>.github.io/reviewflow-ai/
   ```
5. **(Optional) connect a real backend** — deploy `backend/` + `vision/` (Dockerfiles
   included) to Render/Fly/HF Spaces, then edit the `env:` block in
   `.github/workflows/deploy-pages.yml` to set `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL`
   to that backend's URL, commit, and push — the next Pages build goes live automatically.

## 🛠️ Tech stack

Next.js 14 (App Router) · Tailwind CSS · Framer Motion · Lucide React · FastAPI · LangGraph
· Groq (Llama 3.1 / 3.3) · Supabase Postgres + pgvector (HNSW) · Redis · Pillow + OpenCV ·
Docker & Docker Compose.

## 📜 License

MIT — see [`LICENSE`](./LICENSE).

---

<p align="center"><b>Designed & Developed by NIKHIL CHARY SRIRAMOJU</b><br/>
<a href="https://github.com/Nikhil-creat">GitHub</a> ·
<a href="https://in.linkedin.com/in/nikhil-chary-sriramoju-95041b38a">LinkedIn</a></p>
