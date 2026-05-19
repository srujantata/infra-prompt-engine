# DevOps Platform — Environment Setup
# Run once: .\setup_env.ps1
# Sets all required environment variables permanently in User scope (no admin required).
# Restart your terminal after running this script for changes to take effect.

Write-Host "Setting up DevOps Platform environment variables..." -ForegroundColor Cyan
Write-Host ""

$vars = @{
    # ── AI Backend ────────────────────────────────────────────────────────────
    # Swap INFRA_AI_BACKEND to "ollama" to use a local model (free, uses RTX 4090)
    "ANTHROPIC_API_KEY"        = "YOUR_ANTHROPIC_API_KEY_HERE"
    "INFRA_AI_BACKEND"         = "anthropic"           # "anthropic" or "ollama"
    "INFRA_AI_MODEL"           = "claude-sonnet-4-5"   # or "llama3.1:70b" for Ollama
    "INFRA_AI_BASE_URL"        = ""                    # blank = Anthropic; "http://localhost:11434" for Ollama

    # ── GitHub ────────────────────────────────────────────────────────────────
    "GITHUB_TOKEN"             = "YOUR_GITHUB_TOKEN_HERE"
    "GITHUB_DEFAULT_REPO"      = "srujantata/aws-eks-platform"

    # ── EKS cluster ──────────────────────────────────────────────────────────
    "EKS_CLUSTER_NAME"         = "devops-poc"
    "AWS_DEFAULT_REGION"       = "us-east-1"

    # ── Prompt engine server ──────────────────────────────────────────────────
    "INFRA_ENGINE_URL"         = "http://localhost:8000"
    "INFRA_ENGINE_PORT"        = "8000"

    # ── Tool URLs (update these after each terraform apply) ───────────────────
    "ARGOCD_URL"               = "http://a944fe58b20d24057b8cf0af7f586c3a-245014201.us-east-1.elb.amazonaws.com"
    "JENKINS_URL"              = "http://a910314d11cee49a99b923e221108e05-468852420.us-east-1.elb.amazonaws.com:8080"
    "SONARQUBE_URL"            = "http://a386f7224766d43d6b50aeee825abe34-1292105297.us-east-1.elb.amazonaws.com:9000"
    "HARBOR_URL"               = "http://a68756541aa5a454d81e6515e061e3c2-574233704.us-east-1.elb.amazonaws.com"
}

foreach ($key in $vars.Keys) {
    [System.Environment]::SetEnvironmentVariable($key, $vars[$key], "User")
    Write-Host "  SET $key" -ForegroundColor Green
}

Write-Host ""
Write-Host "Done! Restart your terminal for changes to take effect." -ForegroundColor Yellow

Write-Host ""
Write-Host "────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "To switch to local Ollama (free, uses your RTX 4090):" -ForegroundColor Cyan
Write-Host "  1. Install Ollama:" -ForegroundColor White
Write-Host "       winget install Ollama.Ollama" -ForegroundColor DarkYellow
Write-Host "  2. Pull a model (llama3.1:70b fits in 48 GB VRAM):" -ForegroundColor White
Write-Host "       ollama pull llama3.1:70b" -ForegroundColor DarkYellow
Write-Host "  3. Switch the three env vars:" -ForegroundColor White
Write-Host '       [System.Environment]::SetEnvironmentVariable("INFRA_AI_BACKEND","ollama","User")' -ForegroundColor DarkYellow
Write-Host '       [System.Environment]::SetEnvironmentVariable("INFRA_AI_MODEL","llama3.1:70b","User")' -ForegroundColor DarkYellow
Write-Host '       [System.Environment]::SetEnvironmentVariable("INFRA_AI_BASE_URL","http://localhost:11434","User")' -ForegroundColor DarkYellow
Write-Host "  4. Restart your terminal, then restart the prompt engine." -ForegroundColor White

Write-Host ""
Write-Host "────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "To start the prompt engine:" -ForegroundColor Cyan
Write-Host '  cd D:\Srujan\Claude\devops\infra-prompt-engine' -ForegroundColor White
Write-Host "  uvicorn prompt_engine.server:app --reload --port 8000" -ForegroundColor White

Write-Host ""
Write-Host "────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "To open the Chat UI:" -ForegroundColor Cyan
Write-Host "  Open chat_ui\index.html in your browser, or:" -ForegroundColor White
Write-Host "  python -m http.server 3000 --directory chat_ui" -ForegroundColor White
Write-Host "  Then visit http://localhost:3000" -ForegroundColor White
Write-Host ""
