# CLAUDE OPERATIONS GUIDE — Podcast-Agent-Pipeline

## 1. Mission Snapshot
- **Goal:** Autonomous ingestion → transcription → analysis → publication for long-form podcast streams.
- **Architecture:** Tiered compute cluster (Tier 1 `etl-node-01`, Tier 2 `mid-node-01`, Tier 3 `gpu-node-01`). Prefect orchestrates Watcher → Ear → Brain → Courier agents. Shared storage via NFS + WD Black archival disk.
- **Reference Specs:** Review `docs/system-specs.md` **before** making assumptions. All implementation plans must stay consistent with that document.
- **Claude Code Canon:** Follow Boris Cherny’s Claude Code tips — plan before execution, keep feedback loops tight, and log lessons learned back into this file.

### Environment Context & Hosts
| Host | IP | Role | Notes |
| --- | --- | --- | --- |
| `etl-node-01` | 192.168.2.81 | Gateway & ingestion | Ubuntu Server 24.04, always-on; Prefect server, Watcher, Courier, Redpanda |
| `mid-node-01` | 192.168.2.82 | Logic orchestrator | Ubuntu Server 24.04 on MBP 2019 chassis; metadata, Qdrant, light inference, GitHub runner |
| `gpu-node-01` | 192.168.2.83 | Heavy inference | Ubuntu Server 24.04 desktop; Wake 19:00 / suspend 07:00; ROCm 6.2 (`HSA_OVERRIDE_GFX_VERSION=11.0.1`) |

- **Network:** All nodes hardwired via 2.5 Gbps switch with 1 Gbps uplink to router; SSH key access from MBP M4.
- **Energy Policy:** Respect the night-time GPU burst schedule (off-peak 19:00–07:00). Schedule heavy jobs through Prefect’s Scheduling Agent; prioritize Tier 2 for light tasks to save power.
- **Testing Reminder:** Run `pytest` before any cluster deploy; suite mocks Telegram/Ollama/yt-dlp so it should pass locally without secrets. In staging, Watcher is verified on etl-node-01 (downloads All-In podcast audio) and Prefect UI is reachable at `http://192.168.2.81:4200/`.
- **Current Status:** Tier 1 stack (Prefect server/worker, Redpanda, Watcher, Courier placeholder) is live on `etl-node-01`. Tier 2/3 not yet deployed.

## 2. Claude Engagement Rules
1. **Plan → Execute:** Every non-trivial task starts with a `/plan` mindset. Use `<analysis>` sections to spell out intent, risks, and parallel search strategy before editing.
2. **Respect Modes:** Honor `[analyze-mode]`, `[search-mode]`, `[build-mode]`, etc. Switch only when instructed.
3. **Default to Delegation:** Prefer specialized agents/tools (e.g., `task(category="quick", load_skills=[...])`) over lone reasoning whenever possible.
4. **Evidence > Opinion:** Back recommendations by citing files, commands, or authoritative docs.
5. **No Side Effects Without Consent:** Never run destructive commands, install deps, or touch git history unless explicitly requested.
6. **Security First:** Never log secrets. Treat `.env`, Telegram tokens, and API keys as sensitive.

### Required Response Structure
- Begin heavy-lift answers with:
  ```
  <analysis>
  ... reasoning ...
  </analysis>
  ```
- Conclude with:
  ```
  <results>
  <files>…changed files…</files>
  <answer>…summary…</answer>
  <next_steps>…follow-ups…</next_steps>
  </results>
  ```
- If nothing changed, `<files>` can be omitted but `<analysis>` + `<answer>` must remain.

## 3. Repository Quick Map
| Path | Purpose |
| --- | --- |
| `docs/system-specs.md` | Canonical architecture, hardware, workflow, storage plan |
| `README.md` | Public entry point (currently minimal) |
| `CLAUDE.md` | You are here — engagement guide for Anthropic agents |
| `AGENTS.md` | Operational handbook for Watcher/Ear/Brain/Courier modules (create & maintain) |

## 4. Development Workflow Expectations
1. **Planning**
   - Start with `docs/system-specs.md` to confirm constraints (Prefect, FastAPI, yt-dlp, NFS, Docker workflow, etc.).
   - Produce todos (via `todowrite`) for any multi-step change.
   - Create `/plan`-style bullet list before taking action; reference relevant files/commands.
2. **Execution**
   - Use `task(...)` to launch explore/librarian/oracle agents in parallel wherever feasible.
   - Work out of multiple git worktrees when investigating divergent ideas (mirrors Boris’s tip on parallel sessions).
   - Prefer focused patches per feature; no shotgun edits.
   - When touching Prefect-decorated functions, maintain optional-import fallbacks (`flow`/`task`) so pytest can run without Prefect installed.
3. **Verification**
   - Give Claude a verification hook: run tests, linters, or Prefect flows whenever possible and capture output.
   - Include command snippets/logs in `<results>`.
4. **Documentation**
   - Update `docs/system-specs.md`, `AGENTS.md`, or this file whenever workflows or lessons learned change.

## 5. Response Conventions
| Scenario | Expectation |
| --- | --- |
| User asks for plan | Provide structured outline + decision points |
| User requests code | Give precise diffs or files, with brief reasoning |
| Ambiguity | Ask exactly one clarifying question before proceeding |
| Disagreement with user | Concisely note risk + alternative, ask for direction |

## 6. Tooling & Commands
- **Prefect:** Python orchestration. Document flows, tasks, and retry policies in code comments.
- **yt-dlp:** Standard for audio extraction. Keep command templates in docs/tests.
- **FastAPI:** Preferred HTTP surface for agents. Enforce Pydantic schemas.
- **Storage:** `/srv/pap` (NFS export) on controller, `/mnt/pap` mount on compute, `/mnt/pap-archive` for rsync backups.
- **Telemetry:** Grafana + Loki + Prometheus (to be implemented). Plan for metrics from day one.
- **GPU Runtime:** Any directive touching Tier 3 must propagate `HSA_OVERRIDE_GFX_VERSION=11.0.1` into container envs and ensure WOL scheduling is respected.
- **task() Usage:** Always specify `category`, `load_skills`, and `run_in_background`. Example:
  ```
  task(category="quick", load_skills=["git-master"], run_in_background=false,
       description="stage files", prompt="Run git add -A")
  ```
- **Tests:** `pytest` (full suite). Set `PAP_STORAGE_ROOT` to a writable path when running outside pytest fixtures to avoid `/srv` permissions.
- **Staging Verification:**
  - Watcher logs on etl-node show successful downloads; inspect `/srv/pap/raw/all-in` for MP3/JSON.
  - Prefect UI accessible at `http://192.168.2.81:4200/`; ensure browser uses LAN IP (avoids `prefect-server` DNS errors).
  - Known issues: watcher currently restarts after each run (single-pass flow); courier container is placeholder until Telegram notifier is finalized.

## 7. Git & Review Discipline
1. **Commits:** Only when explicitly requested. Single-purpose commits with clear, action-oriented messages.
2. **Branches/PRs:** Follow user instructions; when creating PRs, include summary + testing evidence.
3. **No Secrets in Git:** Never commit `.env`, tokens, or generated credentials.

## 8. Open Questions Checklist (keep current)
- [x] Define concrete test commands once services exist (`pytest`).
- [x] Expand README with quick-start instructions.
- [ ] Implement monitoring stack and document dashboards.
- [ ] Capture lessons learned (missteps, best prompts) back into `CLAUDE.md` à la Boris Cherny’s workflow.

Keep this file updated whenever operating procedures change. If a new workflow or policy is introduced, add it here **before** coding against it.
