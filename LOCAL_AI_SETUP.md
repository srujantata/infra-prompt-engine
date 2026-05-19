# Local AI Deployment Guide — RTX 4090 + Ollama

> Deploy the full DevOps AI assistant stack on your local machine.
> Zero API cost after setup. All inference runs on your GPU.

## Hardware Requirements

| Component | Minimum | This Machine |
|-----------|---------|--------------|
| GPU | RTX 3090 (24GB VRAM) | RTX 4090 (24GB VRAM) ✅ |
| RAM | 32GB | 64GB ✅ |
| CPU | 8 cores | i9-13900K (24 cores) ✅ |
| Storage | 80GB free | — |
| OS | Windows 10/11, macOS 12+, Ubuntu 20+ | Windows 11 ✅ |

## Model Comparison

| Model | VRAM | Speed | Quality | Best for |
|-------|------|-------|---------|---------|
| llama3.1:70b | 40GB (too large for 4090 solo) | — | ⭐⭐⭐⭐⭐ | Use with CPU offload |
| llama3.1:8b | 8GB | ~80 tok/s | ⭐⭐⭐ | Fast responses |
| codellama:34b | 20GB | ~25 tok/s | ⭐⭐⭐⭐ | Code/Terraform/kubectl ✅ RECOMMENDED |
| deepseek-coder-v2:16b | 12GB | ~45 tok/s | ⭐⭐⭐⭐ | Code generation |
| mistral:7b | 6GB | ~90 tok/s | ⭐⭐⭐ | General chat |

**Recommendation for RTX 4090 (24GB VRAM):** `codellama:34b` — fits entirely in VRAM, excellent at Terraform HCL and kubectl, ~25 tokens/sec is fast enough for real-time chat.

For maximum quality: `llama3.1:70b` with `OLLAMA_NUM_GPU_LAYERS=40` (partial GPU offload — 24GB GPU + 64GB RAM).

---

## Step 1 — Install Ollama

### Windows
```powershell
winget install Ollama.Ollama
# Verify
ollama --version
```

### Mac
```bash
brew install ollama
```

### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

---

## Step 2 — Configure GPU Acceleration

### Windows — verify CUDA
```powershell
nvidia-smi
# Should show: CUDA Version 12.x, RTX 4090 24GB
```

Ollama auto-detects CUDA on Windows. No additional setup needed.

### Confirm GPU is being used
```powershell
# After starting a model, run in a separate terminal:
nvidia-smi dmon -s u
# GPU utilisation column should show >0 during inference
```

Expected output during active inference:
```
# gpu     sm    mem    enc    dec    jpg    ofa
    0     87     62      0      0      0      0
```

---

## Step 3 — Pull Models

Download sizes and estimated times on a 500 Mbps connection:

| Model | Download size | Estimated time |
|-------|--------------|----------------|
| codellama:34b | ~19 GB | ~5 min |
| llama3.1:8b | ~4.7 GB | ~1.5 min |
| deepseek-coder-v2:16b | ~9 GB | ~3 min |
| llama3.1:70b | ~40 GB | ~11 min |

```powershell
# Primary recommendation — fits in 24GB VRAM, best for Terraform+kubectl
ollama pull codellama:34b

# Fast fallback — 8GB VRAM, instant responses
ollama pull llama3.1:8b

# Optional — 70B quality with partial GPU offload (slow but best output)
$env:OLLAMA_NUM_GPU_LAYERS = "40"
ollama pull llama3.1:70b
```

Verify models are available:
```powershell
ollama list
# NAME                   ID              SIZE    MODIFIED
# codellama:34b          685be00e1532    19 GB   Just now
# llama3.1:8b            46e0c10c039e    4.7 GB  Just now
```

---

## Step 4 — Configure Environment Variables

```powershell
# Switch from Anthropic to Ollama — no code changes needed
[System.Environment]::SetEnvironmentVariable("INFRA_AI_BACKEND","ollama","User")
[System.Environment]::SetEnvironmentVariable("INFRA_AI_MODEL","codellama:34b","User")
[System.Environment]::SetEnvironmentVariable("INFRA_AI_BASE_URL","http://localhost:11434","User")

# Restart terminal after this
```

Or run the setup script:
```powershell
cd D:\Srujan\Claude\devops\infra-prompt-engine
.\setup_env.ps1
# Then edit INFRA_AI_BACKEND=ollama in your user environment variables
```

Verify the variables are set:
```powershell
[System.Environment]::GetEnvironmentVariable("INFRA_AI_BACKEND","User")
# Expected: ollama
[System.Environment]::GetEnvironmentVariable("INFRA_AI_MODEL","User")
# Expected: codellama:34b
```

---

## Step 5 — Start Ollama Server

```powershell
# Ollama runs as a background service on Windows after install
# Verify it's running:
curl http://localhost:11434/api/tags

# If not running:
ollama serve
```

Expected response from `/api/tags`:
```json
{
  "models": [
    {
      "name": "codellama:34b",
      "model": "codellama:34b",
      "modified_at": "2026-05-18T...",
      "size": 19068480000
    }
  ]
}
```

---

## Step 6 — Start the Prompt Engine

```powershell
cd D:\Srujan\Claude\devops\infra-prompt-engine
pip install -r requirements.txt
uvicorn prompt_engine.server:app --reload --port 8000
```

Expected startup output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx]
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## Step 7 — Open the Chat UI

