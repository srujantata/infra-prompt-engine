"""
Natural language → kubectl command translator + executor.
Uses Claude to translate a plain-English admin request into one or more
kubectl commands, then optionally executes them against the live cluster.

Safety model:
  - translate_to_kubectl() is always safe — it only calls the Claude API.
  - execute_kubectl() refuses any command containing destructive patterns
    (delete cluster, destroy, kubectl delete node, drain without --dry-run).
  - run_kubectl_prompt() is the main entrypoint: translate → optionally execute.
"""

import json
import os
import re
import subprocess

import anthropic


# ─────────────────────────────────────────
# System prompt for kubectl translation
# ─────────────────────────────────────────
KUBECTL_SYSTEM_PROMPT = (
    "You are a Kubernetes administrator. Translate the user's request into kubectl "
    "commands for a cluster named 'devops-poc'. Return JSON only: "
    '{"commands": ["kubectl ...", ...], "explanation": "...", '
    '"risk": "low|medium|high", "warning": "...or null"}'
)

# Patterns that are unconditionally blocked at execution time
_BLOCKED_PATTERNS = [
    r"delete\s+cluster",
    r"destroy",
    r"kubectl\s+delete\s+node",
    r"\bdrain\b(?!.*--dry-run)",  # drain is OK only when paired with --dry-run
]


# ─────────────────────────────────────────
# Core functions
# ─────────────────────────────────────────

def translate_to_kubectl(prompt: str, dry_run: bool = True) -> dict:
    """
    Translate a plain-English Kubernetes admin request into kubectl commands.

    Args:
        prompt:   Natural language request, e.g. "scale Jenkins to 3 replicas"
        dry_run:  Passed through to the caller; does NOT affect the Claude call
                  (translation is always safe).  Stored in the returned dict so
                  the caller can decide whether to execute.

    Returns:
        {
            "commands":    ["kubectl ...", ...],
            "explanation": "What these commands do",
            "risk":        "low" | "medium" | "high",
            "warning":     "string or null",
            "dry_run":     True | False,
        }

    Raises:
        ValueError: If Claude returns non-JSON or is missing required keys.
        anthropic.APIError: On API communication failures.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        system=KUBECTL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if model included them despite the instruction
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Claude returned invalid JSON: {e}\nRaw output:\n{raw[:500]}"
        )

    required_keys = {"commands", "explanation", "risk", "warning"}
    missing = required_keys - set(result.keys())
    if missing:
        raise ValueError(f"Claude response missing required keys: {missing}")

    if not isinstance(result["commands"], list):
        raise ValueError("'commands' must be a JSON array")

    result["dry_run"] = dry_run
    return result


def execute_kubectl(commands: list) -> list:
    """
    Execute a list of kubectl commands and return their output.

    Safety check: raises ValueError before running anything if any command
    matches a blocked pattern (delete cluster / destroy / delete node /
    drain without --dry-run).

    Args:
        commands: List of kubectl command strings.

    Returns:
        List of dicts: [{command, stdout, stderr, returncode}, ...]

    Raises:
        ValueError: If any command matches a blocked pattern.
    """
    # --- Safety gate: check ALL commands before executing ANY ---
    for cmd in commands:
        for pattern in _BLOCKED_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                raise ValueError(
                    f"Execution blocked — command contains a disallowed pattern "
                    f"({pattern!r}): {cmd!r}\n"
                    "If this operation is intentional, run it manually with "
                    "explicit confirmation after reviewing the impact."
                )

    results = []
    for cmd in commands:
        try:
            proc = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=30,
            )
            results.append(
                {
                    "command": cmd,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "returncode": proc.returncode,
                }
            )
        except subprocess.TimeoutExpired:
            results.append(
                {
                    "command": cmd,
                    "stdout": "",
                    "stderr": "ERROR: command timed out after 30 seconds",
                    "returncode": -1,
                }
            )

    return results


def run_kubectl_prompt(prompt: str, execute: bool = False) -> dict:
    """
    Full pipeline: natural language → kubectl commands → optional execution.

    Args:
        prompt:  Plain-English Kubernetes admin request.
        execute: If True, run the translated commands against the live cluster.
                 Defaults to False (safe — translate only).

    Returns:
        {
            "commands":    [...],
            "explanation": "...",
            "risk":        "low|medium|high",
            "warning":     "...|null",
            "dry_run":     bool,
            "results":     [...] or None,   # None when execute=False
        }
    """
    translation = translate_to_kubectl(prompt, dry_run=not execute)

    if execute:
        translation["results"] = execute_kubectl(translation["commands"])
    else:
        translation["results"] = None

    return translation
