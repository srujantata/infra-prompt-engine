# DevOps AI Platform — Roadmap & Enhancement Vision

> Current state: Prompt → Terraform HCL → GitHub PR → EKS deployment + kubectl natural language admin
> Vision: Fully autonomous, self-healing, self-patching DevOps platform administered entirely through conversation

## Current Capabilities (v1.0 — Complete)

| Feature | Status | Details |
|---------|--------|---------|
| Prompt → Terraform → GitHub PR | ✅ Live | `POST /generate`, claude-sonnet-4-5 |
| kubectl natural language | ✅ Live | `POST /kubectl`, safety-gated execution |
| Conversational chat UI (PWA) | ✅ Live | PC/Mac/Mobile, works offline |
| Local AI (Ollama RTX 4090) | ✅ Live | codellama:34b, $0/month |
| EKS cluster + DevOps toolchain | ✅ Live | Jenkins, SonarQube, Harbor, ArgoCD |
| Active-passive DR blueprint | ✅ Documented | us-east-1 → us-west-2, RTO 30min |

---

## Phase 2 — Self-Healing Infrastructure (v2.0)

### 2.1 Autonomous Pod Repair Loop

A background loop (runs every 60s) that watches the cluster and auto-remediates common failures without human intervention.

**What it detects and fixes automatically:**

| Problem | Detection | Auto-Fix |
|---------|-----------|----------|
| CrashLoopBackOff | `kubectl get pods \| grep CrashLoop` | Restart pod, capture logs, AI diagnose root cause |
| OOMKilled | event reason=OOMKilled | Increase memory limit by 25%, patch deployment, alert |
| Pod stuck Pending | pending >5min | Check node capacity, trigger Karpenter scale-out |
| ImagePullBackOff | event reason=Failed | Verify Harbor connectivity, re-pull image |
| PVC stuck Pending | WaitForFirstConsumer >10min | Check EBS CSI, re-create StorageClass if needed |
| Node NotReady | `kubectl get nodes` | Cordon node, drain workloads, alert |
| Deployment rollout stuck | rollout status timeout | Auto-rollback to previous revision |

**Implementation:** New file `prompt_engine/self_heal.py` — extend the existing monitoring pattern from the crypto bot's autonomous loop. Runs as a background asyncio task inside the FastAPI server.

**New API endpoint:** `GET /heal/status` — returns last 50 remediation actions with timestamps.

### 2.2 AI-Powered Root Cause Analysis

When a pod fails, before restarting:
1. Capture `kubectl logs --previous` (last crash logs)
2. Capture `kubectl describe pod` (events, resource usage)
3. Feed both to Claude/Ollama with prompt: "Analyse these Kubernetes pod logs and events. Identify the root cause of the crash. Return JSON: {cause, severity, recommended_fix, auto_fixable}"
4. If `auto_fixable: true` → apply fix immediately
5. If `auto_fixable: false` → create GitHub Issue with full analysis + recommended steps

### 2.3 Terraform Drift Detection

Every 6 hours: run `terraform plan` against the live cluster. If drift detected:
1. AI analyses the diff: "Is this expected drift or configuration rot?"
2. If safe → auto `terraform apply`
3. If risky → open GitHub PR with explanation, block until merged

**New file:** `prompt_engine/drift_detect.py`

---

## Phase 3 — Self-Patching System (v2.1)

### 3.1 Automated Security Scanning + Auto-PR

**Container image CVE scanning** (Harbor Trivy already installed):
- Daily job: scan all deployed image tags for HIGH/CRITICAL CVEs
- If CVE found: AI checks if a patched image version exists in Harbor
- If patched version available: open GitHub PR updating the Helm `values.yaml` image tag
- PR body: CVE ID, severity, affected packages, patched version, CVSS score

**Implementation:** `prompt_engine/security_scan.py` — calls Harbor API + Trivy reports

### 3.2 Dependency Auto-Update (Renovate Bot)

