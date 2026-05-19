"""
CLI entry point for infra-prompt-engine.

Terraform mode (default):
  python -m prompt_engine.cli "Create a VPC with 3 AZs"
  python -m prompt_engine.cli --dry-run "Create an RDS cluster"

kubectl mode:
  python -m prompt_engine.cli --mode kubectl "scale Jenkins to 3 replicas"
  python -m prompt_engine.cli --mode kubectl --execute "show all failing pods"
  python -m prompt_engine.cli --mode kubectl --execute "get Jenkins logs last 50 lines"
"""

import argparse
import json
import os
import sys

from .generate import generate_and_pr


def _run_kubectl_mode(prompt: str, execute: bool) -> None:
    """Handle --mode kubectl: translate (and optionally execute) a kubectl prompt."""
    # Import here so the terraform path never pulls in kubectl_exec needlessly
    from .kubectl_exec import run_kubectl_prompt  # noqa: PLC0415

    print(f"Translating: {prompt}")
    result = run_kubectl_prompt(prompt, execute=execute)

    print(f"\nExplanation : {result['explanation']}")
    print(f"Risk level  : {result['risk'].upper()}")
    if result.get("warning"):
        print(f"WARNING     : {result['warning']}")

    print("\nCommands:")
    for cmd in result["commands"]:
        print(f"  {cmd}")

    if execute and result.get("results"):
        print("\nExecution results:")
        for item in result["results"]:
            print(f"\n  $ {item['command']}")
            print(f"  exit={item['returncode']}")
            if item["stdout"]:
                print(item["stdout"].rstrip())
            if item["stderr"]:
                print(f"  [stderr] {item['stderr'].rstrip()}", file=sys.stderr)
    elif not execute:
        print("\n(Use --execute to run these commands against the live cluster.)")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "infra-prompt-engine CLI — generate Terraform or translate kubectl commands "
            "from natural language"
        )
    )
    parser.add_argument("prompt", help="Natural language request")

    # ── mode ──────────────────────────────────────────────────────────────────
    parser.add_argument(
        "--mode",
        default="terraform",
        choices=["terraform", "kubectl"],
        help="Operation mode: terraform (default) or kubectl",
    )

    # ── terraform-only flags ──────────────────────────────────────────────────
    parser.add_argument(
        "--env",
        default="dev",
        choices=["dev", "staging", "prod"],
        help="[terraform] Target environment (default: dev)",
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="[terraform] GitHub repo in owner/repo format (default: GITHUB_REPO env var)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="[terraform] Print generated Terraform without opening a PR",
    )

    # ── kubectl-only flags ────────────────────────────────────────────────────
    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "[kubectl] Execute the translated commands against the live cluster. "
            "Defaults to False (translate only). "
            "Destructive commands (delete cluster/node, drain without --dry-run) "
            "are always blocked."
        ),
    )

    args = parser.parse_args()

    # ── validate env vars ─────────────────────────────────────────────────────
    missing = []
    if not os.environ.get("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if args.mode == "terraform" and not args.dry_run and not os.environ.get("GITHUB_TOKEN"):
        missing.append("GITHUB_TOKEN")
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        print("Copy .env.example to .env and fill in the values.", file=sys.stderr)
        sys.exit(1)

    # ── dispatch ──────────────────────────────────────────────────────────────
    if args.mode == "kubectl":
        _run_kubectl_mode(args.prompt, execute=args.execute)
    else:
        result = generate_and_pr(args.prompt, args.env, args.repo, args.dry_run)
        if result != "dry-run":
            print(f"\nSuccess! Review and merge: {result}")


if __name__ == "__main__":
    main()
