"""
FastAPI server exposing the prompt engine as a REST API.
Run: uvicorn prompt_engine.server:app --reload

Endpoints:
  POST /generate        - Full pipeline: prompt -> Terraform -> GitHub PR
  POST /generate/dry-run - Generate Terraform without opening PR
  POST /kubectl         - Translate (and optionally execute) kubectl commands
  POST /kubectl/dry-run - Translate kubectl commands only (never executes)
  POST /chat            - Conversational AI assistant for infra + kubectl tasks
  GET  /health          - Health check
"""

import json
import os
import re

import anthropic
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .generate import generate_terraform, open_pull_request, _make_client, AI_MODEL
from .kubectl_exec import run_kubectl_prompt

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


# ─────────────────────────────────────────
# kubectl natural-language admin endpoints
# ─────────────────────────────────────────

class KubectlRequest(BaseModel):
    prompt: str
    execute: bool = False  # default safe — translate only, do not run


class KubectlResponse(BaseModel):
    commands: list[str]
    explanation: str
    risk: str
    warning: str | None
    results: list[dict] | None  # None when execute=False


@app.post("/kubectl", response_model=KubectlResponse)
def kubectl_admin(req: KubectlRequest):
    """
    Translate a plain-English Kubernetes admin request into kubectl commands
    and optionally execute them against the live cluster.

    Set execute=false (default) for safe translation-only mode.
    Set execute=true to run the commands — high-risk operations (delete cluster,
    destroy, delete node, drain without --dry-run) are always blocked.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    try:
        result = run_kubectl_prompt(req.prompt, execute=req.execute)
        return KubectlResponse(
            commands=result["commands"],
            explanation=result["explanation"],
            risk=result["risk"],
            warning=result["warning"],
            results=result.get("results"),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/kubectl/dry-run", response_model=KubectlResponse)
def kubectl_dry_run(req: KubectlRequest):
    """
    Translate a plain-English Kubernetes admin request into kubectl commands
    without executing them — execute flag in request body is ignored.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    try:
        result = run_kubectl_prompt(req.prompt, execute=False)
        return KubectlResponse(
            commands=result["commands"],
            explanation=result["explanation"],
            risk=result["risk"],
            warning=result["warning"],
            results=None,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────
# /chat — conversational assistant
# ─────────────────────────────────────────

# Intent classifier system prompt — returns JSON only
_INTENT_SYSTEM = (
    "Classify this infrastructure request as 'kubectl', 'terraform', or 'general'. "
    "Return JSON only: {\"intent\": \"kubectl|terraform|general\"}. "
    "kubectl: anything about pods, deployments, scaling, logs, nodes, namespaces, "
    "services, ingress, helm, restarts, rollouts, resource usage. "
    "terraform: anything about creating/modifying/destroying AWS infrastructure, "
    "new clusters, databases, S3, networking, EKS, RDS, ElastiCache, IAM, storage. "
    "general: questions about status, health checks, explanations, comparisons, "
    "or anything else."
)

# Conversational reply system prompt
_CHAT_SYSTEM = """You are a friendly, expert DevOps assistant embedded in the infra-prompt-engine.
You help engineers manage a Kubernetes cluster called 'devops-poc' on EKS (us-east-1) running
Jenkins, ArgoCD, SonarQube, and Harbor.

When answering:
- Be concise and conversational — no walls of text
- For kubectl operations: explain what you'll run and why it's safe (or flag if risky)
- For Terraform: describe what will be created and mention that a PR will be opened for review
- For status/health: summarise results in plain English, highlight anything concerning
- Always mention execute=true if the user needs to actually apply the change
- Use short code blocks for commands, avoid over-formatting"""


def _detect_intent(message: str, client: anthropic.Anthropic) -> str:
    """Ask Claude to classify the message intent. Returns 'kubectl', 'terraform', or 'general'."""
    resp = client.messages.create(
        model=AI_MODEL,
        max_tokens=64,
        system=_INTENT_SYSTEM,
        messages=[{"role": "user", "content": message}],
    )
    raw = resp.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    try:
        return json.loads(raw).get("intent", "general")
    except (json.JSONDecodeError, AttributeError):
        return "general"


def _build_kubectl_reply(
    message: str,
    execute: bool,
    client: anthropic.Anthropic,
) -> dict:
    """Route to kubectl pipeline and build a conversational ChatResponse dict."""
    result = run_kubectl_prompt(message, execute=execute)

    # Ask Claude to write a friendly reply summarising the operation
    summary_prompt = (
        f"User asked: {message!r}\n"
        f"Commands prepared: {result['commands']}\n"
        f"Explanation: {result['explanation']}\n"
        f"Risk: {result['risk']}\n"
        f"Executed: {execute}\n"
        f"Results: {result.get('results')}\n\n"
        "Write a short, conversational reply (2-4 sentences) explaining what was done "
        "or what is ready to run. If not executed, invite the user to set execute=true."
    )
    reply_resp = client.messages.create(
        model=AI_MODEL,
        max_tokens=512,
        system=_CHAT_SYSTEM,
        messages=[{"role": "user", "content": summary_prompt}],
    )
    reply = reply_resp.content[0].text.strip()

    return {
        "reply": reply,
        "mode": "kubectl",
        "commands": result["commands"],
        "risk": result["risk"],
        "executed": execute,
        "results": result.get("results"),
        "pr_url": None,
        "files_generated": None,
    }


def _build_terraform_reply(
    message: str,
    execute: bool,
    client: anthropic.Anthropic,
) -> dict:
    """Route to Terraform pipeline and build a conversational ChatResponse dict."""
    terraform_files = generate_terraform(message)

    pr_url = None
    files_generated = list(terraform_files.keys())

    if execute:
        if not os.environ.get("GITHUB_TOKEN"):
            raise ValueError("GITHUB_TOKEN not configured — cannot open PR")
        pr_url = open_pull_request(message, terraform_files)

    # Ask Claude to write a friendly reply
    summary_prompt = (
        f"User asked: {message!r}\n"
        f"Terraform files generated: {files_generated}\n"
        f"PR opened: {pr_url or 'no (execute=false)'}\n\n"
        "Write a short, conversational reply (2-4 sentences) describing what infrastructure "
        "will be created and the next step (review PR or set execute=true)."
    )
    reply_resp = client.messages.create(
        model=AI_MODEL,
        max_tokens=512,
        system=_CHAT_SYSTEM,
        messages=[{"role": "user", "content": summary_prompt}],
    )
    reply = reply_resp.content[0].text.strip()

    return {
        "reply": reply,
        "mode": "terraform",
        "commands": None,
        "risk": "medium",
        "executed": execute and pr_url is not None,
        "results": None,
        "pr_url": pr_url,
        "files_generated": files_generated,
    }


def _build_general_reply(
    message: str,
    execute: bool,
    client: anthropic.Anthropic,
) -> dict:
    """
    Handle general questions — auto-fetches cluster status when relevant,
    then composes a conversational reply.
    """
    # Keywords that suggest we should pull live cluster data first
    status_keywords = re.compile(
        r"\b(pod|pods|node|nodes|namespace|health|healthy|running|cluster|status|memory|cpu|usage)\b",
        re.IGNORECASE,
    )

    cluster_context = ""
    commands_run: list[dict] = []

    if status_keywords.search(message):
        # Gather live data; swallow errors gracefully — no kubeconfig in CI is fine
        try:
            pods_result = run_kubectl_prompt("list all pods in all namespaces", execute=True)
            nodes_result = run_kubectl_prompt("get all nodes with status", execute=True)
            commands_run = (pods_result.get("results") or []) + (nodes_result.get("results") or [])

            pods_out = "\n".join(
                r["stdout"] for r in (pods_result.get("results") or []) if r["stdout"]
            )
            nodes_out = "\n".join(
                r["stdout"] for r in (nodes_result.get("results") or []) if r["stdout"]
            )
            cluster_context = (
                f"\n\n--- Live cluster data ---\nPods:\n{pods_out}\n\nNodes:\n{nodes_out}"
            )
        except Exception:
            cluster_context = "\n\n(Could not reach cluster — kubeconfig may not be configured.)"

    reply_resp = client.messages.create(
        model=AI_MODEL,
        max_tokens=1024,
        system=_CHAT_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": message + cluster_context,
            }
        ],
    )
    reply = reply_resp.content[0].text.strip()

    return {
        "reply": reply,
        "mode": "general",
        "commands": None,
        "risk": None,
        "executed": bool(commands_run),
        "results": commands_run or None,
        "pr_url": None,
        "files_generated": None,
    }


class ChatRequest(BaseModel):
    message: str
    execute: bool = False


class ChatResponse(BaseModel):
    reply: str
    mode: str                        # "kubectl" | "terraform" | "general"
    commands: list[str] | None = None
    risk: str | None = None
    executed: bool = False
    results: list[dict] | None = None
    pr_url: str | None = None
    files_generated: list[str] | None = None


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Conversational assistant for infra + Kubernetes operations.

    Auto-detects intent:
      - kubectl  → translates to kubectl commands, optionally executes
      - terraform → generates Terraform HCL, optionally opens GitHub PR
      - general  → answers questions; auto-fetches cluster status when relevant

    The 'reply' field is always a plain-English conversational response.
    Set execute=true to apply kubectl commands or open a Terraform PR.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    try:
        client = _make_client()
        intent = _detect_intent(req.message, client)

        if intent == "kubectl":
            data = _build_kubectl_reply(req.message, req.execute, client)
        elif intent == "terraform":
            data = _build_terraform_reply(req.message, req.execute, client)
        else:
            data = _build_general_reply(req.message, req.execute, client)

        return ChatResponse(**data)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
