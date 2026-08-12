# Software Bill of Materials (SBOM)

## Document Information

| Field | Value |
|---|---|
| Project | Systems Integration Lab Environment |
| Document version | 1 |
| Generated | 2026-04-27 |
| Build state | Working-tree state at generation time (post-Step 7a Ollama bundling, model `llama3.2:3b` pulled into volume) |
| Format | Human-readable Markdown; SPDX-style fields |
| Generator | Manual, sourced from `docker compose images`, `pip freeze`, `dpkg-query`, `ollama --version`, `ollama list` against the live stack |
| Document license | MIT (matches project) |

## Scope

This SBOM enumerates every third-party component shipped or installed by the lab's `docker-compose up --build` and the documented one-time `ollama pull` step. It covers:

1. Container base images
2. OS packages added on top of the middleware base image (via `apt`)
3. Application binaries installed into containers (Ollama)
4. Python packages installed into the middleware container
5. AI model weights pulled into the `ollama_data` volume
6. First-party source files in this repository

Out of scope: transitive OS packages baked into upstream base images (inherited from `python:3.12-slim`, `httpd:2.4-alpine`, `postgres:16-alpine`). Their licenses follow Debian and Alpine upstream policy and are documented by their respective distributions.

---

## 1. Container Images

| Image | Tag | Local Image ID | Manifest Digest | Platform | Size | License | PURL |
|---|---|---|---|---|---|---|---|
| `httpd` | `2.4-alpine` | (upstream) | `sha256:968c8b4098fcecb473762b45f6c541a3b2b2cfab2caccb1edbd2cece071ef160` | linux/arm64 | base ~12 MB | Apache-2.0 | `pkg:docker/library/httpd@2.4-alpine` |
| `python` | `3.12-slim` | (upstream) | `sha256:46cb7cc2877e60fbd5e21a9ae6115c30ace7a077b9f8772da879e4590c18c2e3` | linux/arm64 | base ~45 MB | Python-2.0 (PSF) | `pkg:docker/library/python@3.12-slim` |
| `postgres` | `16-alpine` | `4e6e670bb069` | `sha256:4e6e670bb069649261c9c18031f0aded7bb249a5b6664ddec29c013a89310d50` | linux/arm64/v8 | 108 MB | PostgreSQL | `pkg:docker/library/postgres@16-alpine` |
| `systems_integration_course-frontend` | `latest` | `490472505e16` | `sha256:490472505e163ad1fac67ea3b6de9a68014276a08a149c431df6105ec1d24644` | linux/arm64 | 21.2 MB | MIT (this project) | locally built |
| `systems_integration_course-middleware` | `latest` | `1a2b0e3f7e8c` | `sha256:1a2b0e3f7e8c45a61ed26256c25114e43970d46868a1af4a7b96ff1e48cbbe3c` | linux/arm64 | 79.1 MB (compressed) / 342 MB (uncompressed) | MIT (this project) | locally built |

Notes:
- Locally built images are not published to a registry; their manifest digests reflect the most recent local build.
- Upstream digests above were captured during the most recent pull on this build host. They will be re-pulled on student machines and may differ if the upstream tag has been updated.

---

## 2. OS Packages (apt, installed into `middleware` on top of `python:3.12-slim`)

| Package | Version | License | Source | PURL |
|---|---|---|---|---|
| `ca-certificates` | `20250419` | MPL-2.0 (Mozilla CA bundle) + GPL-2.0-or-later (helper scripts) | Debian Trixie | `pkg:deb/debian/ca-certificates@20250419` |
| `curl` | `8.14.1-2+deb13u2` | curl license (MIT-style) | Debian Trixie | `pkg:deb/debian/curl@8.14.1-2+deb13u2` |
| `zstd` | `1.5.7+dfsg-1` | BSD-3-Clause / GPL-2.0 (dual) | Debian Trixie | `pkg:deb/debian/zstd@1.5.7%2Bdfsg-1` |

Transitive apt dependencies (libcurl4t64, libgnutls30t64, libidn2-0, libk5crypto3, libkrb5-3, libldap2, libnghttp2, libnghttp3, libpsl5t64, libssh2-1t64, libtasn1-6, librtmp1, libsasl2-2, libunistring5, libbrotli1, libkeyutils1, libcom-err2, libkrb5support0, libsasl2-modules-db, libp11-kit0) are pulled in automatically by Debian's package manager. Each carries its own upstream license; in aggregate they are LGPL/MIT/BSD/zlib-style. Full enumeration available via `docker compose exec middleware dpkg-query -W -f='${Package}\t${Version}\n'`.

---

## 3. Application Binaries

| Binary | Version | Location in image | License | Source |
|---|---|---|---|---|
| `ollama` | `0.21.2` | `/usr/local/bin/ollama` + `/usr/local/lib/ollama/` | MIT | https://github.com/ollama/ollama |

Notes:
- Installed via the official `https://ollama.com/install.sh` script during image build.
- The CUDA acceleration libraries (`/usr/local/lib/ollama/cuda_v12`, `cuda_v13`) are deleted in the same build layer to remove ~3.6 GB of unused GPU runtime. CPU inference is unaffected.

---

## 4. Python Packages (installed into `middleware` via pip)

### Direct dependencies (pinned in `middleware/requirements.txt`)

