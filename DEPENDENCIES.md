# Third-Party Dependencies & Licenses

All dependencies used in this course module are open source. This file tracks each first-class dependency and its license.

## Container images & runtimes

| Dependency | Purpose | License | URL |
|---|---|---|---|
| Docker Engine | Container runtime | Apache 2.0 | https://github.com/moby/moby |
| Docker Compose | Multi-container orchestration | Apache 2.0 | https://github.com/docker/compose |
| Apache HTTP Server | Frontend web server (Container 1) | Apache 2.0 | https://httpd.apache.org/ |
| Python 3.12 (slim) | Middleware runtime (Container 2) | PSF License (permissive) | https://www.python.org/ |
| PostgreSQL 16 | Relational database (Container 3) | PostgreSQL License (permissive) | https://www.postgresql.org/ |
| Ollama | Local LLM serving, bundled in middleware container | MIT | https://github.com/ollama/ollama |

## Python packages (in middleware/requirements.txt)

| Package | Purpose | License |
|---|---|---|
| Flask | Web framework | BSD-3-Clause |
| Flask-CORS | Cross-origin request handling | MIT |
| psycopg[binary] | PostgreSQL driver (binary build) | LGPL-3.0 |
| ollama | Python client for the Ollama HTTP API | MIT |

Transitive dependencies (pydantic, httpx, jinja2, werkzeug, etc.) are pinned automatically by pip during build. Their licenses are MIT / BSD / Apache 2.0 — all permissive.

## LLM model

| Model | Size | Quantization | License | URL |
|---|---|---|---|---|
| `llama3.2:3b` | ~2 GB | Q4_K_M | Llama 3.2 Community License (permissive for educational use) | https://ollama.com/library/llama3.2 |

The model is **not** committed to the repo. It is pulled into the `ollama_data` Docker volume on first setup via `docker compose exec middleware ollama pull llama3.2:3b`.

## Notes
- All container images used are official or well-maintained community images
- No proprietary APIs, services, or API keys required
- Any new dependency must be added here with its license before being merged
