# Architecture Design Document — Podcast-Agent-Pipeline (PAP)

## System Overview
- **System Nature:** Distributed AI-agentic workflow
- **Primary Objective:** Autonomous ingestion, transcription, analysis, and long-term archival of podcast streams

---

## 1. Node Topology & Hardware Mapping
### Tier 0 — Local Dev Host (MBP M4)
- **Hardware:** Apple Silicon M4 (24 GB RAM)
- **Role:** Authoring, unit testing, container builds (developer laptop)
- **Execution Mode:** Docker Desktop with CPU-only mocks (no GPU passthrough)
- **Workflow:** Build & test locally → push to Git → CI deploys to staging/production

### Tier 1 — Gateway & Ingestion (`etl-node-01`, 192.168.2.81)
- **Hardware:** Trigkey Mini PC (Intel Tiger Lake i5)
- **Role:** 24/7 Always-On gateway for RSS monitoring, audio downloading, Redpanda/message bus, task scheduling (Prefect server/agent)
- **Storage:** Primary SSD for active data; mirrors hot payloads onto shared NFS root `/srv/pap`
- **Energy Mode:** Always-on; lowest power draw handles entry tier processing
- **OS & Access:** Ubuntu Server 24.04; accessible via SSH key pair from MBP M4 over wired Ethernet

### Tier 2 — Logic Orchestrator (`mid-node-01`, 192.168.2.82)
- **Hardware:** MacBook Pro 2019 (Intel i7, 32 GB RAM) stationed lid-closed
- **Role:** Stay-awake orchestrator for audio pre-processing, metadata tagging, Qdrant vector DB, lightweight inference (≤3B models), GitHub Actions runner
- **Status:** Always-on/Stay-awake to absorb daytime workloads and minimize GPU usage
- **Storage:** Hosts Qdrant + metadata SQLite; syncs with `/srv/pap` via SMB/NFS mounts
- **OS & Access:** Ubuntu Server 24.04 (bare-metal) reachable via SSH key from MBP; wired to 2.5 Gbps switch

### Tier 3 — Heavy Inference (`gpu-node-01`, 192.168.2.83)
- **Hardware:** Desktop AMD Ryzen 7700X + AMD Radeon RX 7700 XT (12 GB VRAM)
- **Role:** Faster-Whisper transcription, 32B+ LLM reasoning, GPU-intensive flows
- **Runtime:** ROCm 6.2 with `HSA_OVERRIDE_GFX_VERSION=11.0.1`
- **Status:** Energy-aware schedule (Wake-on-LAN 19:00, suspend 07:00) aligned with Toronto off-peak electricity window
- **Archival Storage:** WD Black 1 TB HDD receives rsynced historical audio, transcripts, inference artifacts from Tier 1/2
- **OS & Access:** Ubuntu Server 24.04; SSH key access via wired Ethernet

All three tier nodes connect via a dedicated 2.5 Gbps Ethernet switch uplinked to the home router with 1 Gbps cable, ensuring low-latency SSH and data transfer.
---

## 2. Agentic Component Architecture (Opencode-Orchestrated)

| Module | Name & Role | Key Details |
| --- | --- | --- |
| 1 | **The Watcher** — Ingestion Agent | Python package (`src/watcher/`) with feed poller, yt-dlp downloader, SQLite ledger, Prefect flow + CLI. Uses Feedparser and respects `PAP_STORAGE_ROOT`. |
| 2 | **The Ear** — Transcription Agent | FastAPI service (`src/ear/`) exposing `/transcribe` backed by stub `TranscriptEngine`. GPU integration via faster-whisper planned for Tier 3 deployment. |
| 3 | **The Brain** — Reasoning Agent | Analyzer (`src/brain/`) calling Ollama (qwen2.5-coder) when available; ships JSON-schema validation + graceful fallback when Ollama missing. |
| 4 | **The Courier** — Notification & Persistence | Service (`src/courier/`) that renders Markdown summaries, writes to `/srv/pap/summaries`, and posts to Telegram via HTTPX (mockable in tests). |
| 5 | **Prefect Pipeline** | `flows/pipeline.py` wires Watcher→Ear→Brain→Courier using Prefect decorators but degrades gracefully if Prefect not installed (used in unit tests). |

---

## 3. Distributed Workflow
1. **Ingest:** Watcher on `etl-node-01` detects new episode → downloads to `/data/podcasts/raw/`.
2. **Dispatch:** Controller checks `ai-node-01`; if offline, issues Wake-on-LAN.
3. **Transcribe:** Controller sends task payload to `ai-node-01`.
4. **Analyze:** `ai-node-01` performs ASR, pipes transcript to LLM, generates JSON summary.
5. **Sync:** Results return to `etl-node-01` for SQLite persistence.
6. **Broadcast:** Courier formats Markdown summary and posts via Telegram Channel API.

