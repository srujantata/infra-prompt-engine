# DevOps Platform Chat UI

A single-file Progressive Web App (PWA) for interacting with the infra-prompt-engine conversational API.

## Open in browser

**Simplest** — just open the file:

```
chat_ui/index.html
```

Double-click it in Explorer / Finder, or drag it to your browser.
On first load a modal will ask for your server URL (default: `http://localhost:8000`).

## Serve locally (required for PWA "Add to Home Screen")

```bash
# Python (built-in, no install needed)
python -m http.server 3000 --directory chat_ui

# Then open: http://localhost:3000
```

On macOS/Linux, or WSL:
```bash
python3 -m http.server 3000 --directory chat_ui
```

## Access from phone (same WiFi)

1. Start the prompt engine on your PC:
   ```
   uvicorn prompt_engine.server:app --host 0.0.0.0 --port 8000
   ```
2. Find your PC's local IP (Windows: `ipconfig`, Mac/Linux: `ifconfig | grep 192`).
3. Serve the UI:
   ```
   python -m http.server 3000 --directory chat_ui --bind 0.0.0.0
   ```
4. On your phone: open `http://<your-pc-ip>:3000`
5. Set server URL to `http://<your-pc-ip>:8000` in the Connect modal.
6. On iPhone: tap Share → "Add to Home Screen" for app-like experience.
   On Android: Chrome menu → "Add to Home Screen" or "Install app".

## Features

- Dark theme (GitHub dark)
- Left sidebar: cluster health stats, quick links to ArgoCD/Jenkins/SonarQube/Harbor
- Chat bubbles: user (right), AI (left)
- Code blocks with monospace font; kubectl commands highlighted with green left border
- Collapsible execution results under each command
- Execute toggle: off by default (safe — translate only), ON sends `execute: true`
- Red warning banner when Execute mode is ON
- Enter to send, Shift+Enter for newline
- Auto-fetches cluster status on load to populate the sidebar
- Starter prompt chips on first open
- Server URL stored in localStorage — survives page refreshes

## Switching to Ollama (free, local)

```powershell
# Windows PowerShell
[System.Environment]::SetEnvironmentVariable("INFRA_AI_BACKEND","ollama","User")
[System.Environment]::SetEnvironmentVariable("INFRA_AI_MODEL","llama3.1:70b","User")
[System.Environment]::SetEnvironmentVariable("INFRA_AI_BASE_URL","http://localhost:11434","User")
# Restart terminal, then restart the uvicorn server
```

```bash
# Mac/Linux
export INFRA_AI_BACKEND=ollama
export INFRA_AI_MODEL=llama3.1:70b
export INFRA_AI_BASE_URL=http://localhost:11434
# Restart the uvicorn server
```
