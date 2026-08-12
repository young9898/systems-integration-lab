# PITFALLS

Common mistakes when building this lab stack, with diagnosis and fix.
Read this when something breaks, or before something does.

---

## 1. Don't install dependencies on your host machine

**Symptom**: A lab step says you need Ollama, Postgres, or Python. You install it on your Mac/Windows/Linux and connect to it from the container.

**Why it's wrong**: This is a course on system integration, and the entire point of containers in the lab is to remove "works on my machine" variance. Every process in this stack runs **inside the docker-compose stack**. Your host machine should have only Docker Desktop and git installed. Nothing else.

**The temptation**: Installing on the host is faster. Native install on a Mac uses GPU acceleration. You'll see a real performance gain.

**Why you do it the hard way anyway**:
- Your stack must work on every classmate's laptop, on every grader's laptop, in every CI environment. A host dependency breaks all of that.
- "Containers are the lab tool, not the lesson" — but only if you respect the boundary. Once you reach across to the host, you've lost the lesson.

**Rule**: If a process is part of the lab, it lives in a container. Period.

---

## 2. The middleware container runs TWO processes (Flask + Ollama)

**Symptom**: You're not sure where Ollama belongs. You ask "is it tier 4?" or "should it be its own container?"

**Diagnosis**: Neither. The course is **three-tier**: presentation, application logic, data. The LLM is a *capability* of the application logic tier — like a calculator on a desk. The desk doesn't become a 4th tier because you put a calculator on it.

**Fix**: Bundle Ollama and Flask into the same container. Use a shell entrypoint that starts `ollama serve` in the background, waits until it's ready, then starts Flask in the foreground.

```sh
#!/bin/sh
set -e
ollama serve &
until curl -fs http://localhost:11434/api/tags >/dev/null 2>&1; do
    sleep 1
done
exec python app.py
```

**Why it's defensible** (this comes up): Multi-process containers are an anti-pattern in production — you'd run the LLM inference service separately for scaling. For a teaching lab on a student laptop, collapsing both processes into one container preserves the architectural lesson (three tiers = three containers) and reflects the logical reality (the LLM is part of the brain, not its own brain).

---

## 3. Alpine vs glibc: Ollama will not install on Alpine Linux

**Symptom**: You base middleware on `python:3.12-alpine` (smallest Python image). You add Ollama. The install script appears to succeed. Then `ollama serve` fails to start, or the binary won't run at all.

**Diagnosis**: Alpine uses **musl libc**. Ollama's binary is compiled against **glibc**. Same architecture, incompatible C library. The binary loads but cannot link.

**Fix**: Use `python:3.12-slim` (Debian-based, glibc) as the base.

**Cost**: ~100 MB more image space. Worth it.

**Lesson**: Base image choice is not interchangeable. Read what your dependencies require. "The smallest base image" is not always the right answer.

---

## 4. The Ollama install script silently requires zstd

**Symptom**: Your Dockerfile installs Ollama via the official script. Build fails with:
```
ERROR: This version requires zstd for extraction. Please install zstd and try again
```

**Diagnosis**: Recent Ollama releases ship the binary as a zstd-compressed archive. The base Debian/Ubuntu image doesn't include zstd by default. The install script tells you exactly what to do.

**Fix**: Add `zstd` to your `apt-get install` line:

```dockerfile
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates zstd \
 && curl -fsSL https://ollama.com/install.sh | sh
```

**Lesson**: When an installer fails, **read the error message before guessing**. The fix was in the message.

---

## 5. The default Ollama install drops 3.6 GB of unused GPU libraries

**Symptom**: Your middleware image is 6+ GB after adding Ollama, even before pulling a model.

**Diagnosis**: Run this inside the container:
```sh
du -sh /usr/local/lib/ollama/*
```

You will see:
```
2.5G    /usr/local/lib/ollama/cuda_v12
1.1G    /usr/local/lib/ollama/cuda_v13
```

The Ollama install script bundles NVIDIA CUDA runtime libraries by default for Linux+NVIDIA hosts. Docker Desktop on Mac and Windows **cannot pass NVIDIA GPUs through to containers**, so these libraries are dead weight on every student's machine.

**Fix**: Delete them in the same `RUN` layer as the install:

```dockerfile
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates zstd \
 && curl -fsSL https://ollama.com/install.sh | sh \
 && rm -rf /usr/local/lib/ollama/cuda_v12 /usr/local/lib/ollama/cuda_v13 \
 && rm -rf /var/lib/apt/lists/*
```

**Result**: middleware image drops from ~6 GB to ~340 MB. Inference runs on CPU regardless, so nothing changes functionally.