Install Renovate Bot on all 5 GitHub repos:
- Auto-PRs for: Terraform module version bumps, Helm chart updates, Python package updates, GitHub Actions version bumps
- Config file: `renovate.json` in each repo
- AI reviews each Renovate PR: "Is this a breaking change? What's the migration effort?"
- Auto-merge if: patch update + all CI tests pass + AI rates risk as low

### 3.3 EKS Node OS Patching

Managed node group rolling update strategy:
1. AWS releases new EKS optimized AMI
2. Automation detects new AMI via AWS SSM Parameter Store
3. Creates Terraform PR: updates `ami_type` or launches new node group version
4. After merge: `kubectl drain` nodes one at a time, AWS replaces with patched AMI
5. Validates workloads healthy after each node replacement

---

## Phase 4 — Live Troubleshooter (v2.2)

### 4.1 k8sgpt Integration

Install [k8sgpt](https://k8sgpt.ai/) as a pod in the cluster:
```bash
helm repo add k8sgpt https://charts.k8sgpt.ai/
helm install k8sgpt k8sgpt/k8sgpt-operator -n k8sgpt --create-namespace \
  --set secret.name=k8sgpt-sample-secret \
  --set secret.anthropicApiKey=$ANTHROPIC_API_KEY
```

k8sgpt continuously analyses:
- Failing pods with AI explanations in plain English
- Resource pressure warnings
- RBAC misconfigurations
- Network policy issues
- Exposed secrets in pod specs

**Chat UI integration:** New sidebar widget shows k8sgpt live findings. Click any finding → chat box pre-populated with "Fix this: [finding]"

### 4.2 Prometheus + Grafana + AI Alerting

**Install stack:**
```bash
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  --set grafana.enabled=true \
  --set prometheus.prometheusSpec.retention=7d
```

**AI Alert Responder:** Prometheus fires alert → Alertmanager webhook → `/alerts` endpoint → AI analyses metric history + logs → generates remediation action → executes if safe (auto-scale, restart) or opens GitHub Issue if not

**New endpoint:** `POST /alerts` — receives Alertmanager webhook payload

### 4.3 Conversational Runbook Engine

Store runbooks as YAML in `dr-failover-runbook/runbooks/`:
```yaml
name: sonarqube-oom-recovery
trigger: OOMKilled in sonarqube namespace
steps:
  - kubectl rollout restart deployment/sonarqube -n sonarqube
  - kubectl wait --for=condition=ready pod -l app=sonarqube -n sonarqube --timeout=120s
  - curl -f $SONARQUBE_URL/api/system/health
```

When a trigger matches a runbook: AI runs the steps in sequence, reports each step's output in plain English in the chat UI. Fails gracefully and asks user if unexpected output occurs.

### 4.4 Slack / Teams Integration

New env var: `SLACK_WEBHOOK_URL`

Every auto-remediation action posts to Slack:
```
Auto-fixed: CrashLoopBackOff in jenkins/jenkins-0
   Root cause: Java heap exhausted (Xmx512m too low)
   Fix applied: memory limit 1Gi -> 2Gi, pod restarted
   Status: Running | View logs: [link]
```

---

## Phase 5 — Cost Intelligence (v2.3)

### 5.1 AI Cost Analyser

Daily job pulls AWS Cost Explorer API → feeds to Claude:
"Analyse this AWS cost breakdown. Identify the top 3 cost optimisation opportunities. Return specific Terraform changes that would reduce costs."

Returns actionable PRs: "Switch these 3 pods to Spot instances → saves $47/month"

### 5.2 Karpenter + Spot Optimisation

Upgrade from managed node groups to Karpenter for workload pods:
- Deploy workload pods on cheap Spot instances
- Auto-evict from Spot before termination, reschedule on On-Demand
- Right-sizing: Karpenter selects cheapest instance type that fits pod requests

### 5.3 Idle Resource Detector

Scans for:
- Deployments with 0 requests in last 24h → scale to 0 or delete
- Unused PVCs → alert + delete after 7-day grace period
- Orphaned Load Balancers (service deleted but LB still exists in AWS) → auto-delete
- Unused EBS volumes → alert

---

## Phase 6 — Multi-Cluster & Production Hardening (v3.0)

### 6.1 DR Activation via Prompt

Current DR is documented but manual. Make it prompt-driven:
- "activate DR failover" → runs Velero restore + updates Route53 + scales up us-west-2 cluster
- "test DR" → non-destructive failover test with traffic split 5% → us-west-2

### 6.2 Service Mesh (Istio)

- mTLS between all services (zero-trust networking)
- Traffic splitting for canary deployments: "deploy Jenkins 2.480 to 10% of traffic"
- Distributed tracing (Jaeger) auto-instrumented

### 6.3 Policy Engine (OPA Gatekeeper)

Enforce policies via prompts:
- "no container should run as root"
- "all images must come from harbor.internal"
- "pods must have resource limits set"

AI generates Rego policy → deploys as ConstraintTemplate

### 6.4 Chaos Engineering (Chaos Mesh)

- "test what happens if the sonarqube pod is killed" → runs chaos experiment → reports recovery time
- Automated game days: weekly random chaos in non-prod namespace

---

## Phase 7 — Mobile-First & Notifications (v3.1)

### 7.1 Push Notifications

When self-heal loop fixes something:
- Browser push notification (Web Push API — already PWA)
- Optional: Telegram bot for mobile alerts
- Optional: PagerDuty integration for on-call escalation

### 7.2 Voice Interface

Web Speech API (browser built-in, no external service):
- Microphone button in chat UI
- Speak: "scale Jenkins to 3 replicas" → transcribed → sent to `/chat`
- AI response read aloud via SpeechSynthesis API

### 7.3 Dashboard Mode

Full-screen cluster dashboard (alternative to chat view):
- Live pod grid: colour-coded by status (green/yellow/red)
- Node CPU/memory bars (from metrics-server)
- Recent auto-heal actions feed
- Cost-this-month meter
- One-click access to all tool UIs

---

## Implementation Priority

| Phase | Effort | Impact | Recommended Order |
|-------|--------|--------|------------------|
| 2.1 Self-healing loop | Medium | High — prevents 3am alerts | 1st |
| 4.1 k8sgpt | Low | High — install in 10 min | 2nd |
| 4.2 Prometheus + AI alerts | Medium | High | 3rd |
| 3.1 CVE scanning | Low | High — Harbor already has Trivy | 4th |
| 4.4 Slack notifications | Low | High | 5th |
| 5.1 Cost analyser | Low | Medium | 6th |
| 7.2 Voice interface | Low | Medium — browser built-in | 7th |
| 2.3 Terraform drift | Medium | Medium | 8th |
| 6.1 DR via prompt | High | High — production milestone | 9th |
| 6.2 Istio | High | Medium — production hardening | 10th |

---

## Architecture Evolution

```
v1.0 (Current)                    v2.0 (Self-healing)              v3.0 (Autonomous)
-----------------                 --------------------             ---------------------
User -> Chat UI                   Heal Loop (60s)                  AI Agent (continuous)
     -> /chat                          |                                |
     -> Claude/Ollama             Detect failure                   Monitor everything
     -> kubectl/terraform         AI diagnose                      Predict failures
     -> GitHub PR                 Auto-fix or PR                   Self-patch
                                  Slack notify                     Cost-optimise
                                                                   Zero human ops
```

---

## Contributing / Extending

Each phase is designed to be added as a new file in `prompt_engine/`:
- `self_heal.py` — Phase 2.1
- `drift_detect.py` — Phase 2.3
- `security_scan.py` — Phase 3.1
- `alert_responder.py` — Phase 4.2
- `cost_analyser.py` — Phase 5.1

All new modules follow the same pattern as `kubectl_exec.py`:
1. A `detect_*()` function that gathers data
2. An `analyse_with_ai()` function that calls Claude/Ollama
3. A `remediate()` function that applies the fix
4. A FastAPI endpoint registered in `server.py`
5. Tests in `tests/test_*.py`
