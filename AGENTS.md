# AGENTS OPERATIONS MANUAL — Podcast-Agent-Pipeline

## 1. Prefect-Orchestrated Flow
- Controller node (`etl-node-01`) hosts Prefect server/agent plus the Docker Compose stack for Watcher/Courier/Prefect services. Each module below corresponds to a Prefect task in the Watcher → Ear → Brain → Courier flow.
- All tasks exchange artifacts through the shared NFS root `/srv/pap` (mounted on compute node at `/mnt/pap`); containers mount the same paths per `docs/system-specs.md` §6.
- Retry policies, telemetry, and alerting are defined at the flow level; modules must emit structured logs and metrics for tracing.
- Staging and production follow the same container topology as documented in `docs/system-specs.md` §7–§8.

## 2. Shared Contracts
| Item | Requirement |
| --- | --- |
| **Config** | Read from YAML (`config/*.yaml`) with environment overrides + `.env` secrets. No hard-coded paths or tokens. (See `docs/system-specs.md` §5 for environment layout.) |
| **Paths** | Refer to `docs/system-specs.md` §6 for canonical storage paths (raw audio, transcripts, summaries). Set `PAP_STORAGE_ROOT` in tests/local runs. |
| **Energy Policy** | Follow Toronto TOU schedule (off-peak 19:00–07:00). Queue GPU-bound work until Tier 3 is online; prioritize Tier 2 for lightweight tasks. All tier nodes run Ubuntu Server 24.04 with wired 2.5 Gbps interconnect. |
| **Logging** | JSON logs (level, task_id, episode_id, duration). Send to Loki stack once deployed. |
| **Error Reporting** | Raise structured exceptions; Prefect handles retries. Fatal failures must enqueue record into dead-letter SQLite table. |
| **Security** | Use API keys from `.env`. Never log secrets. |

## 3. Module Guides

### 3.1 Watcher — Ingestion Agent (Docker service: `watcher`, Tier 1 `etl-node-01`)
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
- **Pitfalls & Lessons:**
  - The module depends on `feedparser` and `yt-dlp`. Missing deps caused early test failures—ensure they’re installed before invoking Watcher.
  - Tests cannot write to `/srv`; use `PAP_STORAGE_ROOT` to redirect outputs during local runs.
  - Prefect decorators are optional; when Prefect isn’t installed the flow still runs synchronously—mirror this pattern for new tasks.

### 3.2 Ear — Transcription Agent (Docker service: `ear`, Tier 3 `gpu-node-01`)
- **Purpose:** Convert audio to text using faster-whisper on `ai-node-01`.
- **Surface:** FastAPI (`POST /transcribe`) with request payload { `episode_id`, `audio_path`, `language_hint` }.
- **Outputs:**
  - Transcript JSON (`segments`, `timestamps`, `language`, `confidence`).
  - Intermediate diarization, if enabled, stored under `/srv/pap/transcripts/tmp/` (cleanup after success).
- **Runtime Requirements:**
  - ROCm 6.2, environment var `HSA_OVERRIDE_GFX_VERSION=11.0.1`.
  - Access to `/mnt/pap` NFS mount (mounted into container with GPU passthrough; see `docs/system-specs.md` §7).
- **Error Handling:**
  - GPU OOM → automatic retry with lower chunk size.
  - API failure surfaces HTTP 5xx + log entry. Prefect retry handles resubmission.
  - Watchdog kills jobs exceeding SLA; record detail in dead-letter table.
- **Pitfalls & Lessons:**
  - Local FastAPI tests rely on CPU mocks; never assume ROCm presence during development.
  - Always expose `/health` and `/transcribe` endpoints—pytest covers both.
  - When swapping in faster-whisper, maintain current Pydantic response schema to avoid breaking downstream consumers/tests.

### 3.3 Brain — Reasoning Agent (Docker service: `brain`, Tier 3 `gpu-node-01`)
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
- **Pitfalls & Lessons:**
  - Ollama client is optional; fallback path must stay deterministic for tests.
  - Use `model_dump()` (Pydantic v2) instead of deprecated `dict()` when exporting results.
  - Mocking Ollama is mandatory in CI—monkeypatch network calls when writing new tests.

### 3.4 Courier — Notification & Persistence (Docker service: `courier`, Tier 1 `etl-node-01`)
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
- **Pitfalls & Lessons:**
  - Telegram API errors (404) surfaced during tests; mock `send_message` in unit tests to avoid hitting real endpoints.
  - Markdown renderer uses UTC timestamps; switched to timezone-aware `datetime.now(timezone.utc)` to avoid warnings.
  - `PAP_STORAGE_ROOT` must be writable before persisting summaries.

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

## 6. Testing & Verification
| Agent | Local (MBP, Docker CPU mocks) | Staging / Production |
| --- | --- | --- |
| Watcher | `docker compose -f docker/docker-compose.local.yml run watcher pytest -k watcher` (uses mock feeds) | Prefect staging flow `watcher_smoke` downloads sample YouTube feed; verifies ledger rows + file hashes |
| Ear | `docker compose ... run ear-mock pytest -k ear` (CPU mock) | GPU container runs `pytest -k ear_gpu` + Prefect flow `ear_transcription_smoke` on golden audio |
| Brain | `docker compose ... run brain-mock pytest -k brain` (mock prompts) | Prefect flow `brain_summary_smoke` validates schema + timestamp coverage |
| Courier | `docker compose ... run courier pytest -k courier` | Prefect flow `courier_delivery_smoke` sends to Telegram sandbox + checks `/srv/pap/summaries` output |

- **Verification Loop:** CI deploys to staging first; Prefect smoke flows must pass before promoting images to production (see `docs/system-specs.md` §8).
- **Manual Review:** Oracle agent reviews staging artifacts/logs and signs off prior to production rollout.

Maintain this manual as modules evolve. Each code change touching agent behavior must be reflected here.
### 3.5 Scheduling Agent — Energy-Aware Coordinator (Prefect + Redpanda, Tier 1/Tier 2)
- **Purpose:** Enforce TOU-aware execution by deciding when heavy jobs move from Tier 2 queues to Tier 3 GPU workers.
- **Inputs:** Task metadata from Watcher/Logic tier; Redpanda events; TOU timetable.
- **Outputs:** Wake-on-LAN payloads at 19:00, suspend commands at 07:00, Prefect task releases for GPU queue, Telegram alerts for schedule drift.
- **Behavior:**
  - Maintain FIFO queues for GPU workloads on `mid-node-01`; only release when GPU online.
  - Force light inference (<3B) to remain on `mid-node-01` unless backlog > threshold.
  - Emit audit logs whenever GPU wake or suspend fails; escalate to operator.
### 3.5 Scheduling Agent — Energy-Aware Coordinator (Prefect + Redpanda, Tier 1/Tier 2)
- **Pitfalls & Lessons:** Prefect workers must respect concurrency limits; GPU pool should remain at 1 to avoid VRAM exhaustion. Automation scripts should log when WOL fails so tests can assert on notifications.
