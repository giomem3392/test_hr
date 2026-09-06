# Research: Microsoft Agent Framework Python note agent as Azure AI Foundry hosted agent

**Repo target:** `giomem3392/test_hr`  
**Date:** 2026-09-06  
**Scope:** Project shape, APIs/SDKs, file layout, and infra templates only (no live Azure deploy required).  
**Done when:** Correct packaging/entrypoint, session-sandbox note persist/read pattern, `azure.yaml`/Bicep/azd guidance, recommended layout, Python CI lint/analyze options, risks + package versions — with official doc citations and facts vs assumptions.

---

## Executive summary

Build a **Microsoft Agent Framework (MAF) Python** agent that:

1. Hosts via `ResponsesHostServer` (or Invocations) from `agent-framework-foundry-hosting`.
2. Exposes tools so the model can **create/read note files under `$HOME`** in the Foundry **per-session sandbox**.
3. On save, replies exactly in the form `saved note as xyz` (prompt/tool-return contract).
4. Deploys as a Foundry **hosted agent** with `azd` + unified `azure.yaml` provisioning a Foundry project, a cheap chat model deployment, and the agent (optionally eject Bicep with `azd ai agent init --infra`).

Closest official references: MAF Foundry hosting docs, Foundry session/`$HOME` docs, and the Python **notetaking-agent** sample (BYO Responses + `$HOME` JSONL). Prefer MAF `@tool` + write under `$HOME` (or `FileAccessProvider` rooted at `$HOME`) over the BYO OpenAI function-calling sample if the requirement is MAF-first.

---

## 1. Current Microsoft Agent Framework Python APIs + hosted agent packaging/entrypoint

### Facts

