# Systems Integration Lab Environment

## What this is

**This is the completed reference implementation of the lab stack, not the student assignment.** Everything here runs; the "Current State" sections below are all marked done because they are done.

A graduate-level Systems Integration teaching stack: a three-tier enterprise architecture in containers, with a small local LLM added as a capability of the middleware tier. The architecture is the lesson. The AI rides on it.

**The step-by-step lab worksheets do not exist.** You will see references to a numbered build sequence ("legacy from Step 4", "post-Step 7a"); those are the order the stack was built in, not documents you are missing. Nothing is being withheld — the worksheets were never written. What you get is a working stack, the reasoning behind each decision, and an unusually honest troubleshooting record. Wrapping that in learning objectives and deliverables is the part left to you.

**Four choices are load-bearing.** They look like things to modernize; they are the lesson:
1. **Three containers, not four** — the LLM lives inside the middleware tier because it is a capability, not a tier.
2. **`python:3.12-slim`, not alpine** — the Ollama binary is glibc-linked and will not run on musl.
3. **No host installs** — every process runs in the compose stack; the only host requirements are Docker and git.
4. **Ollama on loopback only** — the model is reachable by Flask, not from outside the container.

`PITFALLS.md` argues each of these from the failure that produced it.

## Prerequisites
- A container runtime: [Docker Desktop](https://www.docker.com/products/docker-desktop/), [Colima](https://github.com/abiosoft/colima), OrbStack, or Docker Engine on Linux
- [Git](https://git-scm.com/)
- A text editor

**Nothing else is installed on your host machine.** Every process in this lab runs inside a container. See [PITFALLS.md](PITFALLS.md) for why this matters.

### What your machine actually needs

This is the part that costs people an evening, so it is stated up front rather than discovered.

| Resource | Needed | Why |
|---|---|---|
| Container VM RAM | **8 GB recommended**, 4 GB likely floor | The 3B model must fit in RAM *inside the VM*, alongside Postgres |
| Disk | **~10 GB free** | ~2 GB model, ~1 GB images, plus build cache |
| CPU | 4+ cores recommended | Inference is CPU-only here; fewer cores means slower answers, not failure |
| Architecture | arm64 or x86_64 | Verified on Apple Silicon (arm64) |

**On macOS or Windows your containers run inside a Linux VM, and that VM's memory limit is the one that matters — not your machine's.** A laptop with 32 GB of RAM will still fail if the VM was given 2 GB. Docker Desktop defaults are usually adequate; Colima's default is not.

```bash
# Colima: the default 2 CPU / 2 GB VM is too small for a 3B model.
colima start --cpu 6 --memory 12 --disk 60

# Docker Desktop: Settings → Resources → Memory, 8 GB or more
```

If the model is starved of memory the symptom is not a clear error — it is a request that hangs, or a container that disappears. See [PITFALLS.md §13](PITFALLS.md).

Verified working configuration: Colima 6 CPU / 12 GB / 60 GB on an Apple Silicon Mac, Docker Engine 29.5.2, Compose 5.2.0.

## Getting Started
```bash
git clone <repo-url>
cd Systems_Integration_Course
cp .env.example .env          # then edit .env and set DB_PASSWORD
docker compose up --build -d
docker compose exec middleware ollama pull llama3.2:3b   # one-time, ~2 GB
```
Open `http://localhost:8080` in your browser to see the frontend.

**Do not skip the `ollama pull`.** The stack builds, starts, and answers
`/api/health` and `/api/inventory` without it — only the chat fails, and it fails
at the point where you have already been told everything is running.

The database password lives in `.env`, which is gitignored — no credential is
committed to this repository. Compose refuses to start with a clear error if
`DB_PASSWORD` is unset, rather than quietly falling back to a default. Any value
works for local lab use since the database is not reachable outside the compose
network; `openssl rand -base64 24` will generate one.

## Architecture
```
┌─────────────┐     ┌─────────────────────────┐     ┌─────────────┐
│  Frontend    │────▶│  Middleware              │────▶│  Database    │
│  (Apache)    │◀────│  (Python/Flask)          │◀────│  (Postgres)  │
│              │     │  + Small LLM (Ollama)    │     │              │
│  Container 1 │     │  Container 2             │     │  Container 3 │
└─────────────┘     └─────────────────────────┘     └─────────────┘
```
Three tiers, three containers. The LLM is a capability of the middleware tier — not a tier of its own. See [PITFALLS.md §2](PITFALLS.md) for the architectural rationale.

## Current State

### Container 1: Frontend (done)
- Apache HTTP Server on Alpine Linux
- Serves chat-style UI on port 8080
- Sends user messages to the middleware via REST API
- Source: `frontend/index.html`, `frontend/Dockerfile`

### Container 2: Middleware (done — Flask + LLM endpoint wired)
- Python 3.12 on Debian (slim) — glibc base required for the Ollama binary
- Flask app exposes:
  - `POST /api/message` — echo endpoint (legacy from Step 4)
  - `GET /api/health` — health check
  - `GET /api/inventory` — reads inventory rows from Postgres and returns JSON
  - `POST /api/ask` — natural-language question answering: pulls inventory context from Postgres, sends prompt + context to the LLM, returns `{"answer": "..."}`
- Ollama LLM server bundled in the same container, listening on `127.0.0.1:11434` (loopback only — only Flask can reach it)
- Entrypoint script starts `ollama serve` first, waits for readiness, then starts Flask
- Model name is configurable via the `OLLAMA_MODEL` env var in `docker-compose.yml` (default: `llama3.2:3b`)
- Exposed on port 5001 (port 5000 is reserved by macOS AirPlay)
- Source: `middleware/app.py`, `middleware/Dockerfile`, `middleware/entrypoint.sh`, `middleware/requirements.txt`

### Container 3: Database (done)
- PostgreSQL 16 on Alpine Linux
- `inventory` table with 6 seed rows, schema and seed data loaded from `db/init.sql` on first run
- Healthcheck via `pg_isready`; middleware waits for `service_healthy` before starting
- Persisted in named volume `db_data`
- Not exposed outside the compose network (middleware reaches it as hostname `db:5432`)
- Source: `db/init.sql`, `docker-compose.yml`

### AI Integration (done)
After the stack is up for the first time, pull the course model into the Ollama volume:
```bash
docker compose exec middleware ollama pull llama3.2:3b
```
This downloads ~2 GB into the `ollama_data` named volume. The volume persists across rebuilds, so this is one-time. Verify:
```bash
docker compose exec middleware ollama list
```
The chat UI at `http://localhost:8080` is wired to `POST /api/ask`. The middleware fetches inventory data from Postgres, injects it into the system prompt, and asks the LLM. The LLM is instructed to answer only from inventory data and decline questions outside that scope.

Test from the command line:
```bash
curl -X POST http://localhost:5001/api/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "Which item has the lowest stock?"}'
```

**Latency expectations**: first response after a stack restart is slow (~5–40 sec depending on hardware) because the model loads into RAM. After that, responses are ~1–10 sec while the model is warm. Ollama keeps the model resident for 5 minutes of idle time (`OLLAMA_KEEP_ALIVE=5m`) before unloading.

## Useful Commands
```bash
# Stack lifecycle
docker compose up --build -d   # Build and start all containers
docker compose down            # Stop and remove containers (volumes preserved)
docker compose down -v         # Stop and DELETE volumes (loses db data + model)
docker compose ps              # Show running containers
docker compose logs <service> --tail 30   # Recent logs from one service

# Health checks
curl http://localhost:8080                    # Frontend
curl http://localhost:5001/api/health         # Middleware
curl http://localhost:5001/api/inventory      # Middleware→DB only (NOT the frontend hop)
docker compose exec middleware ollama list    # Model status

# Resource accounting
docker stats --no-stream      # Live container RAM/CPU
docker system df              # Disk usage by category
docker images --format "{{.Repository}}\t{{.Size}}"

# Cleanup (safe — does not delete running containers, named images, or volumes)
docker builder prune -f       # Reclaim build cache
docker image prune -f         # Reclaim dangling images
```

## Ports
| Service     | Host Port | Container Port | Notes |
|-------------|-----------|----------------|-------|
| Frontend    | 8080      | 80             |       |
| Middleware  | 5001      | 5000           | Port 5000 reserved by macOS AirPlay |
| Database    | (none)    | 5432           | Internal to compose network only |
| Ollama      | (none)    | 11434          | Inside middleware container, loopback only |

## Tests
```bash
docker compose exec middleware python -m unittest discover -s tests
```
Fully mocked — no database, no LLM, no network. They live under `middleware/`
because that is the compose build context; a root-level `tests/` could not be
copied into the image.

## When something breaks
Start with [PITFALLS.md](PITFALLS.md) — it covers every issue we expect students to hit (and why), with diagnosis and fix.

## License
MIT — see [LICENSE](LICENSE)

## Dependencies
All dependencies are open source.
- [DEPENDENCIES.md](DEPENDENCIES.md) — human-readable summary
- [SBOM.md](SBOM.md) — formal Software Bill of Materials (pinned versions, digests, PURLs, licenses)
