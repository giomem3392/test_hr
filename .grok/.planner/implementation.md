# Implementation: Foundry hosted notes agent

**Repo:** `giomem3392/test_hr`  
**Branch:** `feature/foundry-notes-agent`  
**Date:** 2026-09-06  
**PR:** _(filled after open)_

## Summary

Shipped a MAF + `ResponsesHostServer` notes agent with `$HOME` file tools, root `azure.yaml` (project + `gpt-4.1-mini` + hosted python agent, protocol `2.0.0`, code deploy), GitHub Actions CI (ruff + mypy), and README with Mermaid session/notes flow. No live Azure provision/deploy.

## Files delivered

| Path | Role |
|------|------|
| `src/notes-agent/notes.py` | Sanitize + save/read/list under `$HOME` |
| `src/notes-agent/main.py` | `FoundryChatClient` + `Agent` + `@tool` + `ResponsesHostServer` |
| `src/notes-agent/requirements.txt` | Runtime pins (incl. hosting prerelease) |
| `src/notes-agent/.env.example` | Local/env docs |
| `src/notes-agent/.agentignore` | Exclude local env/caches from agent package |
| `azure.yaml` | Foundry project + model + hosted agent |
| `.github/workflows/ci.yml` | ruff lint/format + mypy on PRs |
| `pyproject.toml` / `requirements-dev.txt` | Tooling pins + ruff/mypy config |
| `README.md` | Usage, contracts, Mermaid |
| `.grok/.planner/implementation.md` | This file |

## Pins used

| Package | Version |
|---------|---------|
| `agent-framework` | `1.17.0` |
| `agent-framework-foundry` | `1.12.0` |
| `agent-framework-foundry-hosting` | `1.0.0b260903` |
| `azure-identity` | `1.25.3` |
| `python-dotenv` | `1.2.3` |
| `ruff` | `0.16.6` |
| `mypy` | `2.3.1` |

## Plan checklist

1. Scaffold `src/notes-agent/` — done  
2. `notes.py` helpers + exact `saved note as {filename}` — done (local helper checks passed)  
3. MAF Agent + `@tool` + `ResponsesHostServer` — done  
4. Root `azure.yaml` — done  
5. CI ruff + mypy — done (workflow committed locally; push may need workflow-scope token)  
6. README + Mermaid — done  
7. Branch + PR + implementation.md — in progress

## Choices / deviations

1. **`implementation.md` path:** GioBot / Implementor profile asked for `.grok/.planner/implementation.md`. Plan text reserved `.grok/.implementor/implementation.md`. Wrote the planner path.
2. **Cloud agent unavailable:** Implemented via local clone `/workspace/test_hr` + GitHub MCP fallback.
3. **`azure.yaml` model `version`:** Set to `2025-04-14` as a catalog starting point; README instructs verifying/replacing from the regional catalog at `azd` init. Agents extension floor set to `>=1.0.0-beta.11` for `sessionConfiguration`.
4. **CI mypy cwd:** Runs from `src/notes-agent` so flat `notes` / `main` imports typecheck despite the hyphenated folder name.
5. **Optional `list_notes`:** Included (plan allowed optional).
6. **Import of `ResponsesHostServer`:** From `agent_framework_foundry_hosting` per plan/research.

## Residual risks

- Hosting package is prerelease; pin and re-test on upgrade.  
- LLM may still paraphrase save replies; hardened via tool return + strict instructions only.  
- Multi-turn `$HOME` reuse needs `agent_session_id` or `conversation`.  
- `gpt-4.1-mini` version/availability is region-dependent.  
- mypy uses `ignore_missing_imports` for MAF packages (not installed in CI).

## Anti-patterns avoided

No PLACEHOLDER stubs, no BYO agentserver-only stack, no merge to `main`, Reviewer not started.