```powershell
# Option A — double-click (no PWA features)
start chat_ui\index.html

# Option B — serve as PWA (recommended, enables mobile access)
python -m http.server 3000 --directory chat_ui
```

Open http://localhost:3000 in browser.

On mobile (same WiFi): `http://YOUR_PC_IP:3000` then tap "Add to Home Screen"

Find your PC's local IP:
```powershell
(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi").IPAddress
# Example: 192.168.1.42
```

On mobile:
- iPhone: tap Share → "Add to Home Screen" for app-like experience
- Android: Chrome menu → "Add to Home Screen" or "Install app"

---

## Step 8 — Test It Works

```powershell
# Test Ollama directly
curl -X POST http://localhost:11434/api/generate `
  -H "Content-Type: application/json" `
  -d '{"model":"codellama:34b","prompt":"Write a kubectl command to get all pods","stream":false}'

# Test via prompt engine API — translate (no execution)
curl -X POST http://localhost:8000/kubectl `
  -H "Content-Type: application/json" `
  -d '{"prompt":"show all pods not Running","execute":false}'

# Test Terraform generation
curl -X POST http://localhost:8000/generate/dry-run `
  -H "Content-Type: application/json" `
  -d '{"prompt":"Create an S3 bucket with versioning and encryption","environment":"dev"}'

# Health check
curl http://localhost:8000/health
```

Expected kubectl response:
```json
{
  "commands": ["kubectl get pods -A --field-selector=status.phase!=Running"],
  "explanation": "Lists all pods across all namespaces that are not in Running state.",
  "risk": "low",
  "warning": null,
  "results": null
}
```

---

## Switching Between Anthropic and Ollama

| Variable | Anthropic (cloud) | Ollama (local) |
|----------|------------------|----------------|
| `INFRA_AI_BACKEND` | `anthropic` | `ollama` |
| `INFRA_AI_MODEL` | `claude-sonnet-4-5` | `codellama:34b` |
| `INFRA_AI_BASE_URL` | `` (empty) | `http://localhost:11434` |
| Cost | ~$5–15/month | **$0** |
| Speed | ~50 tok/s (network) | ~25 tok/s (local) |
| Privacy | API calls leave machine | **Fully local** |

To switch back to Anthropic:
```powershell
[System.Environment]::SetEnvironmentVariable("INFRA_AI_BACKEND","anthropic","User")
[System.Environment]::SetEnvironmentVariable("INFRA_AI_MODEL","claude-sonnet-4-5","User")
[System.Environment]::SetEnvironmentVariable("INFRA_AI_BASE_URL","","User")
# Restart terminal, then restart uvicorn
```

---

## Autostart on Windows Boot

```powershell
# Ollama already autoinstalls as a Windows service
# To also autostart the prompt engine at login:
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NonInteractive -Command `"cd D:\Srujan\Claude\devops\infra-prompt-engine; uvicorn prompt_engine.server:app --port 8000`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "InfraPromptEngine" -Action $action -Trigger $trigger -RunLevel Highest

# Verify task was registered:
Get-ScheduledTask -TaskName "InfraPromptEngine"
```

To remove the scheduled task later:
```powershell
Unregister-ScheduledTask -TaskName "InfraPromptEngine" -Confirm:$false
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `CUDA out of memory` | Model too large for 24GB VRAM | Use `codellama:34b` (20GB) or `llama3.1:8b` (8GB) |
| `connection refused localhost:11434` | Ollama not running | Run `ollama serve` |
| Slow responses (>5s/token) | Model running on CPU | Verify `nvidia-smi dmon -s u` shows GPU usage during inference |
| `model not found` | Model not pulled | Run `ollama pull codellama:34b` |
| Chat UI shows red dot | Prompt engine server not running | Run `uvicorn prompt_engine.server:app --port 8000` |
| `INFRA_AI_BACKEND not set` | Env var not reloaded | Restart terminal after `SetEnvironmentVariable` |
| `ollama: command not found` | Ollama not in PATH | Open new terminal after `winget install Ollama.Ollama` |
| Ollama returns garbled JSON | Model context length exceeded | Shorten your prompt or switch to `llama3.1:8b` |

---

## Cost Comparison: 1 Month of Usage

| Scenario | Anthropic API | Ollama Local |
|----------|--------------|-------------|
| 100 chat messages/day | ~$8/month | $0 |
| 500 chat messages/day | ~$35/month | $0 |
| CI/CD automation (heavy) | ~$80/month | $0 |
| **Electricity (RTX 4090, 350W, 2h/day)** | — | ~$2/month |
| **Net saving** | — | **$6–78/month** |

Electricity calculation: 0.35 kW × 2h × 30 days × $0.10/kWh = ~$2.10/month

---

## Advanced: Partial GPU Offload for llama3.1:70b

The 70B model requires ~40GB VRAM total. With an RTX 4090 (24GB) and 64GB RAM, load 40 layers onto the GPU and the rest onto CPU RAM:

```powershell
# Set before starting Ollama (affects all subsequent model loads)
$env:OLLAMA_NUM_GPU_LAYERS = "40"
ollama serve

# In a new terminal:
ollama run llama3.1:70b
```

Performance with partial offload (RTX 4090 + i9-13900K):
- ~8–12 tokens/sec (slower than codellama:34b but significantly higher quality)
- Best for complex Terraform modules or multi-file refactoring tasks

For everyday kubectl and infra questions, `codellama:34b` full-GPU is the better choice.
