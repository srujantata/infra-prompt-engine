# infra-prompt-engine

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)
![Claude](https://img.shields.io/badge/Claude-API-000000?logo=anthropic)
![Ollama](https://img.shields.io/badge/Ollama-Local%20AI-white?logo=ollama)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)
![Kubernetes](https://img.shields.io/badge/Kubernetes-EKS-326CE5?logo=kubernetes)
![Tests](https://github.com/srujantata/infra-prompt-engine/actions/workflows/test.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)

> **Plain English → Terraform HCL → GitHub PR → AWS EKS**
> **Plain English → kubectl commands → live cluster administration**
> **Chat UI (PWA) — works on PC, Mac, and Mobile**
> **Runs 100% locally on RTX 4090 via Ollama — $0/month**

---

## What This Does

Type a sentence. Get infrastructure.

```
"Add a Redis cache to the POC environment"
        ↓
  Claude / Ollama (local)
        ↓
  main.tf + variables.tf + outputs.tf
        ↓
  GitHub PR opened for review
        ↓
  GitHub Actions runs terraform plan
        ↓
  Merge → terraform apply → AWS
```

Or administer your live Kubernetes cluster:

```
"Scale Jenkins to 3 replicas"        →  kubectl scale deployment jenkins --replicas=3 -n jenkins
"Show all pods that are not Running"  →  kubectl get pods -A --field-selector=status.phase!=Running
"Get SonarQube logs last 100 lines"   →  kubectl logs deploy/sonarqube -n sonarqube --tail=100
"Is my cluster healthy?"              →  runs kubectl get pods/nodes, returns AI summary
```

---

## Live Demo — Chat UI

A single-file Progressive Web App. No install. Works on phone via WiFi.

```
┌──────────────────────────────────────────────────────┐
│  🤖 DevOps Platform Assistant          ● Connected   │
├────────────┬─────────────────────────────────────────┤
│ CLUSTER    │                                         │
│ ● 27 pods  │  You: scale Jenkins to 3 replicas       │
│ ● 2 nodes  │                                         │
│ ● No errors│  AI: I'll scale Jenkins to 3 replicas   │
│            │  in the jenkins namespace.              │
│ TOOLS      │                                         │
│ ArgoCD ↗   │  Command:                               │
│ Jenkins ↗  │  kubectl scale deployment jenkins \     │
│ SonarQube↗ │    --replicas=3 -n jenkins              │
│ Harbor ↗   │                                         │
│            │  Risk: LOW  ──  toggle ⚡ Execute to run │
├────────────┴─────────────────────────────────────────┤
│  Type a message...                    [⚡ OFF] [Send] │
└──────────────────────────────────────────────────────┘
```

**Start it:**
```powershell
python -m http.server 3000 --directory chat_ui
# PC/Mac: http://localhost:3000
# Mobile (same WiFi): http://YOUR_PC_IP:3000  →  Add to Home Screen
```

---

## Quick Start

### 1 — Clone and install
```bash
git clone https://github.com/srujantata/infra-prompt-engine
cd infra-prompt-engine
pip install -r requirements.txt
```

### 2 — Configure environment
```powershell
# Windows — sets all vars permanently
.\setup_env.ps1

# Mac/Linux
chmod +x setup_env.sh && ./setup_env.sh
```

Or manually copy `.env.example` to `.env` and fill in your keys.

### 3 — Start the server
```bash
uvicorn prompt_engine.server:app --reload --port 8000
```

### 4 — Open the chat UI
```bash
python -m http.server 3000 --directory chat_ui
# open http://localhost:3000
```

### 5 — Or use the CLI directly
```bash
# Terraform — dry run (no PR, just shows HCL)
python -m prompt_engine.cli "Create an S3 bucket with versioning" --dry-run

# Terraform — opens real GitHub PR
python -m prompt_engine.cli "Add a Redis cache to POC env" --env poc --repo srujantata/aws-eks-platform

# kubectl — translate only (safe default)
python -m prompt_engine.cli "show all failing pods" --mode kubectl

# kubectl — translate AND execute against live cluster
python -m prompt_engine.cli "restart Harbor registry" --mode kubectl --execute
```

---

## API Endpoints

### `POST /chat` — Conversational AI (auto-routes to Terraform or kubectl)

The main endpoint. Send any message — the engine detects intent and routes automatically.

**Request:**
```json
{ "message": "scale Jenkins to 3 replicas", "execute": false }
```

**Response:**
```json
{
  "reply":    "I'll scale Jenkins to 3 replicas in the jenkins namespace. Command ready — toggle execute to apply.",
  "mode":     "kubectl",
  "commands": ["kubectl scale deployment jenkins --replicas=3 -n jenkins"],
  "risk":     "low",
  "executed": false,
  "results":  null
}
```

**Terraform response example:**
```json
{
  "reply":           "I've generated Terraform to add a Redis ElastiCache cluster and opened a PR for review.",
  "mode":            "terraform",
  "pr_url":          "https://github.com/srujantata/aws-eks-platform/pull/8",
  "files_generated": ["main.tf", "variables.tf", "outputs.tf"],
  "executed":        true
}
```

**General question example:**
```json
// message: "is my cluster healthy?"
{
  "reply": "Your cluster looks healthy. 27 pods are running across 5 namespaces on 2 t3.medium nodes (us-east-1a and us-east-1b). No CrashLoopBackOff or Pending pods detected.",
  "mode":  "general"
}
```

---

### `POST /kubectl` — kubectl Natural Language

```json
{ "prompt": "get the last 50 lines of Harbor logs", "execute": true }
```

Response:
```json
{
  "commands":    ["kubectl logs deploy/harbor-core -n harbor --tail=50"],
  "explanation": "Retrieves the last 50 log lines from the harbor-core deployment.",
  "risk":        "low",
  "warning":     null,
  "results": [
    { "command": "kubectl logs ...", "stdout": "...", "stderr": "", "returncode": 0 }
  ]
}
```

### `POST /kubectl/dry-run` — Translate only, never executes

Same body as `/kubectl` — `execute` flag is always ignored.

---

### `POST /generate` — Terraform → GitHub PR

```json
{
  "prompt":      "Create a VPC with 3 AZs and private subnets with NAT gateway",
  "environment": "poc",
  "repo_name":   "srujantata/aws-eks-platform"
}
```

Returns: `{ "pr_url": "https://github.com/...", "prompt": "...", "environment": "poc" }`

### `POST /generate/dry-run` — Terraform preview, no PR

Same body. Returns the three generated `.tf` files without committing anything.

### `GET /health` — Server health check

```json
{ "status": "ok", "version": "1.0.0" }
```

---

## Example Prompts

### Infrastructure (routes to Terraform → GitHub PR)

| Prompt | What gets generated |
|--------|-------------------|
| `"Add a Redis ElastiCache cluster to POC"` | ElastiCache subnet group + replication group |
| `"Create an RDS PostgreSQL instance"` | RDS module + parameter group + subnet group |
| `"Add a new t3.large node group for CI"` | EKS managed node group Terraform block |
| `"Create an S3 bucket for build artifacts"` | S3 module with versioning + encryption |
| `"Add an Application Load Balancer"` | ALB module + target group + listener |

### Kubernetes Admin (routes to kubectl)

| Prompt | Generated command | Risk |
|--------|------------------|------|
| `"scale Jenkins to 3 replicas"` | `kubectl scale deployment jenkins --replicas=3 -n jenkins` | low |
| `"show all pods not Running"` | `kubectl get pods -A --field-selector=status.phase!=Running` | low |
| `"get SonarQube logs last 100 lines"` | `kubectl logs deploy/sonarqube -n sonarqube --tail=100` | low |
| `"restart Harbor registry"` | `kubectl rollout restart deployment harbor-core -n harbor` | medium |
| `"show resource usage per pod in jenkins"` | `kubectl top pods -n jenkins` | low |
| `"show all PVCs and their status"` | `kubectl get pvc -A` | low |
| `"describe nodes"` | `kubectl describe nodes` | low |
| `"what image is running in harbor-core"` | `kubectl get deploy harbor-core -n harbor -o jsonpath=...` | low |
| `"cordon node ip-10-0-1-219 for maintenance"` | `kubectl cordon ip-10-0-1-219` | high |
| `"rollback jenkins to previous version"` | `kubectl rollout undo deployment jenkins -n jenkins` | high |

### Safety — Always Blocked at Execution

| Blocked pattern | Why |
|----------------|-----|
| `delete cluster` | Destroys the entire EKS cluster |
| `destroy` | Catches eksctl/Terraform destroy |
| `kubectl delete node` | Removes a node permanently |
| `drain` without `--dry-run` | Evicts all pods — requires manual confirmation |

---

## Environment Variables

```bash
# AI Backend — switch between cloud and local
ANTHROPIC_API_KEY=sk-ant-...          # Required if INFRA_AI_BACKEND=anthropic
INFRA_AI_BACKEND=anthropic            # "anthropic" (default) or "ollama"
INFRA_AI_MODEL=claude-sonnet-4-5      # or "codellama:34b" for Ollama
INFRA_AI_BASE_URL=                    # blank for Anthropic; "http://localhost:11434" for Ollama

# GitHub
GITHUB_TOKEN=ghp_...                  # repo + workflow scopes required
GITHUB_DEFAULT_REPO=srujantata/aws-eks-platform

# EKS cluster
EKS_CLUSTER_NAME=devops-poc
AWS_DEFAULT_REGION=us-east-1

# Server
INFRA_ENGINE_URL=http://localhost:8000
INFRA_ENGINE_PORT=8000

# Live tool URLs (update after each terraform apply)
ARGOCD_URL=http://...us-east-1.elb.amazonaws.com
JENKINS_URL=http://...us-east-1.elb.amazonaws.com:8080
SONARQUBE_URL=http://...us-east-1.elb.amazonaws.com:9000
HARBOR_URL=http://...us-east-1.elb.amazonaws.com
```

---

## Local AI — Run on RTX 4090 for $0/month

Skip the Anthropic API entirely. Run all inference locally on your GPU. Fully private — no data leaves your machine.

### Setup (10 minutes)

```powershell
# 1 — Install Ollama
winget install Ollama.Ollama

# 2 — Pull the recommended model (fits in 24GB VRAM, great at Terraform + kubectl)
ollama pull codellama:34b      # ~20GB download, ~25 tok/s on RTX 4090

# 3 — Switch the engine to Ollama (no code changes needed)
[System.Environment]::SetEnvironmentVariable("INFRA_AI_BACKEND","ollama","User")
[System.Environment]::SetEnvironmentVariable("INFRA_AI_MODEL","codellama:34b","User")
[System.Environment]::SetEnvironmentVariable("INFRA_AI_BASE_URL","http://localhost:11434","User")

# 4 — Restart terminal + restart uvicorn — done
```

### Model Guide

| Model | VRAM | Speed | Quality | Use case |
|-------|------|-------|---------|---------|
| `codellama:34b` | 20GB | ~25 tok/s | ⭐⭐⭐⭐ | **Recommended** — Terraform + kubectl |
| `llama3.1:8b` | 8GB | ~80 tok/s | ⭐⭐⭐ | Fast general chat |
| `deepseek-coder-v2:16b` | 12GB | ~45 tok/s | ⭐⭐⭐⭐ | Code generation |
| `llama3.1:70b` | 24GB+RAM | ~8 tok/s | ⭐⭐⭐⭐⭐ | Best quality, partial GPU offload |

### Cost Comparison

| Usage | Anthropic API | Ollama Local |
|-------|--------------|--------------|
| 100 messages/day | ~$8/month | $0 |
| 500 messages/day | ~$35/month | $0 |
| CI/CD automation | ~$80/month | $0 |
| Electricity (RTX 4090, 2h/day) | — | ~$2/month |

→ Full setup guide: **[LOCAL_AI_SETUP.md](LOCAL_AI_SETUP.md)**

---

## Project Structure

```
infra-prompt-engine/
│
├── prompt_engine/
│   ├── generate.py       ← Claude/Ollama API → Terraform HCL → GitHub PR
│   ├── kubectl_exec.py   ← Natural language → kubectl commands + safe execution
│   ├── server.py         ← FastAPI: /chat /kubectl /generate /health
│   ├── cli.py            ← CLI: --mode terraform|kubectl, --execute, --dry-run
│   └── __init__.py
│
├── chat_ui/
│   ├── index.html        ← Single-file PWA chat interface (PC/Mac/Mobile)
│   └── README.md
│
├── tests/
│   ├── test_generate.py  ← Terraform pipeline unit tests (mocked API)
│   └── test_kubectl_exec.py  ← kubectl safety + translation tests
│
├── .github/workflows/
│   └── test.yml          ← pytest CI on every push/PR
│
├── setup_env.ps1         ← Windows one-shot environment setup
├── setup_env.sh          ← Mac/Linux environment setup
├── requirements.txt
├── .env.example
├── LOCAL_AI_SETUP.md     ← Full Ollama + RTX 4090 deployment guide
├── ROADMAP.md            ← 7-phase enhancement vision
└── TEST_RESULTS.md       ← All test results + live cluster verification
```

---

## Test Results

```
$ python -m pytest tests/ -v

tests/test_generate.py::test_returns_three_files        PASSED
tests/test_generate.py::test_strips_markdown_fences     PASSED
tests/test_generate.py::test_raises_on_invalid_json     PASSED
tests/test_generate.py::test_raises_on_missing_keys     PASSED
tests/test_kubectl_exec.py::test_translate_returns_commands       PASSED
tests/test_kubectl_exec.py::test_dry_run_does_not_execute         PASSED
tests/test_kubectl_exec.py::test_invalid_json_raises              PASSED
tests/test_kubectl_exec.py::test_safety_blocks_delete_node        PASSED
tests/test_kubectl_exec.py::test_safety_blocks_delete_cluster     PASSED
tests/test_kubectl_exec.py::test_safety_blocks_destroy            PASSED
tests/test_kubectl_exec.py::test_safety_blocks_drain_without_dry_run  PASSED
tests/test_kubectl_exec.py::test_safety_allows_drain_with_dry_run     PASSED

12 passed in 1.45s
```

→ Full results + live cluster verification: **[TEST_RESULTS.md](TEST_RESULTS.md)**

---

## Roadmap — 7 Phases to Autonomous Ops

| Phase | Feature | Status |
|-------|---------|--------|
| **v1.0** | Prompt → Terraform → GitHub PR | ✅ Live |
| **v1.0** | kubectl natural language admin | ✅ Live |
| **v1.0** | Conversational chat UI (PWA) | ✅ Live |
| **v1.0** | Local AI via Ollama (RTX 4090) | ✅ Live |
| **v2.0** | Self-healing loop — auto-fix CrashLoop, OOMKill, stuck PVCs | 🔲 Planned |
| **v2.1** | Self-patching — CVE scanning, Renovate auto-PRs, node OS updates | 🔲 Planned |
| **v2.2** | Live troubleshooter — k8sgpt, Prometheus + AI alerts, Slack notify | 🔲 Planned |
| **v2.3** | Cost intelligence — AWS Cost Explorer AI, Karpenter Spot optimisation | 🔲 Planned |
| **v3.0** | DR activation via prompt, Istio service mesh, OPA policy engine | 🔲 Planned |
| **v3.1** | Voice interface, mobile push notifications, chaos engineering | 🔲 Planned |
| **v∞** | Zero human ops — AI monitors, heals, patches, optimises autonomously | 🔲 Target |

→ Full implementation plan with architecture diagrams: **[ROADMAP.md](ROADMAP.md)**

---

## Related Repos

| Repo | Purpose |
|------|---------|
| [aws-eks-platform](https://github.com/srujantata/aws-eks-platform) | Terraform EKS cluster — VPC, node groups, EBS CSI, StorageClass |
| [devops-toolchain-helm](https://github.com/srujantata/devops-toolchain-helm) | Helm values — ArgoCD, Jenkins, SonarQube, Harbor |
| [github-actions-iac](https://github.com/srujantata/github-actions-iac) | Reusable GitHub Actions workflows, OIDC auth, no long-lived AWS keys |
| [dr-failover-runbook](https://github.com/srujantata/dr-failover-runbook) | Active-passive DR — Aurora Global DB, Velero, Route53 failover |

---

## Skills Demonstrated

`Python` · `FastAPI` · `Anthropic Claude API` · `Ollama (Local LLM)` · `Terraform` · `AWS EKS` · `kubectl` · `Kubernetes` · `GitHub API (PyGithub)` · `Progressive Web App` · `AI automation` · `pytest` · `CI/CD` · `DevSecOps`
