# Docker Stack Overview

This directory houses docker-compose definitions for the Podcast Agent Pipeline.

## Layout
| File / Dir | Purpose |
| --- | --- |
| `docker-compose.local.yml` | Local MBP stack: Prefect + Postgres + CPU mocks |
| `staging/tier1.yml` | Gateway stack for `etl-node-01` (Prefect server, watcher, courier, Redpanda) |
| `staging/tier2.yml` | Logic stack for `mid-node-01` (Qdrant, metadata workers, logic pool worker) |
| `staging/tier3.yml` | GPU stack for `gpu-node-01` (Prefect GPU worker, Ear, Brain, Ollama) |
| `prod/tier1.yml` | Production counterpart of Tier 1 stack |
| `prod/tier2.yml` | Production counterpart of Tier 2 stack |
| `prod/tier3.yml` | Production counterpart of Tier 3 stack |

## Usage
```bash
# Local developer stack
docker compose -f docker/docker-compose.local.yml up --build

# Staging rollout (run on respective nodes)
docker compose -f docker/staging/tier1.yml up -d --remove-orphans       # etl-node-01
docker compose -f docker/staging/tier2.yml up -d --remove-orphans       # mid-node-01
docker compose -f docker/staging/tier3.yml up -d --remove-orphans       # gpu-node-01

# Production rollout (after staging validation)
docker compose -f docker/prod/tier1.yml pull && docker compose -f docker/prod/tier1.yml up -d
docker compose -f docker/prod/tier2.yml pull && docker compose -f docker/prod/tier2.yml up -d
docker compose -f docker/prod/tier3.yml pull && docker compose -f docker/prod/tier3.yml up -d
```

> **Note:** staging stacks default to `IMAGE_TAG=staging`; production uses `IMAGE_TAG=latest`. Override by exporting `IMAGE_TAG` before running compose commands.
