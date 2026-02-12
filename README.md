# Podcast Agent Pipeline

Prefect-orchestrated home lab workflow that ingests podcast feeds (RSS + YouTube), transcribes them with faster-whisper, summarizes via Ollama, and publishes Markdown/Telegram updates.

## Phase 0 Bootstrap Checklist
1. **Install Docker Desktop** on the MBP M4 (local dev host).
2. **Install Python 3.10+ & uv** for tooling scripts (optional but helpful):
   ```bash
   uv pip install -r pyproject.toml  # or: uv pip install .
   ```
3. **Copy templates**:
   ```bash
   cp .env.example .env
   cp config/feeds.yaml.example config/feeds.yaml
   ```
4. **Populate .env** with Prefect API URL, Telegram bot credentials, Ollama endpoint, and agent API keys.
5. **Run local Docker stack (CPU mocks only)**:
   ```bash
   docker compose -f docker/docker-compose.local.yml up --build
   ```
6. **Prep tiered nodes** (see `docs/system-specs.md` §1 & §7 for hardware/IP map) and copy `.env` to each host.
6. **Review docs**:
   - `docs/system-specs.md` – architecture & hardware specs
   - `docs/development-roadmap.md` – phased implementation plan
   - `AGENTS.md` – operational contracts per module
   - `CLAUDE.md` – collaboration guidelines

## Repository Layout
```
.
├── src/
│   ├── watcher/
│   ├── ear/
│   ├── brain/
│   └── courier/
├── flows/            # Prefect flow definitions
├── config/           # YAML configs (.example provided)
├── scripts/          # Operational helpers (rsync, WOL, etc.)
├── docker/           # docker-compose files + Dockerfiles
├── docs/             # Specs + roadmap
├── .env.example
└── pyproject.toml
```

## Development & Deployment Workflow
1. **Develop locally** using Docker Desktop + `docker/docker-compose.local.yml`. GPU-heavy agents run as CPU mocks; focus on unit tests and integration flows without hardware dependencies.
2. **Push to GitHub** only after local checks pass.
3. **Self-hosted GitHub Action on `etl-node-01`** builds multi-arch Docker images, pushes to GHCR/local registry, and deploys to staging stacks across Tier 1–3.
4. **Staging verification** runs Prefect flows end-to-end on real hardware; Oracle agent reviews logs/results.
5. **Promote to production** by reusing the tested images (compose pull/up) with health checks + Telegram alerts.

### Cluster Deployment Cheatsheet
```bash
# Tier 1 (etl-node-01)
docker compose -f docker/staging/tier1.yml up -d --remove-orphans

# Tier 2 (mid-node-01)
docker compose -f docker/staging/tier2.yml up -d --remove-orphans

# Tier 3 (gpu-node-01) – run after 19:00 off-peak wake
docker compose -f docker/staging/tier3.yml up -d --remove-orphans

# Production rollout after staging sign-off
IMAGE_TAG=latest docker compose -f docker/prod/tier1.yml up -d --pull always
IMAGE_TAG=latest docker compose -f docker/prod/tier2.yml up -d --pull always
IMAGE_TAG=latest docker compose -f docker/prod/tier3.yml up -d --pull always
```

> **Note:** staging stacks default to `IMAGE_TAG=staging`; production uses `IMAGE_TAG=latest`. Override by exporting `IMAGE_TAG` before running compose commands.

### Service Shutdown/Startup Commands
Run these from your MBP (SSH into each node):

```bash
# Tier 1 (etl-node-01, Prefect + Watcher + Courier)
ssh bli@192.168.2.81 'cd /opt/pap/podcast-agent-pipeline && IMAGE_TAG=staging docker compose -f docker/staging/tier1.yml down'
ssh bli@192.168.2.81 'cd /opt/pap/podcast-agent-pipeline && IMAGE_TAG=staging docker compose -f docker/staging/tier1.yml up -d --remove-orphans'

# Tier 2 (mid-node-01, Qdrant + Prefect logic worker)
ssh bli@192.168.2.83 'cd /opt/pap/podcast-agent-pipeline && IMAGE_TAG=staging docker compose -f docker/staging/tier2.yml down'
ssh bli@192.168.2.83 'cd /opt/pap/podcast-agent-pipeline && IMAGE_TAG=staging docker compose -f docker/staging/tier2.yml up -d --remove-orphans'

# (future) Tier 3 (gpu-node-01)
ssh bli@192.168.2.82 'cd /opt/pap/podcast-agent-pipeline && IMAGE_TAG=staging docker compose -f docker/staging/tier3.yml down'
ssh bli@192.168.2.82 'cd /opt/pap/podcast-agent-pipeline && IMAGE_TAG=staging docker compose -f docker/staging/tier3.yml up -d --remove-orphans'
```

## Testing & Local Validation

| Scope | Command | Notes |
| --- | --- | --- |
| Full unit/integration suite | `pytest` | Covers Watcher ledger/poller/downloader, Ear FastAPI endpoints, Brain fallback analyzer, Courier markdown/Telegram stubs, and Prefect flow smoke test with external calls mocked |
| Watcher CLI smoke | `python -m watcher.main --config config/feeds.yaml` | Set `PAP_STORAGE_ROOT` to a temp directory; when Prefect workers aren’t running, tasks fall back to synchronous execution |
| Ear FastAPI | `uvicorn ear.api:app --reload` (then POST to `/transcribe`) | CPU-only stub returning deterministic segments |
| Prefect flow dry-run | `python -m flows.pipeline https://example.com feed guid123 ./output/%(ext)s` | Exercises end-to-end pipeline with download/Telegram mocked; relies on `.env` defaults |
| Staging Tier 1 smoke | `ssh bli@192.168.2.81 docker logs -f staging-watcher-1` | Confirms watcher flow downloads YouTube audio into `/srv/pap/raw` and records ledger entries. Prefect UI reachable at `http://192.168.2.81:4200/`. |

Stick with these local validations until YouTube/Telegram credentials and GPU services are ready for staging deployment.

## Next Steps
- Bring Tier 2 (mid-node-01) online with Qdrant + metadata services
- Wire courier notifications end-to-end using real Telegram credentials
- Add monitoring/logging (Loki/Grafana) and alerting hooks
- Expand Prefect deployments (scheduled watcher runs, flow retries)
