"""
Prompt-to-Terraform engine using Claude API.
Converts natural language infrastructure requests into Terraform HCL
and opens a GitHub pull request for human review.

References:
- Anthropic Messages API: https://docs.anthropic.com/en/api/messages
- PyGithub: https://pygithub.readthedocs.io/en/latest/
"""

import os
import json
import re
from datetime import datetime

import anthropic
from github import Github, GithubException


# ─────────────────────────────────────────
# System prompt for Terraform generation
# ─────────────────────────────────────────
SYSTEM_PROMPT = """You are a senior AWS infrastructure engineer. Generate production-ready Terraform HCL.

RULES:
- Use terraform-aws-modules for VPC (version ~> 5.0) and EKS (version ~> 20.0)
- Always tag resources: Project, Environment, ManagedBy=terraform, Owner
- Use gp3 storage class for EBS volumes
- Enable encryption on all resources (S3, RDS, EBS, DynamoDB)
- Use us-east-1 as default region unless specified
- Output exactly 3 files as a JSON object with keys: main_tf, variables_tf, outputs_tf
- Each value is the file content as a string
- Include helpful comments explaining key decisions
- Do NOT include markdown code fences in the output — raw JSON only

RESPONSE FORMAT (strict JSON, no markdown):
{
  "main_tf": "terraform { ... }",
  "variables_tf": "variable \\"region\\" { ... }",
  "outputs_tf": "output \\"vpc_id\\" { ... }"
}"""


def generate_terraform(prompt: str, model: str = "claude-sonnet-4-5") -> dict:
    """
    Call Claude API to generate Terraform HCL from a natural language prompt.

    Args:
        prompt: Natural language description of infrastructure to create
        model: Claude model to use (default: claude-sonnet-4-5)

    Returns:
        dict with keys: main_tf, variables_tf, outputs_tf

    Raises:
        ValueError: If Claude response is not valid JSON with expected keys
        anthropic.APIError: On API communication errors
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model=model,
        max_tokens=8096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Generate Terraform HCL for: {prompt}"
            }
        ]
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if model included them despite instructions
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude returned invalid JSON: {e}\nRaw output:\n{raw[:500]}")

    required_keys = {"main_tf", "variables_tf", "outputs_tf"}
    missing = required_keys - set(result.keys())
    if missing:
        raise ValueError(f"Claude response missing required keys: {missing}")

    return result


def open_pull_request(
    prompt: str,
    terraform_files: dict,
    environment: str = "dev",
    repo_name: str = None,
) -> str:
    """
    Commit generated Terraform files to a new branch and open a GitHub PR.

    Args:
        prompt: Original user prompt (used for branch name + PR title)
        terraform_files: dict with main_tf, variables_tf, outputs_tf content
        environment: Target environment folder (dev/staging/prod)
        repo_name: GitHub repo in format "owner/repo" (defaults to GITHUB_REPO env var)

    Returns:
        PR URL string

    Raises:
        GithubException: On GitHub API errors
        EnvironmentError: If required env vars are missing
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise EnvironmentError("GITHUB_TOKEN environment variable not set")

    repo_name = repo_name or os.environ.get("GITHUB_REPO", "srujantata/aws-eks-platform")

    gh = Github(token)
    repo = gh.get_repo(repo_name)

    # Create branch name from prompt slug
    slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower())[:40].strip("-")
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    branch_name = f"claude/infra-{slug}-{timestamp}"

    # Get base SHA
    base_sha = repo.get_branch("master").commit.sha

    # Create branch
    repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)

    # Commit files
    base_path = f"terraform/environments/{environment}"
    file_map = {
        f"{base_path}/main.tf": terraform_files["main_tf"],
        f"{base_path}/variables.tf": terraform_files["variables_tf"],
        f"{base_path}/outputs.tf": terraform_files["outputs_tf"],
    }

    for file_path, content in file_map.items():
        try:
            # Update if exists
            existing = repo.get_contents(file_path, ref=branch_name)
            repo.update_file(
                path=file_path,
                message=f"auto: update {file_path.split('/')[-1]}",
                content=content,
                sha=existing.sha,
                branch=branch_name,
            )
        except GithubException:
            # Create new
            repo.create_file(
                path=file_path,
                message=f"auto: add {file_path.split('/')[-1]}",
                content=content,
                branch=branch_name,
            )

    # Open PR
    pr = repo.create_pull(
        title=f"[AI Infra] {prompt[:70]}",
        body=f"""## AI-Generated Infrastructure

**Request:** {prompt}

**Environment:** `{environment}`

**Generated files:**
- `{base_path}/main.tf`
- `{base_path}/variables.tf`
- `{base_path}/outputs.tf`

---
### Review checklist
- [ ] Terraform plan output looks correct (check PR comment after CI runs)
- [ ] Resource names and tags match conventions
- [ ] No sensitive values hardcoded
- [ ] Approved to apply

---
*Generated by [infra-prompt-engine](https://github.com/srujantata/infra-prompt-engine) using Claude API*""",
        head=branch_name,
        base="master",
    )

    return pr.html_url


def generate_and_pr(
    prompt: str,
    environment: str = "dev",
    repo_name: str = None,
    dry_run: bool = False,
) -> str:
    """
    Full pipeline: prompt → Terraform → GitHub PR.

    Args:
        prompt: Natural language infrastructure request
        environment: Target environment (dev/staging/prod)
        repo_name: GitHub repo (owner/repo format)
        dry_run: If True, print Terraform but don't open PR

    Returns:
        PR URL (or Terraform content if dry_run=True)
    """
    print(f"Generating Terraform for: {prompt}")
    terraform_files = generate_terraform(prompt)

    if dry_run:
        print("\n=== main.tf ===")
        print(terraform_files["main_tf"])
        print("\n=== variables.tf ===")
        print(terraform_files["variables_tf"])
        print("\n=== outputs.tf ===")
        print(terraform_files["outputs_tf"])
        return "dry-run"

    print("Opening GitHub PR...")
    pr_url = open_pull_request(prompt, terraform_files, environment, repo_name)
    print(f"PR created: {pr_url}")
    return pr_url