| Package | Installed Version | License | PURL |
|---|---|---|---|
| Flask | 3.1.3 | BSD-3-Clause | `pkg:pypi/flask@3.1.3` |
| flask-cors | 5.0.1 | MIT | `pkg:pypi/flask-cors@5.0.1` |
| psycopg | 3.2.13 | LGPL-3.0-or-later | `pkg:pypi/psycopg@3.2.13` |
| psycopg-binary | 3.2.13 | LGPL-3.0-or-later | `pkg:pypi/psycopg-binary@3.2.13` |
| ollama (Python client) | 0.4.9 | MIT | `pkg:pypi/ollama@0.4.9` |

### Transitive dependencies (pulled in by pip)

| Package | Installed Version | License | PURL |
|---|---|---|---|
| annotated-types | 0.7.0 | MIT | `pkg:pypi/annotated-types@0.7.0` |
| anyio | 4.13.0 | MIT | `pkg:pypi/anyio@4.13.0` |
| blinker | 1.9.0 | MIT | `pkg:pypi/blinker@1.9.0` |
| certifi | 2026.4.22 | MPL-2.0 | `pkg:pypi/certifi@2026.4.22` |
| click | 8.3.3 | BSD-3-Clause | `pkg:pypi/click@8.3.3` |
| h11 | 0.16.0 | MIT | `pkg:pypi/h11@0.16.0` |
| httpcore | 1.0.9 | BSD-3-Clause | `pkg:pypi/httpcore@1.0.9` |
| httpx | 0.28.1 | BSD-3-Clause | `pkg:pypi/httpx@0.28.1` |
| idna | 3.13 | BSD-3-Clause | `pkg:pypi/idna@3.13` |
| itsdangerous | 2.2.0 | BSD-3-Clause | `pkg:pypi/itsdangerous@2.2.0` |
| Jinja2 | 3.1.6 | BSD-3-Clause | `pkg:pypi/jinja2@3.1.6` |
| MarkupSafe | 3.0.3 | BSD-3-Clause | `pkg:pypi/markupsafe@3.0.3` |
| pydantic | 2.13.3 | MIT | `pkg:pypi/pydantic@2.13.3` |
| pydantic-core | 2.46.3 | MIT | `pkg:pypi/pydantic-core@2.46.3` |
| typing-extensions | 4.15.0 | Python-2.0 (PSF) | `pkg:pypi/typing-extensions@4.15.0` |
| typing-inspection | 0.4.2 | MIT | `pkg:pypi/typing-inspection@0.4.2` |
| Werkzeug | 3.1.8 | BSD-3-Clause | `pkg:pypi/werkzeug@3.1.8` |

---

## 5. AI Model

| Component | Tag | Quantization | Local Digest | Size on disk | License | Source |
|---|---|---|---|---|---|---|
| Llama 3.2 Instruct | `llama3.2:3b` | Q4_K_M (default Ollama 3b tag) | `a80c4f17acd5` | 2.0 GB | Llama 3.2 Community License (permissive for educational use) | https://ollama.com/library/llama3.2 |

Storage: Docker named volume `ollama_data` mounted at `/root/.ollama` inside the middleware container. **Not** in this repository, **not** on the host filesystem outside Docker's managed volume.

---

## 6. First-Party Source Files (this repository)

All released under MIT (see `LICENSE`).

| Path | Type | Purpose |
|---|---|---|
| `README.md` | Documentation | Student-facing setup and operation guide |
| `DEPENDENCIES.md` | Documentation | Human-readable summary of dependencies |
| `PITFALLS.md` | Documentation | Troubleshooting guide |
| `SBOM.md` | Documentation | This file |
| `LICENSE` | License | MIT license text |
| `docker-compose.yml` | Configuration | Service orchestration |
| `frontend/Dockerfile` | Configuration | Frontend image definition |
| `frontend/index.html` | Source | Chat UI |
| `middleware/Dockerfile` | Configuration | Middleware image definition |
| `middleware/entrypoint.sh` | Source | Multi-process startup script (ollama serve + Flask) |
| `middleware/app.py` | Source | Flask application |
| `middleware/requirements.txt` | Configuration | Python dependency manifest |
| `db/init.sql` | Source | Postgres schema + seed data |

---

## 7. Caveats and Limitations

1. **Version drift on rebuild.** `requirements.txt` uses major-version constraints (`flask==3.1.*`), not exact pins. Future builds may install patch updates. To produce a reproducible SBOM, lock the manifest with `pip freeze > requirements.lock` and update this document.
2. **Upstream tag mutability.** Container image tags (`postgres:16-alpine`, etc.) point to manifests that the upstream maintainer may update. Pinning to a digest (`postgres@sha256:...`) in `docker-compose.yml` would freeze them — currently we accept the convenience of tag-based pulls.
3. **Transitive OS packages.** Section 2 lists only directly-installed apt packages. The full set of OS components in each container's filesystem (inherited from upstream base images) is not enumerated here. Generating that requires running `dpkg-query -W` (Debian) or `apk info -v` (Alpine) inside each container.
4. **License accuracy.** Licenses for Python packages were sourced from the package metadata as of the date of this SBOM. They are correct to the best of available metadata but should be verified against each project's `LICENSE` file before any redistribution decision.
5. **Vulnerability scanning.** This SBOM is a manifest, not a vulnerability report. Run a scanner (e.g. `docker scout cves`, `trivy image`, `grype`) against each image to check for known CVEs.

---

## 8. Updating This Document

This SBOM should be regenerated whenever any of the following change:
- A container base image tag in `docker-compose.yml` or any Dockerfile
- A line in `middleware/requirements.txt`
- An apt package in `middleware/Dockerfile`
- The Ollama version (currently the install script pulls latest)
- The course default model

To regenerate the version/digest tables, run the discovery commands documented in §Document Information against a fresh `docker compose up --build -d`.