**Lesson**: A default install is for the maintainer's convenience, not yours. Inspect what your image contains. The same `du -sh` trick works on any container directory.

---

## 6. Build cache and dangling images accumulate forever

**Symptom**: Disk space is filling up, but you only have three small containers running. Docker Desktop's disk number keeps growing.

**Diagnosis**: Every time you run `docker compose up --build`, Docker creates new image layers and tags them as the new image. The old image becomes "dangling" (untagged but still on disk). Build cache layers accumulate too. Run:

```sh
docker system df
```

You will see entries under "Build Cache" and possibly "Images" with reclaimable space.

**Fix** (safe — does not touch running containers, named images, or volumes):

```sh
docker builder prune -f      # clears build cache
docker image prune -f        # clears dangling images
```

**Don't run** `docker system prune -a` carelessly — it will delete *all* unused images, including ones you'd have rebuilt cache from.

**Lesson**: Disk space management is part of the lab. Run `docker system df` periodically. Reclaim before the headline number freaks you out.

---

## 7. Docker Desktop's RAM and disk numbers are misleading

**Symptom**: Docker Desktop shows 7+ GB of RAM "in use" and 11+ GB of disk after building the stack, but your containers are clearly small.

**Diagnosis**: The displayed numbers are **VM-level**, not container-level.

For RAM: Docker Desktop runs a Linux VM. Linux uses free RAM as filesystem cache (because empty RAM is wasted RAM). After heavy I/O like a build, most of that "used" memory is page cache that will be evicted instantly under pressure. Check the actual working set inside the container:

```sh
docker stats --no-stream
docker compose exec middleware cat /proc/meminfo | head -5
```

Look at `MemAvailable`, not `MemFree`. The cached portion is reclaimable.

For disk: the headline number includes images, build cache, dangling images, volumes, and the VM's own filesystem overhead. Get the real breakdown with:

```sh
docker system df
docker system df -v   # verbose, per-volume and per-image
```

**Lesson**: Don't trust headline metrics without breaking them down. This is true for every dashboard you'll ever read.

---

## 8. "Diagnose before act" beats "try and retry"

**Symptom**: A command fails. You change something. You run it again. It fails again. You change something else. Repeat.

**Why this is bad**: You are not learning what broke. You are not narrowing the cause. You are just hoping.

