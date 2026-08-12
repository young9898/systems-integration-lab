# Systems Integration Lab Environment

## Overview
This repository contains the lab environment for a graduate-level Systems Integration course. Students build a three-tier enterprise architecture using containers, culminating in a fully integrated system with an AI component.

## Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Git](https://git-scm.com/)
- A text editor

**Nothing else is installed on your host machine.** Every process in this lab runs inside a container. See [PITFALLS.md](PITFALLS.md) for why this matters.

## Getting Started
```bash
git clone <repo-url>
cd Systems_Integration_Course
docker compose up --build -d
```
Open `http://localhost:8080` in your browser to see the frontend.

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
curl http://localhost:5001/api/inventory      # Full integration (FE→MW→DB)
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

## When something breaks
Start with [PITFALLS.md](PITFALLS.md) — it covers every issue we expect students to hit (and why), with diagnosis and fix.

## License
MIT — see [LICENSE](LICENSE)

## Dependencies
All dependencies are open source.
- [DEPENDENCIES.md](DEPENDENCIES.md) — human-readable summary
- [SBOM.md](SBOM.md) — formal Software Bill of Materials (pinned versions, digests, PURLs, licenses)