### Orchestration & Control
- Prefect server/agent pair runs on `etl-node-01`, orchestrating the six-stage pipeline via Python flows.
- Prefect tasks encapsulate each agent call with parameters for source feed, audio URI, and retry policies.
- Controller node owns the Prefect UI/API; compute node only runs worker tasks, minimizing NAT exposure.

### Error Handling & Recovery
- Prefect retries with exponential backoff for transient network/power issues; all failures logged with contextual metadata.
- Dead-letter queue implemented via SQLite table for manual inspection/replay.
- Wake-on-LAN failures and GPU timeouts trigger Telegram alerts for human intervention.

### Podcast Ingestion (YouTube-First Strategy)
- Watcher consumes YouTube channel RSS (`https://www.youtube.com/feeds/videos.xml?channel_id=...`).
- `yt-dlp` executed with `--extract-audio --audio-format mp3 --audio-quality 5 --write-info-json --download-archive downloaded.txt --sleep-interval 5 --max-sleep-interval 15`.
- Audio + metadata stored under `/srv/pap/raw/<channel>/<upload_date>_<id>.mp3` on the shared NFS volume; metadata JSON powers downstream agents.

### Containerized Execution Model
- All agents run as Docker containers; no bare-metal Python processes in production.
- Local development uses Docker Compose on MBP with CPU-only mocks for GPU services.
- Production/staging deployments run Docker Compose stacks per tier:
  - `etl-node-01` (Tier 1): watcher, courier, Redpanda, Prefect server/worker
  - `mid-node-01` (Tier 2): metadata/tagging microservices, Qdrant, lightweight inference workers, GitHub runner
  - `gpu-node-01` (Tier 3): ear (faster-whisper) + brain (LLM) with GPU passthrough (`--device=/dev/kfd --device=/dev/dri --group-add video`)
- Containers communicate via REST over host network; NFS/SMB volumes mounted into containers.

---

## 4. CI/CD & DevOps Lifecycle
- **Repo:** `boyang/podcast-agent-pipeline`
- **Runner:** Self-hosted GitHub Actions runner on `etl-node-01`
- **Local Dev:** MBP M4 builds + tests via Docker Compose (CPU mocks). No production data processed locally.
- **Testing:** `pytest` covers Watcher/Ear/Brain/Courier modules and a mocked Prefect flow; set `PAP_STORAGE_ROOT` + sandbox `.env` to avoid touching `/srv`. Telegram/yt-dlp/Ollama calls are monkeypatched in tests.
- **Flow:**
  1. Developer verifies changes locally in containers (unit tests, lint, mock flows).
  2. `git push` triggers GitHub Action on `etl-node-01` (staging pipeline).
  3. Action builds multi-arch Docker images (arm64 for dev, x86_64 for deployment) and pushes to GHCR/local registry.
  4. Post-build job deploys to **staging stack** on both nodes (Docker Compose pull/up).
  5. Automated staging runs execute Prefect test flows; Oracle agent reviews results.
  6. On approval, same images are promoted to **production stack** (compose pull/up) with health checks (Prefect, `rocminfo`, `ollama ps`).

---

## 5. Agent Development Configuration (Oh-My-Opencode Ready)
- **LLM Endpoint:** `192.168.2.83:11434` (`OLLAMA_HOST=0.0.0.0`)
- **GPU Env Var:** Always set `HSA_OVERRIDE_GFX_VERSION=11.0.1`
- **File Sharing:** Primary NFSv4 export from `etl-node-01` (`/srv/pap`) mounted on `ai-node-01`; nightly `rsync` mirrors cold data to the WD Black archival disk.
- **Configuration & Secrets:** YAML config files tracked in git; `.env` (bot token, chat ID, API keys) stays local and encrypted for backup.
- **Local Dev/Test:** Docker Compose stack with CPU mocks for faster-whisper & Ollama enables development without GPU access. Only staging/prod nodes run GPU containers.
- **Container Runtime Requirements:** GPU services require Docker runtime privileges + device mounts (`/dev/kfd`, `/dev/dri`); add `--group-add video` and propagate `HSA_OVERRIDE_GFX_VERSION` env var inside containers.
- **Known Pitfalls:**
  - Unit tests run as non-root; set `PAP_STORAGE_ROOT` to a writable temp path (pytest fixture already handles this).
  - `feedparser` and `yt-dlp` must be installed before running Watcher.
  - Telegram bot tokens are mandatory in production but mocked during tests.

