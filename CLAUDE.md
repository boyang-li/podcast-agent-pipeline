# CLAUDE OPERATIONS GUIDE — Podcast-Agent-Pipeline

## 1. Mission Snapshot
- **Goal:** Autonomous ingestion → transcription → analysis → publication for long-form podcast streams.
- **Architecture:** Two-node home lab (controller `etl-node-01`, compute `ai-node-01`/`gpu-node-01`). Prefect orchestrates Watcher → Ear → Brain → Courier agents. Shared storage via NFS + WD Black archival disk.
- **Reference Specs:** Review `docs/system-specs.md` **before** making assumptions. All implementation plans must stay consistent with that document.

## 2. Claude Engagement Rules
1. **Be Surgical:** No filler, no flattery, no speculative narratives. Output must read like a senior engineer’s notes.
2. **Respect Modes:** Honor `[analyze-mode]`, `[search-mode]`, `[build-mode]`, etc. Switch only when instructed.
3. **Default to Delegation:** Prefer specialized agents/tools (e.g., `explore`, `librarian`, `oracle`) over lone reasoning whenever possible.
4. **Evidence > Opinion:** Back recommendations by citing files, commands, or authoritative docs.
5. **No Side Effects Without Consent:** Never run destructive commands, install deps, or touch git history unless explicitly requested.
6. **Security First:** Never log secrets. Treat `.env`, Telegram tokens, and API keys as sensitive.

## 3. Repository Quick Map
| Path | Purpose |
| --- | --- |
| `docs/system-specs.md` | Canonical architecture, hardware, workflow, storage plan |
| `README.md` | Public entry point (currently minimal) |
| `CLAUDE.md` | You are here — engagement guide for Anthropic agents |
| `AGENTS.md` | Operational handbook for Watcher/Ear/Brain/Courier modules (create & maintain) |

## 4. Development Workflow Expectations
1. **Planning**
   - Start with `docs/system-specs.md` to confirm constraints (Prefect, FastAPI, yt-dlp, NFS, Telegram bot, etc.).
   - Produce todos (via `todowrite`) for any multi-step change.
2. **Execution**
   - Use `explore` for codebase discovery, `librarian` for external patterns, and `oracle` for architecture reviews.
   - Prefer focused patches per feature; no shotgun edits.
3. **Verification**
   - Run targeted tests/linters where applicable (define commands as the codebase grows).
   - Capture evidence (command output, diagnostics) in responses.
4. **Documentation**
   - Update `docs/system-specs.md` or `AGENTS.md` whenever behavior, topology, or workflows change.

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

## 7. Git & Review Discipline
1. **Commits:** Only when explicitly requested. Single-purpose commits with clear, action-oriented messages.
2. **Branches/PRs:** Follow user instructions; when creating PRs, include summary + testing evidence.
3. **No Secrets in Git:** Never commit `.env`, tokens, or generated credentials.

## 8. Open Questions Checklist (keep current)
- [ ] Define concrete test commands once services exist.
- [ ] Expand README with quick-start instructions.
- [ ] Implement monitoring stack and document dashboards.

Keep this file updated whenever operating procedures change. If a new workflow or policy is introduced, add it here **before** coding against it.
