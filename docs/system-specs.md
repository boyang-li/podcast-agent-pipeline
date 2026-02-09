# Architecture Design Document — Podcast-Agent-Pipeline (PAP)

## System Overview
- **System Nature:** Distributed AI-agentic workflow
- **Primary Objective:** Autonomous ingestion, transcription, analysis, and long-term archival of podcast streams

---

## 1. Node Topology & Hardware Mapping
### Controller Node — `etl-node-01`
- **Hardware:** Trigkey Mini PC (Intel Tiger Lake i5)
- **Role:** Orchestration, ingestion, persistence, notifications
- **Operating State:** 24/7 always-on
- **Storage:** Primary SSD (active data); future WD Black HDD (archival)

### Compute Node — `ai-node-01` (aka `gpu-node-01`)
- **Hardware:** AMD Ryzen 7700X + AMD Radeon RX 7700 XT (12 GB VRAM)
- **Role:** Heavy inference (ASR & LLM)
- **Operating State:** On-demand via Wake-on-LAN
- **Runtime:** ROCm 6.2 with `HSA_OVERRIDE_GFX_VERSION=11.0.1`
- **Archival Storage:** Planned WD Black 1 TB HDD receives rsynced historical audio, transcripts, and inference artifacts from the controller node.

---

## 2. Agentic Component Architecture (Opencode-Orchestrated)

| Module | Name & Role | Key Details |
| --- | --- | --- |
| 1 | **The Watcher** — Ingestion Agent | Python (Feedparser), yt-dlp, SQLite. Polls standard + YouTube RSS feeds, downloads audio-only artifacts via `yt-dlp --extract-audio`, stores channel metadata + JSON payloads. |
| 2 | **The Ear** — Transcription Agent | faster-whisper (ROCm) on `ai-node-01`, exposed via REST (`faster-whisper-server`). Converts speech to text. |
| 3 | **The Brain** — Reasoning Agent | Ollama (qwen2.5-coder 7b/32b). Performs semantic analysis, chain-of-thought prompting for core thesis, timestamped topics, resources, actionable insights. |
| 4 | **The Courier** — Notification & Persistence | Telegram Bot API + git-based versioning. Uses pre-existing bot + chat ID (stored in `.env`) for summaries, status pings, and alert routing. |

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

---

## 4. CI/CD & DevOps Lifecycle
- **Repo:** `boyang/podcast-agent-pipeline`
- **Runner:** Self-hosted GitHub Actions runner on `etl-node-01`
- **Flow:**
  1. `git push` triggers GitHub Action
  2. Action builds/updates Docker images on `etl-node-01`
  3. `etl-node-01` deploys to `ai-node-01` via Ansible or SSH remote exec
  4. Health checks: `rocminfo`, `ollama ps`

---

## 5. Agent Development Configuration (Oh-My-Opencode Ready)
- **LLM Endpoint:** `192.168.2.82:11434` (`OLLAMA_HOST=0.0.0.0`)
- **GPU Env Var:** Always set `HSA_OVERRIDE_GFX_VERSION=11.0.1`
- **File Sharing:** Primary NFSv4 export from `etl-node-01` (`/srv/pap`) mounted on `ai-node-01`; nightly `rsync` mirrors cold data to the WD Black archival disk.
- **Configuration & Secrets:** YAML config files tracked in git; `.env` (bot token, chat ID, API keys) stays local and encrypted for backup.
- **Local Dev/Test:** Docker Compose stack with CPU mocks for faster-whisper & Ollama enables development without GPU access.

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
