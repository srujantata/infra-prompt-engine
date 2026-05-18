"""
CLI entry point for infra-prompt-engine.
Usage: python -m prompt_engine.cli "Create a VPC with 3 AZs"
"""

import argparse
import os
import sys

from .generate import generate_and_pr


def main():
    parser = argparse.ArgumentParser(
        description="Generate Terraform from natural language and open a GitHub PR"
    )
    parser.add_argument("prompt", help="Natural language infrastructure request")
    parser.add_argument(
        "--env",
        default="dev",
        choices=["dev", "staging", "prod"],
        help="Target environment (default: dev)",
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="GitHub repo in owner/repo format (default: GITHUB_REPO env var)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated Terraform without opening a PR",
    )

    args = parser.parse_args()

    # Validate required env vars
    missing = []
    if not os.environ.get("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if not args.dry_run and not os.environ.get("GITHUB_TOKEN"):
        missing.append("GITHUB_TOKEN")
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        print("Copy .env.example to .env and fill in the values.", file=sys.stderr)
        sys.exit(1)

    result = generate_and_pr(args.prompt, args.env, args.repo, args.dry_run)
    if result != "dry-run":
        print(f"\nSuccess! Review and merge: {result}")


if __name__ == "__main__":
    main()