**Fix**:
1. Read the actual error message. The fix is usually in it (see #4).
2. Form a **hypothesis** about why it failed. State it out loud.
3. Test the hypothesis with the **smallest possible isolated check** — one command, one component.
4. Only modify code or retry once you know the root cause.

**Rule**: One retry on trivially obvious causes (typo, wrong path). After that, stop and diagnose. Never modify a script and re-run it in the same step without thinking.

---

## 9. The first LLM response after a stack restart is slow — that's expected

**Symptom**: You hit `/api/ask` (or send a chat message) for the first time after `docker compose up`. The response takes 5–40 seconds. Subsequent calls are 1–10 seconds. Eventually it gets slow again.

**Diagnosis**: Ollama loads the model from disk into RAM only when a request asks for it. That **cold load** is the slow part — the inference itself, after the model is loaded, is fast. The model stays resident for `OLLAMA_KEEP_ALIVE=5m` (default) of idle time, then unloads, and the next request pays the load cost again.

You can confirm by watching:
```bash
docker stats --no-stream    # middleware RAM jumps when model loads
docker compose logs middleware --tail 20    # ollama logs the load events
```

**Fix** (none needed — this is normal): if you want to eliminate the cold start at the cost of permanently holding ~3 GB RAM, set `OLLAMA_KEEP_ALIVE=24h` (or `-1` for forever) in the middleware's environment in `docker-compose.yml`. Don't do this on a memory-constrained machine.

**Why latency varies so widely**: the cold-load cost is dominated by your CPU's memory bandwidth and core count. An M-series Mac loads `llama3.2:3b` in ~3–8 sec; an older 8 GB Intel laptop may need 20–40 sec. After load, inference also varies: M-series ≈ 30–50 tokens/sec, older Intel ≈ 5–10 tokens/sec. A 100-token answer is the difference between feeling instant and waiting 20 seconds.

**Lesson**: not every "slow" is a bug. Some are physics. Distinguish *cold-load* latency (model fetching from disk) from *inference* latency (CPU doing matrix multiplications) before you go optimizing.

---

## 10. The chat says "no valid JSON response" — you skipped the model pull

**Symptom**: the stack builds and starts, `curl localhost:5001/api/health` and
`/api/inventory` both return clean JSON, the page loads at `localhost:8080` — but
every chat message fails.

**Cause**: `docker compose up` does not download the model. That is a separate,
one-time command, and nothing about a healthy-looking stack tells you it is
missing. The model lives in the `ollama_data` volume, so it also disappears if you
ever run `docker compose down -v`.

**Fix**:
```bash
docker compose exec middleware ollama pull llama3.2:3b
docker compose exec middleware ollama list      # confirm it is there
```

**Why this trap is worse than it looks**: before the error handling was added,
`ollama.chat` failing produced an unhandled exception, Flask returned an HTML
error page, and the browser's `res.json()` threw on the HTML. The UI then reported
"could not reach middleware" — a *false* diagnosis. The middleware had been
reached and had answered; only the model was missing. Readers lost time debugging
ports, CORS, and compose networking that were all fine.

The general lesson is worth more than the fix: **an error message that names the
wrong layer is more expensive than no error message at all.** When a diagnosis
points somewhere, verify the pointer before you trust it — check
`docker compose logs middleware --tail 30` and see what the server actually said.

## 11. `curl … | sh` builds a broken image and reports success

**Symptom**: `docker compose build` completes cleanly. The stack starts. Then the
middleware log loops forever on:
```
./entrypoint.sh: 4: ollama: not found
Waiting for Ollama to be ready...
```
Flask never starts, so `/api/health` returns nothing and every request times out.

**Cause**: the Dockerfile installed Ollama with `curl -fsSL … | sh`. The download
returned HTTP 503. Curl failed — but **a pipeline's exit status is the last
command's**, and `sh` handed an empty stdin does nothing and exits 0. The `&&`
chain saw success, the layer was committed, and Docker tagged an image with no
`ollama` binary in it.

The build log contains the evidence, one line among hundreds:
```
curl: (22) The requested URL returned error: 503
```
Nothing else flags it, and the failure only appears later, in a different
container, as a symptom that looks nothing like a download problem.

**Fix** — download first, run second, and demand a receipt:
```dockerfile
RUN curl -fsSL https://ollama.com/install.sh -o /tmp/ollama-install.sh \
 && sh /tmp/ollama-install.sh \
 && rm -f /tmp/ollama-install.sh \
 && command -v ollama        # fails the build if no binary landed
```
`command -v ollama` is the important line. Installing something is not evidence it
installed; checking that the artifact exists is.

**The general lesson**: any `A | B` in a Dockerfile hides A's failure. If you must
pipe, use `SHELL ["/bin/bash", "-o", "pipefail", "-c"]`. And verify the artifact
you were trying to produce actually exists before the layer is committed — a
transient network blip during a build should break the build, not ship.

## 12. Apache returns 403 for a file that is plainly there

**Symptom**: `curl localhost:8080` returns 403. The file is in the image; `ls`
inside the container shows it. The Apache error log says:
```
(13)Permission denied: AH00132: file permissions deny server access:
/usr/local/apache2/htdocs/index.html
```

**Cause**: `COPY` preserves the **host** file's permission bits. If your checkout
has restrictive modes — files under iCloud Drive are created `0600`, and some
umask settings do the same — the file arrives in the image readable only by root.
Apache runs as `www-data` and cannot open it. Nothing about the Dockerfile,
Compose, or Apache config is wrong; the build simply inherited the permissions of
whichever machine ran it, which is why it can work for one person and fail for the
next from identical source.

**Fix**:
```dockerfile
COPY index.html /usr/local/apache2/htdocs/index.html
RUN chmod 644 /usr/local/apache2/htdocs/index.html
```
Normalise permissions in the image rather than depending on the host's. (With
BuildKit, `COPY --chmod=644` does the same in one step.)

**Diagnostic worth internalising**: 403 with the file present means *permissions*,
not configuration. Read the error log before touching the config — `docker compose
logs frontend --tail 20` names the exact file and the exact reason.

## Quick troubleshooting commands

```sh
# Stack health
docker compose ps                       # are containers running?
curl -s localhost:5001/api/health        # is middleware responding?
docker compose logs <service> --tail 30  # what did it say?

# Resource accounting
docker stats --no-stream                 # live container RAM/CPU
docker system df                         # disk by category
docker images --format "{{.Repository}}\t{{.Size}}"

# Inside a container
docker compose exec <service> sh         # shell into a container
docker compose exec <service> du -sh /path

# Cleanup
docker builder prune -f                  # safe
docker image prune -f                    # safe (dangling only)
docker compose down                      # stop stack, keep volumes
docker compose down -v                   # stop stack, DELETE volumes
```