- **Foundry Hosted Agents** run your containerized (or source-deployed) agent on managed infra with per-session sandboxes, Entra agent identity, scaling, and protocol endpoints. GA for the hosting service; Python hosting integration called out as prerelease on Learn.  
  Sources: [Foundry Hosted Agents (Agent Framework)](https://learn.microsoft.com/en-us/agent-framework/hosting/foundry-hosted-agent), [Hosted agents concepts](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents), [Blog: MAF → Foundry Hosted Agents](https://devblogs.microsoft.com/agent-framework/from-local-to-production-deploy-your-microsoft-agent-framework-agent-with-foundry-hosted-agents/).

- **Minimal MAF + Responses host (Python):**
  ```python
  from agent_framework import Agent
  from agent_framework.foundry import FoundryChatClient
  from agent_framework_foundry_hosting import ResponsesHostServer
  from azure.identity import DefaultAzureCredential

  client = FoundryChatClient(
      project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
      model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
      credential=DefaultAzureCredential(),
  )
  agent = Agent(
      client=client,
      instructions="...",
      default_options={"store": False},  # platform manages history for Responses
      tools=[...],  # note save/read tools
  )
  ResponsesHostServer(agent).run()  # default port 8088, POST /responses
  ```
  Sources: [Foundry Hosted Agents](https://learn.microsoft.com/en-us/agent-framework/hosting/foundry-hosted-agent), [Host MAF as Foundry hosted agents](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/framework-hosted-agents).

- **Protocols:**
  | Protocol | Endpoint | Use |
  |---|---|---|
  | Responses | `/responses` | OpenAI-compatible chat, streaming, platform conversation history |
  | Invocations | `/invocations` | Custom JSON / webhooks; platform does **not** store conversation history |
  Prefer **Responses** for this note chatbot. Protocol version in `azure.yaml` should be **`2.0.0`** (1.0.0 and 2.0.0 are incompatible).  
  Sources: [framework-hosted-agents](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/framework-hosted-agents), [MAF samples README](https://github.com/microsoft/agent-framework/blob/main/python/samples/04-hosting/foundry-hosted-agents/README.md), [Migrate hosted agent preview](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/migrate-hosted-agent-preview).

- **Install (docs differ slightly):**
  - Hosting guide: `pip install --pre agent-framework-foundry agent-framework-foundry-hosting azure-identity`
  - Develop guide: `pip install -U agent-framework agent-framework-foundry-hosting azure-identity python-dotenv`
  - Migration guide maps preview names: `ChatAgent` → `Agent`, `AzureAIAgentClient` → `FoundryChatClient`, `@ai_function` → `@tool`.  
  Sources: same Learn pages + [migrate](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/migrate-hosted-agent-preview).

- **Tools API (MAF Python):** use `@tool` / `FunctionTool` (not legacy `@ai_function` / `AIFunction` after `python-1.0.0b260128`).  
  Source: [agent-framework issue #5564](https://github.com/microsoft/agent-framework/issues/5564), [PR #3413](https://github.com/microsoft/agent-framework/pull/3413).

- **Optional file harness:** `FileAccessProvider` + `FileSystemAgentFileStore` expose `file_access_save_file` / `file_access_read_file` / list / delete / search. Docs note shared-store semantics across sessions unless scoped carefully — for Foundry session isolation, root the store at `$HOME` and rely on per-session sandboxes (or stick to custom `@tool` writers under `$HOME`).  
  Sources: [context providers](https://learn.microsoft.com/en-us/agent-framework/concepts/agents/conversations/context-providers), [PR #6099](https://github.com/microsoft/agent-framework/pull/6099).

- **Runtime env injected by Foundry into the container:**
  - `FOUNDRY_PROJECT_ENDPOINT`
  - `AZURE_AI_MODEL_DEPLOYMENT_NAME` (also referenced as set during `azd ai agent init`)
  - `APPLICATIONINSIGHTS_CONNECTION_STRING`  
  Do **not** declare `FOUNDRY_PROJECT_ENDPOINT` in `azure.yaml` `env` (platform reserves `FOUNDRY_` / `AGENT_` prefixes).  
  Sources: [Foundry Hosted Agents](https://learn.microsoft.com/en-us/agent-framework/hosting/foundry-hosted-agent), [azure.yaml reference](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/azure-yaml-reference).

- **Scaffold / sample entrypoints:**
  - `azd ai agent init -m <manifest-or-azure.yaml-url>` then `azd ai agent run` / `azd provision` / `azd deploy`.
  - Official MAF samples: [python/samples/04-hosting/foundry-hosted-agents](https://github.com/microsoft/agent-framework/tree/main/python/samples/04-hosting/foundry-hosted-agents).
  - Foundry samples (incl. AF + BYO): [foundry-samples hosted-agents](https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents).

### Assumptions

- **Assumption:** For `giomem3392/test_hr`, implementer will use **Responses + MAF** (`ResponsesHostServer`) rather than the BYO `ResponsesAgentServerHost` notetaking sample, while copying that sample’s **`$HOME` persistence idea**.
- **Assumption:** Exact reply string `saved note as xyz` is enforced via **tool return value + system instructions** (and optionally post-processing), not via a Foundry platform feature.

---

## 2. Session sandbox filesystem APIs for persist/read

### Facts

- A **session** = isolated sandbox compute + persisted filesystem (`$HOME` and `/files`). Distinct from a **conversation** (`previous_response_id` / `conversation` for Responses history).  
  Source: [Manage hosted agent sessions](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/manage-hosted-sessions).

- Lifecycle: sessions up to **~30 days**; idle timeout configurable **5–60 min** (default **15 min** / 900s) then compute deprovisions but `$HOME` is restored on resume. Disk budget up to **~20 GiB** at ≥1 vCPU (scaled down for smaller tiers; ~20% reserved).  
  Sources: [manage sessions](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/manage-hosted-sessions), [hosted agents concepts](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents).

- **Inside the agent container:** write/read with normal Python `open()` under `os.environ["HOME"]`. Files appear on the Session Files API. Official note: “A container can also write files directly into the session sandbox (under `$HOME`) and have them appear through these APIs.” Example: [notetaking-agent sample](https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents/bring-your-own/responses/notetaking-agent).

- **Notetaking sample pattern (`note_store.py`):**
  - Path: `$HOME/notes_{safe_session_id}.jsonl`
  - `save_note(session_id, note_text)` appends JSONL
  - `get_notes(session_id)` reads all entries  
  This is **one file per session**, not one file per note named by the model — close but not identical to the product requirement.

- **Client/SDK Session Files API** (`azure-ai-projects>=2.3.0`):
  - `create_session` / `list_sessions` / `get_session` / `delete_session` / `stop_session`
  - `upload_session_file` / `list_session_files` / `download_session_file` / `delete_session_file`
  - Upload max **50 MB** per file  
  Keyword naming quirk: `session_id` on upload vs `agent_session_id` on some other methods (docs call this out).  
  Source: [Manage hosted agent sessions](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/manage-hosted-sessions).

- **Binding calls to the same sandbox (Responses):** pass `agent_session_id` in the body (or use a `conversation` id which auto-binds a session). `previous_response_id` alone does **not** reuse `$HOME`.  
  Source: same Learn page.

### Recommended note behavior for this task (facts + design)

**Facts used:** `$HOME` persistence; tools callable by the model.

**Design recommendation (labeled assumption where needed):**

1. Tools (custom `@tool`):
   - `save_note(filename: str, content: str) -> str` → write `Path(HOME)/sanitize(filename)`, return exactly `saved note as {filename}` (or return that string and instruct the model to echo it verbatim).
   - `read_note(filename: str) -> str` → read file contents or a clear not-found message.
   - Optional: `list_notes() -> str`.
2. Instructions: model **chooses filename from content** (e.g. slug from first line / topic); on save, user-visible reply must match `saved note as xyz`.
3. Keep `agent_session_id` (or `conversation`) stable across turns so later “retrieve note xyz” hits the same `$HOME`.
4. Sanitize filenames (alnum, `-`, `_`, `.`); reject path traversal (`..`, absolute paths).

### Assumptions

- **Assumption:** Product wants **one file per note** with model-chosen names, not the sample’s single JSONL log.
- **Assumption:** Client apps will pass `agent_session_id` or use `conversation` when testing multi-turn retrieve; local `azd ai agent invoke` may need flags/docs for session reuse.

---

## 3. Infra: Azure YAML / Bicep / azd patterns

### Facts

- **Single config file:** unified `azure.yaml` (replaces split `agent.manifest.yaml` + `agent.yaml`).  
  Sources: [azure.yaml reference](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/azure-yaml-reference), [Author azure.yaml](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/author-azure-yaml).

- **Minimal shape:**
  - `services.<name>` with `host: azure.ai.project` + `deployments[]` (model name/version/sku/capacity)
  - `services.<agent>` with `host: azure.ai.agent`, `kind: hosted`, `uses: [ai-project]`, `protocols: [{protocol: responses, version: 2.0.0}]`, `project: src/...`, env for model deployment name, `container.resources` or `codeConfiguration`

- **azd commands:** `azd provision` (project, models, ACR, App Insights, …), `azd deploy` (build/push image or code ZIP + create agent version), `azd up`, `azd down`, `azd ai agent init|run|invoke|monitor|show`, file helpers `azd ai agent files …`.  
  Extension versions called out: `azure.ai.agents >= 1.0.0-beta.8` (reference) / sample uses `>=1.0.0-beta.9`; `azure.ai.projects >= 1.0.0-beta.4`; `azd >= 1.27.1`.

- **Bicep-less by default:** infrastructure synthesized from `azure.yaml` at provision. Eject with:
  - `azd ai agent init --infra` or `--infra=bicep` → `./infra/`
  - `--infra=terraform` also supported  
  Ejected Bicep (based on [azd-ai-starter-basic](https://github.com/Azure-Samples/azd-ai-starter-basic)) creates: RG, AI Services/Foundry account, Foundry project, model deployments, ACR, App Insights, Log Analytics, managed identity. Docs explicitly cite **`gpt-4.1-mini`** as an example model deployment.  
  Source: [CLI infrastructure](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/cli-infrastructure).

- **Deploy modes:** `code` (ZIP + remote build; default for Python/.NET) vs `container` (Dockerfile → ACR). Notetaking sample uses `language: python` + `codeConfiguration.runtime: python_3_13` + `entryPoint: main.py` and `infra.provider: microsoft.foundry`.

- **Illustrative `azure.yaml` fragment** (adapt model to cheapest available in target region; versions change):
  ```yaml
  # yaml-language-server: $schema=https://raw.githubusercontent.com/Azure/azure-dev/main/schemas/v1.0/azure.yaml.json
  name: test-hr-notes
  requiredVersions:
    azd: ">=1.27.1"
    extensions:
      azure.ai.agents: ">=1.0.0-beta.9"
      azure.ai.projects: ">=1.0.0-beta.4"
  services:
    ai-project:
      host: azure.ai.project
      deployments:
        - name: gpt-4.1-mini   # or gpt-5.4-mini / whatever catalog returns
          model:
            format: OpenAI
            name: gpt-4.1-mini
            version: "<catalog-version>"
          sku:
            name: GlobalStandard
            capacity: 10
    notes-agent:
      host: azure.ai.agent
      project: src/notes-agent
      language: python          # or docker
      codeConfiguration:
        runtime: python_3_13
        entryPoint: main.py
      uses: [ai-project]
      kind: hosted
      name: notes-agent
      protocols:
        - protocol: responses
          version: 2.0.0
      env:
        AZURE_AI_MODEL_DEPLOYMENT_NAME: ${AZURE_AI_MODEL_DEPLOYMENT_NAME}
      container:
        resources:
          cpu: "0.25"
          memory: 0.5Gi
      sessionConfiguration:
        idleTimeoutSeconds: 900
  ```
  `sessionConfiguration.idleTimeoutSeconds` requires agents extension **≥1.0.0-beta.11** per sessions doc.

### Assumptions

- **Assumption:** Cheapest suitable model is **`gpt-4.1-mini`** when available in the chosen region; if not, use whatever `azd ai agent init` / catalog offers as the mini-tier OpenAI chat model (samples often show `gpt-5.4-mini`). **Verify at init time** — do not hardcode a dead version.
- **Assumption:** For this repo, prefer **code deploy** (no local Docker) unless packaging needs a custom base image.

---

## 4. Recommended repo layout for `giomem3392/test_hr`

```text
test_hr/
├── azure.yaml                          # Foundry project + model + hosted agent
├── infra/                              # optional: ejected Bicep (azd ai agent init --infra)
├── .grok/
│   ├── .researcher/research.md         # this file
│   └── .planner/                       # later pipeline stages
├── src/
│   └── notes-agent/
│       ├── main.py                     # Agent + tools + ResponsesHostServer.run()
│       ├── notes.py                    # $HOME path helpers + sanitize
│       ├── requirements.txt / pyproject.toml
│       ├── Dockerfile                  # only if container deploy mode
│       ├── .dockerignore / .agentignore
│       └── .env.example
├── .github/workflows/ci.yml            # ruff + mypy (or pyright) on PRs
├── README.md                           # architecture + how to azd init/run (no deploy required for research)
└── pyproject.toml                      # optional monorepo tooling root
```

Align with [notetaking sample](https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents/bring-your-own/responses/notetaking-agent) (`azure.yaml` + `src/<agent>/`) and MAF hosting samples under [agent-framework foundry-hosted-agents](https://github.com/microsoft/agent-framework/tree/main/python/samples/04-hosting/foundry-hosted-agents).

---

## 5. Lint / static-analysis tools for Python CI on PRs

### Facts / recommendations

Pipeline policy for feature builds expects GitHub Actions on the PR that **lints and statically analyzes** the language(s).

| Tool | Role | Notes |
|---|---|---|
| **Ruff** | Lint + import sort + many style rules (replaces flake8/isort/pyupgrade) | Fast; pin latest stable (PyPI snapshot 2026-09-06: `ruff==0.16.6`) |
| **Mypy** or **Pyright** | Static typing | Prefer mypy if gradual typing; pyright if stricter IDE-aligned checks. Snapshot: `mypy==2.3.1` |
| **Ruff format** (optional) | Formatter | Or Black; keep one formatter |

Suggested workflow jobs: `ruff check`, `ruff format --check`, `mypy src` (or `pyright`), on `pull_request` to `main`. Add `requirements-dev.txt` or `[dependency-groups] dev` in `pyproject.toml`.

### Assumptions

- **Assumption:** No need for Bandit/Semgrep in the first CI unless security review asks; Ruff + typechecker satisfies the pipeline’s “lint and statically analyze” bar.

---

## 6. Risks, unknowns, and package/version recommendations

### Package / version recommendations (as of 2026-09-06 PyPI)

| Package | Observed latest | Guidance |
|---|---|---|
| `agent-framework` | `1.17.0` | Meta/core install path used in develop docs |
| `agent-framework-foundry` | `1.12.0` | `FoundryChatClient` |
| `agent-framework-foundry-hosting` | `1.0.0b260903` | Prerelease; pin explicitly; must match protocol **2.0.0** |
| `azure-ai-projects` | `2.6.0` | Use **≥2.3.0** for session file APIs |
| `azure-identity` | (pin current stable) | `DefaultAzureCredential` |
| `python-dotenv` | optional | Local `.env` |
| `ruff` | `0.16.6` | CI lint |
| `mypy` | `2.3.1` | CI types |

Also note BYO sample pins older stacks (`azure-ai-agentserver-responses==2.1.0`, `azure-ai-projects==2.0.1`) — **do not mix** that stack with MAF hosting packages without a deliberate choice.

Last protocol 1.0.0 hosting package called out as `agent-framework-foundry-hosting==1.0.0a260625` — avoid for new work.

### Risks / unknowns

| Item | Severity | Notes |
|---|---|---|
| **Env var naming drift** | High | Docs/samples use `AZURE_AI_MODEL_DEPLOYMENT_NAME`, `MICROSOFT_FOUNDRY_MODEL_DEPLOYMENT_NAME`, and occasionally other Foundry names. Confirm what `azd ai agent init` writes into `.azure/<env>/.env` and what the container receives; read both in code if needed. |
| **Hosting package prerelease** | Medium | API surface intended stable; still pin and re-test on upgrade. |
| **Protocol 1.0.0 vs 2.0.0** | High | Incompatible; set `protocols.version: 2.0.0` everywhere. |
| **Exact reply contract** | Medium | LLMs may paraphrase; harden via tool return + instructions (+ optional host middleware). |
| **Filename safety** | Medium | Must sanitize to avoid path escape outside `$HOME`. |
| **Session vs conversation confusion** | High | Multi-turn note retrieve needs `agent_session_id` or `conversation`, not only `previous_response_id`. |
| **Model availability / quota** | Medium | `gpt-4.1-mini` vs `gpt-5.4-mini` depends on region/catalog; resolve at `azd` init. |
| **FileAccessProvider sharing semantics** | Medium | Designed as shared store in MAF docs; prefer custom `$HOME` tools for session-scoped notes unless carefully rooted/scoped. |
| **ARM vs amd64 images** | Medium | If building Docker locally on Apple Silicon, must `--platform=linux/amd64` or use ACR remote build (`azd deploy`). |
| **Empty repo bootstrap** | Low | `test_hr` had no default branch until this research commit. |

---

## Facts vs assumptions (checklist)

### Facts

- Hosted agents persist `$HOME` across idle resume; Session Files API mirrors those files.
- MAF entrypoint for Responses is `ResponsesHostServer(agent).run()`.
- Unified `azure.yaml` + `azd` provision/deploy is the supported project shape; Bicep is optional via `--infra`.
- Official notetaking sample proves `$HOME` + function tools + Responses for notes.
- Protocol version for new agents should be `2.0.0`.
- `azure-ai-projects>=2.3.0` for session CRUD/files.

### Assumptions

- Implement with **MAF** (not BYO agentserver-only) unless Planner chooses otherwise.
- One **file per note**, model-chosen name, exact `saved note as xyz` user text.
- Prefer **code** deploy mode and cheapest **mini** OpenAI chat deployment available in-region.
- CI = **Ruff + mypy** is sufficient for the pipeline gate.

---

## Open questions for Planner / Implementor

1. Confirm **MAF** vs **BYO `azure-ai-agentserver-responses`** (sample is BYO; requirement text says MAF).
2. Confirm exact user-visible save string: strictly `saved note as xyz` with no punctuation/extra words?
3. Filename rules: extension required (`.txt`/`.md`)? overwrite policy?
4. Target Azure region and whether **`gpt-4.1-mini`** is available (else which mini model)?
5. Deploy mode: **code** vs **container**?
6. Should notes be listable via Session Files API paths for operators, or only through the agent?
7. Which model env var name does the chosen `azd` extension version inject — align code to that single name.

---

## Key official URLs

- https://learn.microsoft.com/en-us/agent-framework/hosting/foundry-hosted-agent  
- https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/framework-hosted-agents  
- https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents  
- https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/manage-hosted-sessions  
- https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/deploy-hosted-agent  
- https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/azure-yaml-reference  
- https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/author-azure-yaml  
- https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/cli-infrastructure  
- https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/migrate-hosted-agent-preview  
- https://devblogs.microsoft.com/agent-framework/from-local-to-production-deploy-your-microsoft-agent-framework-agent-with-foundry-hosted-agents/  
- https://github.com/microsoft/agent-framework/tree/main/python/samples/04-hosting/foundry-hosted-agents  
- https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents/bring-your-own/responses/notetaking-agent  
- https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents/agent-framework  
