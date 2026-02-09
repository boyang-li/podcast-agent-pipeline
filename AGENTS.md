# AGENTS OPERATIONS MANUAL — Podcast-Agent-Pipeline

## 1. Prefect-Orchestrated Flow
- Controller node (`etl-node-01`) hosts Prefect server/agent. Each module below corresponds to a Prefect task in the Watcher → Ear → Brain → Courier flow.
- All tasks exchange artifacts through the shared NFS root `/srv/pap` (mounted on compute node at `/mnt/pap`).
- Retry policies, telemetry, and alerting are defined at the flow level; modules must emit structured logs and metrics for tracing.

## 2. Shared Contracts
| Item | Requirement |
| --- | --- |
| **Config** | Read from YAML (`config/*.yaml`) with environment overrides + `.env` secrets. No hard-coded paths or tokens. |
| **Paths** | Raw audio `/srv/pap/raw/<channel>/<timestamp>_<id>.mp3`; transcripts `/srv/pap/transcripts/<episode_id>.json`; summaries `/srv/pap/summaries/<episode_id>.md`. |
| **Logging** | JSON logs (level, task_id, episode_id, duration). Send to Loki stack once deployed. |
| **Error Reporting** | Raise structured exceptions; Prefect handles retries. Fatal failures must enqueue record into dead-letter SQLite table. |
| **Security** | Use API keys from `.env`. Never log secrets. |

## 3. Module Guides

### 3.1 Watcher — Ingestion Agent
- **Purpose:** Poll RSS feeds (standard + YouTube), download audio-only assets, emit metadata for downstream tasks.
- **Tech Stack:** Python, Feedparser, yt-dlp, SQLite (download ledger).
- **Inputs:** Feed list (`config/feeds.yaml`), Prefect parameters (channel id, polling interval).
- **Outputs:**
  - Audio file on `/srv/pap/raw/...`
  - Metadata JSON (title, description, publish date, duration, yt video id)
  - SQLite entry referencing download path (prevents duplicates)
- **Key Commands:**
  ```bash
  yt-dlp --extract-audio --audio-format mp3 --audio-quality 5 \
         --write-info-json --download-archive downloaded.txt \
         --sleep-interval 5 --max-sleep-interval 15 \
         --output "/srv/pap/raw/%(channel)s/%(upload_date)s_%(id)s.%(ext)s" URL
  ```
- **Failure Modes & Handling:**
  - HTTP 429 / captcha: exponential backoff + Telegram alert.
  - Download already recorded: yt-dlp exits 0; skip rest of flow.
  - RSS parsing errors: log feed + last GUID, retry with jitter.

### 3.2 Ear — Transcription Agent
- **Purpose:** Convert audio to text using faster-whisper on `ai-node-01`.
- **Surface:** FastAPI (`POST /transcribe`) with request payload { `episode_id`, `audio_path`, `language_hint` }.
- **Outputs:**
  - Transcript JSON (`segments`, `timestamps`, `language`, `confidence`).
  - Intermediate diarization, if enabled, stored under `/srv/pap/transcripts/tmp/` (cleanup after success).
- **Runtime Requirements:**
  - ROCm 6.2, environment var `HSA_OVERRIDE_GFX_VERSION=11.0.1`.
  - Access to `/mnt/pap` NFS mount.
- **Error Handling:**
  - GPU OOM → automatic retry with lower chunk size.
  - API failure surfaces HTTP 5xx + log entry. Prefect retry handles resubmission.
  - Watchdog kills jobs exceeding SLA; record detail in dead-letter table.

### 3.3 Brain — Reasoning Agent
- **Purpose:** Run semantic analysis via Ollama (models: `qwen2.5-coder:7b` for speed, `qwen2.5-coder:32b` for precision).
- **Inputs:** Transcript JSON, metadata (title, guest list, publish date).
- **Outputs:** Structured JSON with:
  - `core_thesis`
  - `timestamped_topics[]`
  - `resources[]` (books, links, mentions)
  - `actionable_insights[]`
- **Prompt Strategy:** Chain-of-thought with explicit instructions to cite timestamps and keep hallucinations low.
- **Resource Constraints:**
  - LLM endpoint `http://192.168.2.82:11434` (`OLLAMA_HOST=0.0.0.0`).
  - Use streaming API to begin parsing responses early.
- **Quality Gates:**
  - Validate JSON schema before emitting.
  - On parse failure, retry with deterministic temperature 0.2.
  - Flag low-confidence sections for manual review (extra metadata field).

### 3.4 Courier — Notification & Persistence
- **Purpose:** Persist final artifacts and broadcast via Telegram.
- **Inputs:** Analysis JSON, summary Markdown template, channel metadata.
- **Outputs:**
  - Markdown summary stored in `/srv/pap/summaries/<episode_id>.md` (also versioned via git if enabled).
  - Telegram message to configured chat ID.
  - Status update row in SQLite (delivered timestamp, message_id).
- **Telegram Usage:**
  - Bot token + chat id loaded from `.env` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).
  - Use MarkdownV2 escaping; include fallback plain-text if formatting fails.
- **Delivery Errors:**
  - Network failures → retry with exponential backoff.
  - Telegram rate limits → respect `retry_after` and push alert.
  - Final failure: record in dead-letter queue + leave TODO for operator.

## 4. Operational Runbooks
1. **Wake-on-LAN Failure**
   - Prefect task times out → send Telegram alert → manual power cycle `ai-node-01`.
2. **NFS Outage**
   - Switch to rsync fallback (`rsync -avz etl-node-01:/srv/pap/raw /mnt/pap-fallback`).
   - Pause Ear/Brain tasks until NFS healthy.
3. **yt-dlp Breakage**
   - Update to latest version; if banned, use VPN/YouTube Premium cookie jar.
4. **Ollama Model Drift**
   - Re-pull base models, regenerate prompts, run regression suite on known episodes.

## 5. Future Enhancements
- Add monitoring hooks (Prometheus exporters for download/transcription latency).
- Introduce queueing layer (Redis or RabbitMQ) if Prefect task volume grows.
- Expand Courier to additional channels (email, RSS, web dashboard).

Maintain this manual as modules evolve. Each code change touching agent behavior must be reflected here.
