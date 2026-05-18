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

## Skills Demonstrated
`Python` · `Claude API` · `Anthropic SDK` · `FastAPI` · `GitHub API` · `Terraform` · `AI automation` · `pytest`