---

## 6. Storage, File Sharing & Archival Plan
1. **NFS Service (Primary):**
   - `etl-node-01` hosts `nfs-kernel-server`, exporting `/srv/pap/raw`, `/srv/pap/transcripts`, `/srv/pap/summaries` with `rw,sync,no_root_squash` to LAN clients.
   - Firewall restricts NFS ports to the Bell home subnet; nodes remain private behind NAT.
2. **Client Mounts:**
   - `ai-node-01` uses `nfs-common` and `/etc/fstab` for persistent mounts at `/mnt/pap` (used by Ear/Brain tasks).
3. **Archival Disk:**
   - WD Black 1 TB HDD on `ai-node-01` mounted at `/mnt/pap-archive`; nightly cron-driven `rsync` copies completed audio, transcripts, and LLM outputs for long-term retention.
4. **Fallback Transfers:**
   - `rsync` over SSH serves as manual recovery path if NFS is unavailable.
5. **Integrity & Monitoring:**
   - Prefect tasks emit metrics for transfer latency; Grafana dashboards surface NFS availability and rsync job status.

---

## 7. Tiered Processing & Energy Schedule

### Tiered Processing Logic
1. **Entry Tier (Tier 1 — `etl-node-01`):** Always-on ingest & scheduling. Buffers audio, metadata, and tasks into Redpanda. Only dispatches heavy jobs when Tier 2/3 availability is confirmed.
2. **Logic Tier (Tier 2 — `mid-node-01`):** Performs CPU-friendly workloads (audio pre-processing, tagging, vector writes) and queues GPU workloads. Acts as coordination plane + vector DB.
3. **Power Tier (Tier 3 — `gpu-node-01`):** Executes ASR + large LLM reasoning during off-peak window. Processes queued batches from Tier 2 and streams results back to Tier 1 storage.

### Energy-Aware Scheduling
- **Toronto TOU Off-Peak:** 19:00 – 07:00. GPU node wakes via automated Wake-on-LAN at 19:00 and suspends at 07:00 daily.
- **Night-Time Burst:** Prefect Scheduling Agent (see `AGENTS.md`) drains pending heavy tasks once GPU online; tasks queued outside window remain on Tier 2.
- **Load Shedding:** Light inference (<3B) or urgent metadata tasks must use Tier 2 to avoid unscheduled GPU wake-ups.
- **Telemetry:** Record energy-schedule events; alert if GPU remains powered after 07:05 or fails to wake at 19:05.

---

## 7. Container Architecture

| Service | Node | Base Image | Notes |
| --- | --- | --- | --- |
| Prefect Server + API | `etl-node-01` | `prefecthq/prefect:2-python3.11` | Hosts orchestration UI/API |
| Watcher | `etl-node-01` | `python:3.11-slim` | Feedparser + yt-dlp, binds `/srv/pap/raw` |
| Courier | `etl-node-01` | `python:3.11-slim` | Telegram notifications, Markdown writers |
| Ear | `ai-node-01` | `rocm/dev-ubuntu-22.04:6.2` + Python layer | faster-whisper w/ GPU passthrough |
| Brain | `ai-node-01` | `python:3.11-slim` + Ollama client | Connects to Ollama server (host or container) |
| Ollama Server | `ai-node-01` | Official `ollama/ollama` image | Serves qwen2.5 models |

### Local Compose (MBP)
- Uses same containers where possible but swaps GPU-dependent ones with CPU mocks.
- Volumes map to `./data` directories to simulate NFS.
- Provides a “staging-lite” environment to catch obvious regressions.

---

## 8. Build, Test & Deployment Workflow

1. **Local Build/Test (MBP):**
   - Run `docker compose -f docker-compose.local.yaml up` for Watcher + Prefect + mocks.
   - Execute unit/integration tests inside containers.
2. **CI Build (GitHub Actions on `etl-node-01`):**
   - Build multi-arch images via `docker buildx bake`.
   - Push images to GitHub Container Registry (`ghcr.io/boyang-li/pap/<service>:<sha>`).
3. **Staging Deployment:**
   - Compose files `docker-compose.staging.yml` on both nodes pull `<sha>-staging` tags.
   - Prefect runs test flows end-to-end; Oracle reviews logs/results.
4. **Production Deployment:**
   - Promote tested images by re-tagging `<sha>` → `latest`.
   - Compose stacks restarted with health checks + Telegram notifications.

### Automation Responsibilities
- **You (developer):** Build/test locally, push to Git.
- **CI (self-hosted runner):** Build images, deploy to staging, run tests, ping Oracle for review.
- **Oracle Agent:** Reviews staging results, authorizes production promotion.
