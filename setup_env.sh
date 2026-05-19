#!/usr/bin/env bash
# DevOps Platform — Environment Setup (Mac / Linux)
# Run once: source ./setup_env.sh   (or: bash setup_env.sh && source ~/.bashrc)
#
# Writes variables to ~/.bashrc AND ~/.zshrc so they survive terminal restarts.
# On Mac the default shell is zsh; on most Linux distros it is bash.

set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
GRAY='\033[0;90m'
RESET='\033[0m'

echo -e "${CYAN}Setting up DevOps Platform environment variables...${RESET}"
echo ""

# ── Variable definitions ──────────────────────────────────────────────────────
declare -A VARS=(
    # AI Backend — swap INFRA_AI_BACKEND to "ollama" to run locally (free)
    [ANTHROPIC_API_KEY]="YOUR_ANTHROPIC_API_KEY_HERE"
    [INFRA_AI_BACKEND]="anthropic"            # "anthropic" or "ollama"
    [INFRA_AI_MODEL]="claude-sonnet-4-5"      # or "llama3.1:70b" for Ollama
    [INFRA_AI_BASE_URL]=""                    # blank = Anthropic; "http://localhost:11434" for Ollama

    # GitHub
    [GITHUB_TOKEN]="YOUR_GITHUB_TOKEN_HERE"
    [GITHUB_DEFAULT_REPO]="srujantata/aws-eks-platform"

    # EKS cluster
    [EKS_CLUSTER_NAME]="devops-poc"
    [AWS_DEFAULT_REGION]="us-east-1"

    # Prompt engine server
    [INFRA_ENGINE_URL]="http://localhost:8000"
    [INFRA_ENGINE_PORT]="8000"

    # Tool URLs (update these after each terraform apply)
    [ARGOCD_URL]="http://a944fe58b20d24057b8cf0af7f586c3a-245014201.us-east-1.elb.amazonaws.com"
    [JENKINS_URL]="http://a910314d11cee49a99b923e221108e05-468852420.us-east-1.elb.amazonaws.com:8080"
    [SONARQUBE_URL]="http://a386f7224766d43d6b50aeee825abe34-1292105297.us-east-1.elb.amazonaws.com:9000"
    [HARBOR_URL]="http://a68756541aa5a454d81e6515e061e3c2-574233704.us-east-1.elb.amazonaws.com"
)

# ── Write to shell RC files ───────────────────────────────────────────────────
RC_FILES=()
[[ -f "$HOME/.bashrc" ]] && RC_FILES+=("$HOME/.bashrc")
[[ -f "$HOME/.zshrc"  ]] && RC_FILES+=("$HOME/.zshrc")
# Create .bashrc if neither exists (fresh Linux install)
if [[ ${#RC_FILES[@]} -eq 0 ]]; then
    touch "$HOME/.bashrc"
    RC_FILES+=("$HOME/.bashrc")
fi

for KEY in "${!VARS[@]}"; do
    VALUE="${VARS[$KEY]}"

    # Export in current shell
    export "$KEY"="$VALUE"
    echo -e "  ${GREEN}SET $KEY${RESET}"

    # Persist to each RC file — remove old line then append
    for RC in "${RC_FILES[@]}"; do
        # Remove any previous export of this key
        sed -i.bak "/^export ${KEY}=/d" "$RC" 2>/dev/null || true
        echo "export ${KEY}=\"${VALUE}\"" >> "$RC"
    done
done

echo ""
echo -e "${YELLOW}Done! Variables exported for this session and written to:${RESET}"
for RC in "${RC_FILES[@]}"; do
    echo "  $RC"
done

echo ""
echo -e "${GRAY}────────────────────────────────────────────────────────────${RESET}"
echo -e "${CYAN}To switch to local Ollama (free, no API costs):${RESET}"
echo "  Mac:"
echo "    brew install ollama"
echo "    ollama pull llama3.1:70b"
echo "  Linux:"
echo "    curl -fsSL https://ollama.com/install.sh | sh"
echo "    ollama pull llama3.1:70b"
echo ""
echo "  Then switch the three variables (re-run or set manually):"
echo '    export INFRA_AI_BACKEND="ollama"'
echo '    export INFRA_AI_MODEL="llama3.1:70b"'
echo '    export INFRA_AI_BASE_URL="http://localhost:11434"'
echo ""
echo -e "${GRAY}────────────────────────────────────────────────────────────${RESET}"
echo -e "${CYAN}To start the prompt engine:${RESET}"
echo "  cd /path/to/infra-prompt-engine"
echo "  uvicorn prompt_engine.server:app --reload --port 8000"
echo ""
echo -e "${GRAY}────────────────────────────────────────────────────────────${RESET}"
echo -e "${CYAN}To open the Chat UI:${RESET}"
echo "  Open chat_ui/index.html in your browser, or:"
echo "  python3 -m http.server 3000 --directory chat_ui"
echo "  Then visit http://localhost:3000"
echo ""
