"""
FastAPI server exposing the prompt engine as a REST API.
Run: uvicorn prompt_engine.server:app --reload

Endpoints:
  POST /generate        - Full pipeline: prompt -> Terraform -> GitHub PR
  POST /generate/dry-run - Generate Terraform without opening PR
  GET  /health          - Health check
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

from .generate import generate_terraform, open_pull_request

app = FastAPI(
    title="Infra Prompt Engine",
    description="Convert natural language to Terraform and open GitHub PRs via Claude API",
    version="1.0.0",
)


class GenerateRequest(BaseModel):
    prompt: str
    environment: str = "dev"
    repo_name: str = None


class GenerateResponse(BaseModel):
    pr_url: str
    prompt: str
    environment: str


class DryRunResponse(BaseModel):
    prompt: str
    main_tf: str
    variables_tf: str
    outputs_tf: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "infra-prompt-engine"}


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    """Generate Terraform from prompt and open a GitHub PR."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    if not os.environ.get("GITHUB_TOKEN"):
        raise HTTPException(status_code=500, detail="GITHUB_TOKEN not configured")

    try:
        terraform_files = generate_terraform(req.prompt)
        pr_url = open_pull_request(req.prompt, terraform_files, req.environment, req.repo_name)
        return GenerateResponse(pr_url=pr_url, prompt=req.prompt, environment=req.environment)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/dry-run", response_model=DryRunResponse)
def generate_dry_run(req: GenerateRequest):
    """Generate Terraform from prompt without opening a PR."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    try:
        terraform_files = generate_terraform(req.prompt)
        return DryRunResponse(prompt=req.prompt, **terraform_files)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
