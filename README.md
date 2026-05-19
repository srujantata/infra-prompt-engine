# infra-prompt-engine

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)
![Claude](https://img.shields.io/badge/Claude-API-000000)
![Tests](https://github.com/srujantata/infra-prompt-engine/actions/workflows/test.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)

Natural language → Terraform HCL → GitHub PR. Describe infrastructure in plain English; this engine calls the Claude API to generate valid Terraform and automatically opens a pull request for human review before anything is applied.

## How It Works

```
User prompt → Claude API (claude-sonnet) → Terraform HCL (3 files)
    → GitHub branch → PR opened → GitHub Actions runs terraform plan
    → Human reviews plan in PR comment → Merges → terraform apply
```

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY and GITHUB_TOKEN

# CLI — opens a real GitHub PR
python -m prompt_engine.cli "Create an S3 bucket with versioning and encryption"

# CLI — dry run (prints Terraform, no PR)
python -m prompt_engine.cli --dry-run "Create a VPC with 3 AZs and NAT gateway"

# API server
uvicorn prompt_engine.server:app --reload
# POST http://localhost:8000/generate
# POST http://localhost:8000/generate/dry-run
```

## API

### POST /generate
```json
{
  "prompt": "Create a VPC with 3 AZs and private subnets",
  "environment": "dev",
  "repo_name": "srujantata/aws-eks-platform"
}
```
Returns: `{ "pr_url": "https://github.com/...", "prompt": "...", "environment": "dev" }`

### POST /generate/dry-run
Same request body. Returns the generated Terraform files without opening a PR.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Always | Anthropic API key (`sk-ant-...`) |
| `GITHUB_TOKEN` | For PR creation | GitHub token with `repo` + `workflow` scopes |
| `GITHUB_REPO` | Optional | Default target repo (`owner/repo`) |

## Project Structure

```
prompt_engine/
├── __init__.py
├── generate.py    ← Core: Claude API call + GitHub PR creation
├── cli.py         ← CLI entry point
└── server.py      ← FastAPI REST server

tests/
└── test_generate.py  ← Unit tests (mock Claude API)

.github/workflows/
└── test.yml       ← Run pytest on every PR
```

## kubectl Natural Language Administration

Translate plain-English Kubernetes admin requests into `kubectl` commands — and optionally execute them against the live `devops-poc` cluster.

### Example Prompts

| Prompt | Generated command(s) | Risk |
|--------|----------------------|------|
| `scale Jenkins to 3 replicas` | `kubectl scale deployment jenkins --replicas=3 -n jenkins` | low |
| `show me all pods that are not Running` | `kubectl get pods -A --field-selector=status.phase!=Running` | low |
| `get the last 100 lines of SonarQube logs` | `kubectl logs deploy/sonarqube -n sonarqube --tail=100` | low |
| `restart the Harbor registry deployment` | `kubectl rollout restart deployment harbor-core -n harbor` | medium |
| `describe the devops-poc node group` | `kubectl describe nodes` | low |
| `show resource usage for all pods in jenkins namespace` | `kubectl top pods -n jenkins` | low |
| `create a configmap named app-config in jenkins with key=value` | `kubectl create configmap app-config --from-literal=key=value -n jenkins` | medium |
| `what is the current image tag running in harbor-core` | `kubectl get deploy harbor-core -n harbor -o jsonpath='{.spec.template.spec.containers[0].image}'` | low |
| `show all PVCs and their bound status` | `kubectl get pvc -A` | low |
| `cordon node ip-10-0-1-219 for maintenance` | `kubectl cordon ip-10-0-1-219` | high |

### API Endpoints

#### POST /kubectl
Translate (and optionally execute) a plain-English request.

```json
{ "prompt": "scale Jenkins to 3 replicas", "execute": false }
```

Response:
```json
{
  "commands":    ["kubectl scale deployment jenkins --replicas=3 -n jenkins"],
  "explanation": "Scales the Jenkins deployment in the jenkins namespace to 3 replicas.",
  "risk":        "low",
  "warning":     null,
  "results":     null
}
```

Set `"execute": true` to run the commands live. `results` will then be a list of
`{command, stdout, stderr, returncode}` objects.

#### POST /kubectl/dry-run
Identical to `/kubectl` but the `execute` flag in the request body is always ignored —
commands are never run. Safe for use in pipelines or code review workflows.

### CLI Usage

```bash
# Translate only (default — safe, no cluster access)
python -m prompt_engine.cli "scale Jenkins to 3 replicas" --mode kubectl

# Translate and execute
python -m prompt_engine.cli "show all failing pods" --mode kubectl --execute
python -m prompt_engine.cli "get Jenkins logs last 50 lines" --mode kubectl --execute
python -m prompt_engine.cli "restart the Harbor registry deployment" --mode kubectl --execute

# Terraform mode still works as before
python -m prompt_engine.cli "Create a VPC with 3 AZs" --mode terraform
python -m prompt_engine.cli --dry-run "Create an RDS cluster"
```

### Safety

The following operations are **always blocked** at execution time, regardless of `--execute`:

| Blocked pattern | Why |
|-----------------|-----|
| `delete cluster` | Destroys the entire EKS cluster |
| `destroy` | Catches Terraform/eksctl destroy commands |
| `kubectl delete node` | Removes a node from the cluster |
| `drain` without `--dry-run` | Evicts all pods from a node; requires explicit confirmation |

To perform these operations, run them manually after reviewing the generated command.
High-risk commands (risk=`high`) show a warning in both the API response and CLI output.

---

## Skills Demonstrated
`Python` · `Claude API` · `Anthropic SDK` · `FastAPI` · `GitHub API` · `Terraform` · `kubectl` · `Kubernetes` · `AI automation` · `pytest`
