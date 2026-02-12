# Development Roadmap — Podcast-Agent-Pipeline

## 1. Reality Check
- Repo now contains implemented Watcher/Ear/Brain/Courier services, Prefect flows, unit tests, and tiered Docker stacks.
- Tier 1 (etl-node-01) production environment is live; Tier 2 (mid-node-01) and Tier 3 (gpu-node-01) host their respective production services.
- Architecture mandates containerized deployment: local Docker Compose on MBP (CPU mocks) + production stacks on `etl-node-01` (gateway), `mid-node-01` (logic), and `gpu-node-01` (GPU).

## 2. Recommended Development Approach
| Phase | Goals | Key Decisions |
| --- | --- | --- |
| **Phase 0 – Bootstrap** | Establish scaffolding & configuration | Choose dependency manager (`poetry` or `uv/pip`), create `pyproject.toml`/`requirements.txt`, define repo structure (`src/<agent>`, `flows/`, `config/`), add `.env.example`, `config/feeds.yaml.example`. |
| **Phase 1 – Infrastructure Foundation** | Prefect server + storage + monitoring skeleton | Implement Docker Compose stacks (local + production); configure GPU work pool w/ concurrency limit; set up NFS export & mount scripts; stub Grafana/Loki/Prometheus stack. |
| **Phase 2 – Agent Implementations** | ✅ Watcher → Ear → Brain → Courier skeletons + Prefect flow | Implemented Python packages under `src/`, FastAPI Ear service, Ollama fallback Brain, Courier markdown/Telegram client, and Prefect `flows/pipeline.py` with local test coverage. |
| **Phase 3 – Prefect Flows & Resilience** | Wire end-to-end pipeline | Define Prefect flows per stage, add retries/backoff, dead-letter logging, Wake-on-LAN hook, structured logging → Loki, metrics to Prometheus. |
| **Phase 4 – QA & Ops Readiness** | Automated prod tests + monitoring | Container health checks, scheduled Prefect runs, README quickstart, dashboards, runbooks for WOL/NFS/yt-dlp issues. |

## 3. Immediate Action Items (Week 1)
1. **Repo Scaffolding**
   - Create directories: `src/watcher`, `src/ear`, `src/brain`, `src/courier`, `flows`, `scripts`, `config`.
   - Add dependency manifest (`pyproject.toml` or `requirements.txt`) covering `prefect`, `fastapi`, `uvicorn`, `yt-dlp`, `feedparser`, `pydantic`, `httpx`, `python-dotenv`.
2. **Configuration Templates**
   - `config/feeds.yaml.example` with YouTube channel IDs + polling intervals.
   - `.env.example` for `PREFECT_API_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `OLLAMA_HOST`, DB paths.
3. **Prefect & Storage Prep** (✅)
   - Docker Compose stacks for local + production committed under `docker/`.
   - `PAP_STORAGE_ROOT` env + NFS layout codified in shared paths module.
4. **Watcher Prototype** (✅)
   - CLI + Prefect flow implemented; ledger/test coverage in pytest.

## 4. Prefect, Docker & Home-Lab Considerations
- Use Prefect 3 self-hosted with Postgres backend; configure work pools (`default` for controller, `gpu` for compute) and set `gpu` pool concurrency = 1.
- On `ai-node-01`, set `PREFECT_API_URL` to controller IP and run worker with healthcheck.
- Tag GPU tasks and leverage global concurrency limits to avoid VRAM contention.
- Pipe Docker logs to Loki; enable Prefect artifacts to link transcripts/summaries for manual review.
- Local dev uses CPU mocks inside Docker; GPU validation happens via the production GPU node after CI deploys.
- CI builds multi-arch images via docker buildx; production compose stacks pull from GHCR/local registry.

## 5. Risk Watchlist / Open Questions
1. Monitoring stack deployment (Grafana/Loki/Prometheus) still conceptual—decide on hosting approach.
2. Test strategy for GPU-dependent services—ensure CPU mocks in Docker Compose are realistic.
3. README and onboarding docs need expansion once scaffolding lands.
4. Service-to-service authentication scheme (API keys) must be finalized and documented.

## 6. Six-Week Roadmap Snapshot
| Week | Focus |
| --- | --- |
| **1** | Scaffolding, configs, dependency manifest, templates |
| **2** | Prefect server + Postgres, NFS setup, `.env` handling, Docker Compose env |
| **3** | ✅ Watcher + Ear implementations with initial tests |
| **4** | ✅ Brain + Courier services, Ollama prompts, Telegram integration |
| **5** | Prefect flow skeleton + pytest coverage; next: dead-letter handling, WOL automation |
| **6** | Monitoring stack, production integration tests, README + runbooks, launch readiness review |

Keep this roadmap in sync with implementation progress; update milestones whenever scope or sequencing changes.
