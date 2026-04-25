# AXIOM — Personal AI Operating System

> **A packagable, buildable, free & open-source Personal AI Assistant that runs 100% locally.**
> Zero cloud. Zero subscription. Zero data leaves your machine.

**Version:** 0.1.0-draft
**Date:** 2026-04-06
**Author:** Sai Krishna Madavarapu
**License:** Apache 2.0
**Hardware Target:** Lenovo ThinkStation P620 + NVIDIA RTX 3090 (24GB) + 128GB DDR4

---

## Table of Contents

1. [Phase 1: Requirements](#phase-1-requirements)
2. [Phase 2: Design](#phase-2-design)
3. [Phase 3: Tasks](#phase-3-tasks)

---

# Phase 1: Requirements

## 1.1 Problem Statement

### What problem?
Every personal AI assistant today requires sending your most intimate data — emails, calendar, health records, financial documents, voice recordings, screen activity — to remote servers owned by corporations. You rent intelligence. You don't own it. When the subscription lapses, the API changes, or the company pivots, your assistant disappears and your data stays on their servers.

### Who has it?
Privacy-conscious professionals, developers, and power users who:
- Process sensitive documents (legal, medical, financial, proprietary code)
- Want an always-available AI that knows their full context across years
- Refuse to accept the cloud's terms: your data for their service
- Need an assistant that acts autonomously (books, schedules, monitors, codes) — not just chats

### Cost of inaction?
- **Privacy:** Every query to ChatGPT/Claude becomes training data or is stored on servers you don't control
- **Cost:** $20-200/month in subscriptions ($720-$7,200/3 years) vs $0/month after hardware
- **Dependency:** Cloud outages, rate limits, model deprecations, TOS changes — all outside your control
- **Capability ceiling:** Cloud assistants don't know your screen, your files, your routine. They start cold every session

### Why now?
Three convergences in Q1 2026 make this feasible for the first time:
1. **Models caught up:** Gemma 4 26B MoE runs at 100+ tok/s on RTX 3090 with frontier-class quality. Apache 2.0.
2. **Compression broke through:** TurboQuant (Google, ICLR 2026) delivers 6x KV cache compression with zero accuracy loss. Models that needed 48GB now fit in 24GB.
3. **Frameworks matured:** OpenJarvis (Stanford), AgentScope (Alibaba), and the MCP+A2A protocol stack provide production-grade agent orchestration that runs locally.

---

## 1.2 User Stories

### US-1: Morning Briefing
**As a** professional,
**I want** AXIOM to prepare a morning briefing while I sleep,
**So that** I start my day knowing exactly what needs attention without opening 5 apps.

**Acceptance Criteria:**
- GIVEN it is 7:00 AM and the user has not interacted since last night
- WHEN AXIOM's scheduled morning agent runs
- THEN a 1-paragraph briefing is ready covering: unread email count + flagged items, today's calendar with prep notes for meetings, overnight deploy/CI status (if configured), weather and commute estimate
- AND the briefing is available in Open WebUI chat, Telegram, and voice (on wake word)

### US-2: Voice Control — Smart Home
**As a** homeowner,
**I want** to control my smart home with voice using a wake word,
**So that** I get instant, private home control without Alexa/Google listening.

**Acceptance Criteria:**
- GIVEN AXIOM's voice pipeline is running and a Wyoming satellite device is active
- WHEN I say "Hey Axiom, turn on the porch lights"
- THEN the lights turn on within 1.5 seconds (wake word → STT → intent → HA action → TTS confirmation)
- AND no audio data leaves the local network
- AND safety-critical devices (locks, HVAC, garage) require double-confirmation

### US-3: Document Q&A (RAG)
**As a** knowledge worker,
**I want** to ask questions about my local documents and get cited answers,
**So that** I can find information in my files without manual searching.

**Acceptance Criteria:**
- GIVEN I have uploaded documents to AXIOM's knowledge base
- WHEN I ask "What was the payment term in the Acme contract?"
- THEN AXIOM returns the answer with source file name, page/section reference
- AND the answer is generated in under 5 seconds for documents already indexed
- AND no document content is sent to any external service

### US-4: Proactive Notifications
**As a** busy professional,
**I want** AXIOM to surface important items at natural workflow breaks,
**So that** I'm never interrupted mid-focus but never miss something important.

**Acceptance Criteria:**
- GIVEN AXIOM has queued low-priority notifications
- WHEN a workflow boundary is detected (calendar gap, 5+ minutes keyboard idle, meeting end)
- THEN queued items are surfaced in order of priority
- AND AXIOM never interrupts during active typing, video calls, or focus-mode calendar blocks
- AND each notification is actionable (reply, defer, dismiss) in one interaction

### US-5: Autonomous Web Tasks
**As a** user who hates repetitive web tasks,
**I want** AXIOM to browse the web and complete multi-step tasks for me,
**So that** I can say "Book a dentist appointment for next Thursday" and it happens.

**Acceptance Criteria:**
- GIVEN AXIOM has browser automation capability and saved credentials/preferences
- WHEN I request a multi-step web task
- THEN AXIOM plans the steps, executes via browser automation, and reports the result
- AND any action requiring payment or PII submission pauses for explicit user confirmation
- AND failed steps are retried once, then reported with screenshots for manual intervention

### US-6: Code Assistant
**As a** developer,
**I want** AXIOM to read my codebase, write code, run tests, and fix bugs,
**So that** I have a local Copilot-level coding assistant with full repo context.

**Acceptance Criteria:**
- GIVEN AXIOM has access to a project directory
- WHEN I ask "Fix the failing test in auth_service.py"
- THEN AXIOM reads the file, diagnoses the failure, proposes a fix, and optionally applies it
- AND code changes are shown as diffs before application
- AND AXIOM can run shell commands (tests, linters) with user-configured allow-lists

### US-7: Screen Awareness
**As a** power user,
**I want** AXIOM to see and understand what's on my screen,
**So that** I can ask "What was that error I saw 10 minutes ago?" and get an answer.

**Acceptance Criteria:**
- GIVEN ScreenPipe is running and capturing screen + audio
- WHEN I ask about something that appeared on screen
- THEN AXIOM queries the local ScreenPipe database and returns relevant frames/text
- AND screen data is stored only locally in SQLite, never transmitted
- AND capture can be paused/resumed per-app or globally via hotkey

### US-8: Persistent Memory Across Sessions
**As a** daily user,
**I want** AXIOM to remember our past conversations, my preferences, and my context,
**So that** I never have to re-explain myself or my setup.

**Acceptance Criteria:**
- GIVEN I told AXIOM my preferences in a previous session (e.g., "I prefer morning meetings before 10 AM")
- WHEN I start a new session days later
- THEN AXIOM recalls and applies those preferences without being reminded
- AND memory can be inspected, edited, and deleted by the user
- AND memory uses tiered storage: hot (current session) → warm (daily summaries) → cold (vector indexed) → frozen (archived)

### US-9: Self-Improving System
**As a** long-term user,
**I want** AXIOM to get better at my specific tasks over time,
**So that** after 6 months it handles my workflows better than any generic cloud AI.

**Acceptance Criteria:**
- GIVEN AXIOM has collected interaction traces over weeks of use
- WHEN I run `axiom optimize` or the scheduled optimization fires
- THEN AXIOM fine-tunes prompts (via DSPy) and optionally model weights (via Unsloth LoRA) on my interaction data
- AND a before/after evaluation is shown with clear metrics
- AND the user can roll back any optimization

### US-10: One-Command Install
**As a** self-hoster,
**I want** to install AXIOM with a single command,
**So that** I don't spend a weekend wiring Docker containers together.

**Acceptance Criteria:**
- GIVEN a fresh Ubuntu 24.04 machine with an NVIDIA GPU
- WHEN I run `curl -fsSL https://axiom.ai/install.sh | bash`
- THEN AXIOM installs all dependencies, pulls default models, and starts serving
- AND a guided setup wizard configures: profile (name, email, timezone), integrations (calendar, email, HA), voice (wake word, TTS voice), and security (Tailscale, backup location)
- AND the system is fully operational within 30 minutes (including model downloads)

---

## 1.3 Scope Boundaries

### In Scope (v0.1 — "First Light")
- [ ] Core agent loop: perceive → remember → reason → act
- [ ] Ollama inference backend with model router (fast/thinking/general)
- [ ] Text chat via Open WebUI
- [ ] Voice pipeline: OpenWakeWord → faster-whisper (CPU) → LLM → Kokoro/Piper TTS
- [ ] RAG over local documents (PDF, DOCX, TXT, MD) via ChromaDB
- [ ] Persistent memory (Mem0 or SQLite + vector embeddings)
- [ ] MCP tool servers: filesystem, clipboard, shell (sandboxed)
- [ ] Home Assistant integration (Wyoming protocol for voice satellites)
- [ ] Telegram bot for mobile access
- [ ] Docker Compose packaging with GPU profile selection
- [ ] Install script with guided setup wizard
- [ ] Nightly backup cron
- [ ] Ollama watchdog for memory leak mitigation
- [ ] Basic monitoring via Uptime Kuma

### In Scope (v0.2 — "Perception")
- [ ] ScreenPipe integration (screen + audio capture)
- [ ] Browser automation via Browser-Use
- [ ] Proactive notification system with workflow boundary detection
- [ ] Morning briefing agent (email + calendar + CI)
- [ ] Three.js holographic dashboard UI
- [ ] n8n workflow automation integration
- [ ] TurboQuant KV cache compression
- [ ] EAGLE-3 speculative decoding

### In Scope (v0.3 — "Learning")
- [ ] Interaction trace collection
- [ ] Prompt optimization via DSPy
- [ ] Model fine-tuning via Unsloth LoRA
- [ ] Graphiti temporal knowledge graph
- [ ] AG-UI protocol for real-time frontend events
- [ ] Tauri v2 desktop app packaging
- [ ] Runtipi/CasaOS app store manifests

### Out of Scope
- Cloud-hosted inference (by design principle)
- Mobile native app (PWA + Telegram covers mobile)
- Multi-user/team features (this is a personal assistant)
- Training models from scratch (fine-tuning only)
- Video generation / image generation (focus is on intelligence, not media)
- Windows/macOS host OS support in v0.x (Ubuntu-first; others via Docker)
- Commercial SaaS offering
- HIPAA/SOC2 compliance certification (though architecture supports it)

### Dependencies
| Dependency | Version | License | Risk |
|-----------|---------|---------|------|
| OpenJarvis | 0.x | Apache 2.0 | Stanford-maintained, active, well-funded |
| AgentScope | 1.x | Apache 2.0 | Alibaba-maintained, 23K stars |
| Ollama | 0.7+ | MIT | 95K stars, de facto standard |
| Open WebUI | 0.6.37+ | Custom (was BSD-3) | License changed Apr 2025; evaluate fork risk |
| Gemma 4 26B | - | Apache 2.0 | Google-released, unrestricted |
| Qwen 3.5 27B | - | Apache 2.0 | Alibaba-released, unrestricted |
| faster-whisper | - | MIT | Mature, stable |
| Kokoro-82M | - | Apache 2.0 | Small model, low maintenance risk |
| ScreenPipe | 0.x | MIT (core) | 17K stars, funded ($2.8M) |
| Browser-Use | 0.x | MIT | 81K stars, high adoption |
| Mem0 | 0.x | Apache 2.0 | 52K stars, active |
| Composio | 0.x | Open Source | 15K stars, 1000+ integrations |
| n8n | 1.80+ | Fair-code | Self-hosted is free; pin version |

### Assumptions
1. User has a dedicated Ubuntu 24.04 machine (not dual-purpose gaming rig)
2. NVIDIA GPU with 16GB+ VRAM (24GB optimal, 16GB minimum with smaller models)
3. Minimum 64GB system RAM (128GB recommended)
4. 500GB+ free NVMe storage for models
5. Local network with internet access for initial setup (offline after)
6. User is comfortable with terminal/SSH for initial setup

---

## 1.4 Non-Functional Requirements

### Performance

| Metric | Target | Measurement |
|--------|--------|-------------|
| Text generation (Gemma 4 26B MoE) | >80 tok/s | Ollama benchmark |
| Text generation (Qwen 3.5 27B) | >25 tok/s | Ollama benchmark |
| Voice round-trip (wake → response audio) | <3 seconds | End-to-end timer |
| Voice round-trip (simple HA command) | <1.5 seconds | End-to-end timer |
| RAG retrieval + generation | <5 seconds | Query-to-answer timer |
| Document indexing (100-page PDF) | <60 seconds | Ingestion timer |
| Model hot-swap (Gemma → Qwen) | <10 seconds | Ollama switch time |
| Cold boot to operational | <3 minutes | systemd service start |
| Memory retrieval (Mem0 lookup) | <500ms | API response time |

### Reliability

| Metric | Target |
|--------|--------|
| Uptime (with watchdog) | >99% monthly |
| Data durability (conversations, memory) | Zero loss (nightly backups + WAL mode) |
| Recovery from GPU crash | Automatic restart within 60 seconds |
| Recovery from power outage | Auto-boot + service start within 5 minutes |

### Security

| Requirement | Implementation |
|-------------|---------------|
| Network isolation | UFW deny all incoming; Tailscale for remote |
| API authentication | Caddy reverse proxy with basic auth in front of all services |
| Shell execution | Allow-list only; no arbitrary shell from LLM-triggered paths |
| Home automation safety | Device allow-list; destructive actions require confirmation |
| Data encryption at rest | LUKS full-disk encryption on Ubuntu install |
| Backup encryption | GPG-encrypted backup archives |
| Update security | Pin all Docker images; manual update with rollback plan |

### Observability

| Component | Tool |
|-----------|------|
| Service health | Uptime Kuma (HTTP checks every 60s) |
| GPU metrics | nvidia-smi + Prometheus nvidia_gpu_exporter |
| Container health | Docker healthchecks + restart policies |
| Application logs | Docker JSON logs + optional Loki |
| LLM performance | AgentScope Studio (token usage, latency, traces) |

### Resource Budget (24GB VRAM)

| Configuration | GPU VRAM | System RAM | CPU |
|--------------|----------|------------|-----|
| Gemma 4 26B MoE (primary) | 19.5 GB | ~4 GB | Minimal |
| Qwen3 8B (voice/fast) | 5.5 GB | ~2 GB | Minimal |
| faster-whisper turbo (CPU) | 0 GB | ~3 GB | 4 cores |
| Kokoro TTS (CPU) | 0 GB | ~1 GB | 2 cores |
| OpenWakeWord (CPU) | 0 GB | ~500 MB | 1 core |
| nomic-embed-text | ~500 MB | ~1 GB | Minimal |
| ChromaDB | 0 GB | ~1-2 GB | 1 core |
| Open WebUI | 0 GB | ~500 MB | 1 core |
| n8n + PostgreSQL | 0 GB | ~1 GB | 2 cores |
| Uptime Kuma | 0 GB | ~200 MB | Minimal |
| Docker overhead | 0 GB | ~2 GB | 2 cores |
| **TOTAL** | **~20 GB** | **~16 GB** | **~14 cores** |
| **Available** | **24 GB** | **128 GB** | **12-64 cores** |
| **Headroom** | **4 GB (KV cache)** | **112 GB** | **Plenty** |

---

# Phase 2: Design

## 2.1 Architecture Overview

AXIOM follows the **Perceive → Remember → Reason → Act** loop, inspired by OpenJarvis's 5-primitive architecture, adapted for single-machine deployment.

```
                         ┌─────────────────────────────┐
                         │        USER INTERFACES       │
                         │                              │
                         │  Open WebUI  │  Telegram Bot │
                         │  Voice (Wyoming)  │  CLI     │
                         │  Three.js Dashboard (v0.2)   │
                         └──────────┬──────────────────┘
                                    │ AG-UI / WebSocket / HTTP
                         ┌──────────▼──────────────────┐
                         │      AXIOM ORCHESTRATOR      │
                         │                              │
                         │  ┌─────────┐  ┌──────────┐  │
                         │  │ Router  │  │ Scheduler│  │
                         │  │ (model  │  │ (cron +  │  │
                         │  │  select)│  │  proactive│  │
                         │  └────┬────┘  └────┬─────┘  │
                         │       │             │        │
                         │  ┌────▼─────────────▼────┐  │
                         │  │    Agent Loop          │  │
                         │  │  ReAct / Plan-Execute  │  │
                         │  └────┬──────────────┬───┘  │
                         └───────┼──────────────┼──────┘
                    ┌────────────┼──────────────┼────────────┐
                    │            │              │            │
           ┌────────▼───┐ ┌─────▼──────┐ ┌────▼─────┐ ┌────▼─────┐
           │  PERCEIVE   │ │  REMEMBER   │ │  REASON  │ │   ACT    │
           │             │ │             │ │          │ │          │
           │ ScreenPipe  │ │ Mem0        │ │ Ollama   │ │ MCP Tools│
           │ Whisper STT │ │ ChromaDB    │ │          │ │ Browser  │
           │ Wake Word   │ │ Graphiti    │ │ Gemma 4  │ │ Shell    │
           │ MCP:Calendar│ │ SQLite      │ │ Qwen 3.5 │ │ Home Ast│
           │ MCP:Email   │ │             │ │ Qwen3 8B │ │ n8n      │
           │ MCP:Files   │ │ Hot/Warm/   │ │          │ │ Composio │
           │ Clipboard   │ │ Cold/Frozen │ │ +EAGLE-3 │ │ File I/O │
           └─────────────┘ └─────────────┘ │ +TurboQ  │ └──────────┘
                                           └──────────┘

           ┌─────────────────────────────────────────────┐
           │              LEARNING (v0.3)                 │
           │                                              │
           │  Trace Collector → DSPy Prompt Optimizer     │
           │                  → Unsloth LoRA Fine-tuner   │
           │                  → Agent Behavior Optimizer   │
           └─────────────────────────────────────────────┘

           ┌─────────────────────────────────────────────┐
           │              INFRASTRUCTURE                  │
           │                                              │
           │  Docker Compose │ Ollama (systemd)           │
           │  Caddy (reverse proxy + auth)                │
           │  Tailscale (remote access)                   │
           │  Uptime Kuma (monitoring)                    │
           │  Backup Cron (nightly encrypted)             │
           │  Watchdog (Ollama memory leak mitigation)    │
           └─────────────────────────────────────────────┘
```

---

## 2.2 Architecture Decision Records (ADRs)

### ADR-1: Agent Framework — OpenJarvis + AgentScope Hybrid

**Decision:** Use OpenJarvis as the core agent architecture (5-primitive model, self-improving traces, MCP+A2A) with AgentScope's distributed runtime for multi-agent orchestration.

**Why OpenJarvis:**
- 5-primitive architecture (Intelligence, Engine, Agents, Tools & Memory, Learning) maps exactly to AXIOM's needs
- Self-improving Learning primitive is unique — no other framework has closed-loop on-device optimization
- Stanford-maintained, Apache 2.0, sponsored by Google Cloud + Ollama + Lambda
- Native MCP + A2A protocol support
- Multi-backend inference (Ollama, vLLM, llama.cpp)
- Tauri v2 desktop app support built-in

**Why AgentScope for orchestration:**
- Only framework with proven distributed agent support (1M agents on 4 machines)
- Native gRPC + actor model for parallelism
- AgentScope Studio provides monitoring/debugging UI
- CoPaw (built on AgentScope) proves the personal assistant use case

**Rejected alternatives:**
| Alternative | Why Rejected |
|-------------|-------------|
| LangGraph alone | No self-improvement loop. No built-in voice. Steep learning curve. LangSmith monitoring is paid/cloud. |
| CrewAI alone | No distributed support. No learning primitive. Role-based model is too rigid for a personal assistant. |
| AutoGen / MS Agent Framework | AutoGen in maintenance mode. New MS Agent Framework is Azure-centric. |
| Build from scratch | 6+ months to reach feature parity with OpenJarvis. Not justified. |

---

### ADR-2: Primary Inference Runtime — Ollama (with ExLlamaV2 optional)

**Decision:** Ollama as the default runtime. ExLlamaV2 + TabbyAPI as an opt-in performance tier.

**Why Ollama:**
- Single binary install, systemd service, auto-restart
- Model library with `ollama pull` (trivial model management)
- OpenAI-compatible API at `/v1/` (universal client support)
- 95K GitHub stars = massive community, fast bug fixes
- Built-in tool/function calling support

**Why ExLlamaV2 as optional tier:**
- 20-40% faster than Ollama for pure GPU inference
- EXL2 format enables variable bits-per-weight within a single model
- TabbyAPI provides the same OpenAI-compatible API surface
- Worth it for users who want maximum performance and don't mind slightly more setup

**Rejected alternatives:**
| Alternative | Why Rejected |
|-------------|-------------|
| vLLM only | Overkill for single-user. Python-heavy. More complex setup. |
| llama.cpp server only | 26% faster than Ollama, but no model management, no pull ecosystem. |
| LocalAI | Less community, slower development pace. |
| TensorRT-LLM | NVIDIA-only, complex build process, consumer GPU support is secondary. |

---

### ADR-3: Model Selection — Gemma 4 MoE + Qwen 3.5 Dense + Qwen3 8B

**Decision:** Three-model strategy with intelligent routing.

| Role | Model | VRAM | Speed | Why |
|------|-------|------|-------|-----|
| **General / Default** | Gemma 4 26B MoE (Q4_K_M) | 19.5 GB | ~100 tok/s | 4B active params = MoE speed with 26B quality. Apache 2.0. Multimodal (text+image+audio). 262K context. |
| **Deep Thinking** | Qwen 3.5 27B Dense (Q4_K_M) | 16.7 GB | ~35 tok/s | Best reasoning quality in 24GB budget. Dense model catches what MoE misses on hard problems. |
| **Voice / Fast** | Qwen3 8B (Q4_K_M) | 5.5 GB | ~112 tok/s | Sub-second first-token for voice pipeline. 90K context. |
| **Coding** | Qwen3-Coder-Next (on-demand) | ~5 GB (3B active) | Fast | SWE-Bench Pro: 70.6. Swap in for code tasks. |
| **Embeddings** | nomic-embed-text | ~500 MB | Fast | Best local embedding model for RAG. |

**Router logic:**
```
IF voice_input AND simple_command → Qwen3 8B (speed)
ELIF coding_task → Qwen3-Coder-Next (specialization)
ELIF complex_reasoning OR multi_step → Qwen 3.5 27B (depth)
ELSE → Gemma 4 26B MoE (general quality + speed balance)
```

**Rejected alternatives:**
| Alternative | Why Rejected |
|-------------|-------------|
| Single model for everything | Voice needs <100ms TTFT (impossible with 27B dense). Complex reasoning needs dense attention (MoE drops quality on hard chains). |
| Llama 4 Scout (17B active) | Requires 33GB+ even with Unsloth 1.78-bit compression. Doesn't fit 24GB reliably. |
| 70B models via QuIP# 2-bit | Fits in VRAM but quality degrades significantly at 2-bit. 27B Q4 > 70B Q2 for most tasks. |

---

### ADR-4: Memory Architecture — Tiered (Hot/Warm/Cold/Frozen)

**Decision:** Four-tier memory system using Mem0 + SQLite + ChromaDB.

| Tier | Content | Storage | Size Budget | Access Time |
|------|---------|---------|-------------|-------------|
| **Hot** | Current conversation context | LLM context window | 4K tokens | 0ms |
| **Warm** | Today's events, recent summaries | SQLite + Mem0 | 8K tokens (summaries) | <100ms |
| **Cold** | All past conversations, documents | ChromaDB vectors | Unlimited | <500ms (retrieval) |
| **Frozen** | Archived projects, old conversations | Compressed SQLite | Unlimited | <2s (decompress + search) |

**Why this over a single vector DB:**
- Context window performance degrades past 32K tokens even in 262K-capable models
- Hot tier keeps active reasoning fast
- Warm tier gives "memory of today" without retrieving everything
- Cold tier provides infinite history via RAG
- Frozen tier prevents DB bloat from years of use

**Rejected alternatives:**
| Alternative | Why Rejected |
|-------------|-------------|
| Everything in context window | 262K tokens still degrades. KV cache consumes VRAM. |
| Only vector search | Loses temporal awareness. Can't distinguish "told me yesterday" from "told me 6 months ago." |
| Graphiti only | Knowledge graph is great for facts but poor for conversation flow. Use in v0.3 as supplement. |

---

### ADR-5: Voice Pipeline — CPU STT + GPU TTS (Hybrid)

**Decision:** Run faster-whisper (STT) on CPU. Run Kokoro (TTS) on CPU. Keep GPU exclusively for LLM.

**Why:**
- The RTX 3090's 24GB is fully committed to model weights + KV cache
- 128GB DDR4 at 100 GB/s bandwidth handles Whisper turbo on CPU adequately (~500ms-1.5s)
- Kokoro-82M is tiny and runs fast on CPU (<0.3s)
- Zero VRAM contention = zero OOM crashes during voice interaction

**Rejected alternatives:**
| Alternative | Why Rejected |
|-------------|-------------|
| Whisper on GPU | Steals 1-3GB VRAM. Causes OOM when model is loaded. |
| Cloud STT (Deepgram) | Violates zero-cloud principle. |
| Piper only | Lower quality than Kokoro. Fine as fallback for Raspberry Pi satellites. |

---

### ADR-6: Packaging — Docker Compose + Install Script (v0.1), Tauri Desktop (v0.3)

**Decision:** Ship as a Docker Compose stack with a bash install script for v0.1. Add Tauri v2 desktop app in v0.3.

**Why Docker Compose first:**
- Immediate value. Users can run `docker compose up -d` today.
- GPU passthrough via nvidia-container-toolkit is mature
- Each service is isolated and independently restartable
- Community-standard approach (n8n AI Starter Kit, local-ai-packaged)

**Why Tauri v2 for desktop (later):**
- 10-20x smaller than Electron (40MB vs 400MB+)
- Bundles Ollama as a sidecar process
- Cross-platform (macOS, Windows, Linux)
- OpenJarvis already has Tauri desktop support

**Rejected alternatives:**
| Alternative | Why Rejected |
|-------------|-------------|
| Electron desktop first | Too heavy. 400MB+ for a shell around a web UI. |
| Snap/Flatpak | GPU passthrough in sandboxed environments is unreliable. |
| Kubernetes/k3s | Overkill for single-machine personal assistant. |
| Bare metal (no Docker) | Dependency hell. Can't cleanly isolate or restart services. |

---

## 2.3 Data Model

### Core Entities

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Conversation   │────▶│     Message       │────▶│    Memory        │
│                  │     │                   │     │                  │
│ id (UUID)        │     │ id (UUID)         │     │ id (UUID)        │
│ title            │     │ conversation_id   │     │ content          │
│ created_at       │     │ role (user/asst)  │     │ embedding (vec)  │
│ updated_at       │     │ content           │     │ source_msg_id    │
│ summary          │     │ tool_calls[]      │     │ tier (hot/warm/  │
│ model_used       │     │ model_used        │     │   cold/frozen)   │
│ channel (web/    │     │ tokens_used       │     │ valid_from       │
│   tg/voice/cli)  │     │ latency_ms        │     │ valid_until      │
└─────────────────┘     │ created_at        │     │ created_at       │
                         └──────────────────┘     └─────────────────┘

┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Document       │────▶│     Chunk         │     │    Trace         │
│                  │     │                   │     │                  │
│ id (UUID)        │     │ id (UUID)         │     │ id (UUID)        │
│ file_path        │     │ document_id       │     │ conversation_id  │
│ file_type        │     │ content           │     │ agent_type       │
│ file_hash        │     │ embedding (vec)   │     │ input            │
│ indexed_at       │     │ page_number       │     │ output           │
│ chunk_count      │     │ section           │     │ model_used       │
│ total_tokens     │     │ metadata (JSON)   │     │ tools_called[]   │
└─────────────────┘     └──────────────────┘     │ memory_retrieved[]│
                                                  │ latency_ms       │
┌─────────────────┐     ┌──────────────────┐     │ success (bool)   │
│  ScheduledTask   │     │   Notification    │     │ user_feedback    │
│                  │     │                   │     │ created_at       │
│ id (UUID)        │     │ id (UUID)         │     └─────────────────┘
│ name             │     │ content           │
│ cron_expression  │     │ priority (1-5)    │
│ agent_type       │     │ source_agent      │
│ prompt           │     │ status (queued/   │
│ enabled (bool)   │     │   delivered/      │
│ last_run_at      │     │   dismissed)      │
│ next_run_at      │     │ delivered_at      │
│ last_result      │     │ created_at        │
└─────────────────┘     └──────────────────┘
```

### Storage

| Store | Engine | Purpose |
|-------|--------|---------|
| `axiom.db` | SQLite (WAL mode) | Conversations, messages, tasks, notifications, traces |
| `memory/` | Mem0 (backed by SQLite + ChromaDB) | Persistent user memory |
| `vectors/` | ChromaDB | Document chunks, cold-tier memory embeddings |
| `screenpipe/` | ScreenPipe SQLite | Screen captures, OCR text, audio transcripts |
| `config/` | YAML files | User profile, agent definitions, search config |
| `models/` | Ollama data dir | Downloaded model weights |

---

## 2.4 Component Architecture

### Directory Structure

```
axiom/
├── README.md
├── LICENSE                          # Apache 2.0
├── install.sh                       # One-command installer
├── docker-compose.yml               # Full stack definition
├── docker-compose.gpu.yml           # NVIDIA GPU override
├── .env.example                     # Environment template
│
├── axiom/                           # Core Python package
│   ├── __init__.py
│   ├── orchestrator.py              # Main agent loop + router
│   ├── router.py                    # Model selection logic
│   ├── scheduler.py                 # Cron + proactive task scheduler
│   │
│   ├── agents/                      # Agent definitions
│   │   ├── base.py                  # BaseAgent (ReAct loop)
│   │   ├── briefing.py              # Morning briefing agent
│   │   ├── code.py                  # Code assistant agent
│   │   ├── browser.py               # Web automation agent
│   │   ├── home.py                  # Home automation agent
│   │   └── research.py              # Deep research agent
│   │
│   ├── perception/                  # Input layer
│   │   ├── voice.py                 # Whisper STT + wake word
│   │   ├── screen.py                # ScreenPipe client
│   │   └── mcp_servers/             # MCP server definitions
│   │       ├── filesystem.py
│   │       ├── calendar.py
│   │       ├── email.py
│   │       └── clipboard.py
│   │
│   ├── memory/                      # Memory layer
│   │   ├── manager.py               # Tiered memory orchestrator
│   │   ├── hot.py                   # Context window management
│   │   ├── warm.py                  # Daily summaries (Mem0)
│   │   ├── cold.py                  # Vector retrieval (ChromaDB)
│   │   └── frozen.py                # Archive management
│   │
│   ├── action/                      # Output layer
│   │   ├── tool_registry.py         # MCP tool registration
│   │   ├── browser_use.py           # Browser automation wrapper
│   │   ├── shell.py                 # Sandboxed shell execution
│   │   ├── home_assistant.py        # HA REST API client
│   │   └── tts.py                   # Kokoro/Piper TTS
│   │
│   ├── learning/                    # Self-improvement (v0.3)
│   │   ├── traces.py                # Trace collector
│   │   ├── optimizer.py             # DSPy prompt optimization
│   │   └── finetune.py              # Unsloth LoRA training
│   │
│   └── infra/                       # Infrastructure
│       ├── watchdog.py              # Ollama health + VRAM monitor
│       ├── backup.py                # Encrypted backup manager
│       └── setup_wizard.py          # Guided first-run setup
│
├── config/
│   ├── profile.yaml.example         # User profile template
│   ├── agents.yaml                  # Agent role/goal definitions
│   ├── models.yaml                  # Model roster + routing rules
│   ├── tools.yaml                   # Allowed tools + permissions
│   └── security.yaml                # Allow-lists, rate limits
│
├── frontend/
│   ├── dashboard/                   # Three.js holographic UI (v0.2)
│   └── telegram/                    # Telegram bot integration
│
├── scripts/
│   ├── install.sh                   # Full installer
│   ├── ollama-watchdog.sh           # VRAM leak mitigation
│   ├── backup.sh                    # Nightly backup
│   └── optimize.sh                  # Learning trigger (v0.3)
│
├── deploy/
│   ├── docker/                      # Dockerfiles for each service
│   ├── systemd/                     # Service unit files
│   ├── caddy/                       # Caddyfile for reverse proxy
│   ├── runtipi/                     # Runtipi app manifest
│   └── casaos/                      # CasaOS app manifest
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── docs/
    ├── architecture.md
    ├── setup-guide.md
    ├── model-guide.md
    └── troubleshooting.md
```

---

## 2.5 API Contract

AXIOM exposes a unified REST + WebSocket API behind Caddy, fully OpenAI-compatible plus AXIOM-specific extensions.

### Core Endpoints

```
# OpenAI-compatible (proxied from Ollama)
POST   /v1/chat/completions          # Chat with model routing
POST   /v1/embeddings                # Generate embeddings
GET    /v1/models                    # List available models

# AXIOM Extensions
POST   /api/ask                      # Ask AXIOM (with memory + tools)
POST   /api/voice                    # Voice input (audio → response audio)
GET    /api/memory                   # List stored memories
DELETE /api/memory/:id               # Delete a memory
GET    /api/conversations            # List conversations
GET    /api/conversations/:id        # Get conversation history
POST   /api/documents                # Upload document for RAG
GET    /api/documents                # List indexed documents
POST   /api/tasks                    # Create scheduled task
GET    /api/tasks                    # List scheduled tasks
GET    /api/notifications            # Get queued notifications
POST   /api/notifications/:id/ack   # Acknowledge notification
GET    /api/health                   # System health check
GET    /api/metrics                  # GPU, RAM, service status
POST   /api/optimize                 # Trigger learning cycle (v0.3)

# WebSocket
WS     /ws/chat                      # Real-time streaming chat
WS     /ws/events                    # AG-UI event stream (v0.2)
```

---

## 2.6 Security Model

### Threat Model

| Threat | Mitigation |
|--------|-----------|
| LLM hallucinates destructive shell command | Shell tool uses strict allow-list. Commands not on list are rejected. |
| LLM hallucinates HA command (unlock door) | Safety-critical devices in `security.yaml` require user confirmation. |
| Prompt injection via web scraping | Browser-Use output is treated as untrusted data. LLM system prompt includes injection defense. |
| Network exposure of Ollama API | Ollama binds to 127.0.0.1 only. Caddy handles external auth. |
| Compromised Docker container | Containers run as non-root. No `--privileged`. Volumes are read-only where possible. |
| Data theft via physical access | LUKS full-disk encryption. Screen lock timeout. |
| Remote access compromise | Tailscale (WireGuard) only. No port 22 to internet. SSH keys only. |
| Memory/conversation data leak | All data on local disk. No telemetry. No external API calls except user-configured integrations. |

---

# Phase 3: Tasks

## 3.1 Task Decomposition — v0.1 "First Light"

### Sprint 1: Foundation (Week 1-2)

| # | Task | Depends On | Acceptance Test |
|---|------|-----------|-----------------|
| 1.1 | Create project scaffold (directory structure, pyproject.toml, Docker scaffolds) | None | `uv sync` succeeds. `pytest` finds test directory. |
| 1.2 | Write install.sh: NVIDIA driver check, Docker install, nvidia-container-toolkit, Ollama install | None | Fresh Ubuntu 24.04 VM: `bash install.sh` completes without error. `nvidia-smi` works in Docker. |
| 1.3 | Write docker-compose.yml with: Ollama, Open WebUI, PostgreSQL, Caddy, Uptime Kuma | 1.1 | `docker compose up -d` starts all services. `curl localhost:11434/api/tags` returns JSON. Open WebUI loads at :8080. |
| 1.4 | Write Ollama watchdog (health check + VRAM monitor + auto-restart) | 1.3 | Kill Ollama → watchdog restarts within 60s. Simulate VRAM leak → watchdog restarts when >23GB. |
| 1.5 | Write profile.yaml schema and setup wizard (interactive CLI) | 1.1 | `python -m axiom.infra.setup_wizard` walks through name, timezone, model selection, saves valid YAML. |
| 1.6 | Pull default models via Ollama (Gemma 4 26B, Qwen3 8B, nomic-embed-text) | 1.3 | `ollama list` shows all three models. `ollama run gemma4:26b "hello"` returns response. |

### Sprint 2: Core Agent Loop (Week 3-4)

| # | Task | Depends On | Acceptance Test |
|---|------|-----------|-----------------|
| 2.1 | Implement model router (fast/general/thinking selection logic) | 1.6 | Unit test: voice input → routes to 8B. Complex query → routes to 27B. Default → Gemma 4 MoE. |
| 2.2 | Implement BaseAgent with ReAct loop (reason → act → observe cycle) | 1.1 | Agent given "What is 2+2?" → returns "4" via Ollama. Agent given "List files in /tmp" → calls shell tool → returns listing. |
| 2.3 | Implement MCP tool registry + filesystem server | 2.2 | Agent can read/write files via MCP tool calls. |
| 2.4 | Implement sandboxed shell tool with allow-list | 2.2 | Allowed command (`ls`, `git status`) executes. Blocked command (`rm -rf /`) is rejected with error. |
| 2.5 | Implement Caddy reverse proxy with basic auth | 1.3 | Unauthenticated request to :8080 returns 401. Authenticated request passes through. |
| 2.6 | Integrate Open WebUI with Ollama + model router | 1.3, 2.1 | Chat in Open WebUI → model router selects appropriate model → response streams back. |

### Sprint 3: Memory + RAG (Week 5-6)

| # | Task | Depends On | Acceptance Test |
|---|------|-----------|-----------------|
| 3.1 | Implement Mem0 integration for persistent user memory | 2.2 | Tell AXIOM "I prefer dark mode". New session: ask "What do I prefer?" → "dark mode". |
| 3.2 | Implement tiered memory manager (hot/warm/cold/frozen) | 3.1 | Session context stays in hot tier. Day-old memories in warm. Week-old in cold. Month-old in frozen. |
| 3.3 | Implement ChromaDB document indexing (PDF, DOCX, TXT, MD) | 1.1 | Upload 100-page PDF → indexed within 60s. Query about content → returns answer with page citation. |
| 3.4 | Implement RAG pipeline: embed → retrieve → augment → generate | 3.3, 2.2 | "What does the contract say about payment terms?" → returns answer citing Acme_Contract.pdf page 4. |
| 3.5 | Implement memory inspection/deletion API | 3.1 | `GET /api/memory` lists all memories. `DELETE /api/memory/:id` removes one. Deleted memory no longer influences responses. |

### Sprint 4: Voice Pipeline (Week 7-8)

| # | Task | Depends On | Acceptance Test |
|---|------|-----------|-----------------|
| 4.1 | Integrate faster-whisper turbo (CPU mode) as STT service | 1.3 | Send audio file → returns transcription within 1.5s on CPU. |
| 4.2 | Integrate OpenWakeWord with "Hey Axiom" wake word | 4.1 | Say "Hey Axiom" near microphone → wake word detected → STT activates. |
| 4.3 | Integrate Kokoro-82M or Piper as TTS service | 1.3 | Send text → returns audio within 0.5s. Voice sounds natural. |
| 4.4 | Wire full voice pipeline: wake → STT → router → LLM → TTS → speaker | 4.1, 4.2, 4.3, 2.1 | Say "Hey Axiom, what time is it?" → spoken response within 3 seconds. |
| 4.5 | Integrate Wyoming Protocol for Home Assistant satellite devices | 4.4 | HA voice satellite sends audio → AXIOM processes → response plays on satellite. |

### Sprint 5: Channels + Automation (Week 9-10)

| # | Task | Depends On | Acceptance Test |
|---|------|-----------|-----------------|
| 5.1 | Implement Telegram bot integration | 2.2 | Send message to bot → AXIOM responds with full agent capabilities. |
| 5.2 | Implement Home Assistant integration (REST API + device control) | 2.2, 2.4 | "Turn on porch lights" → HA API called → lights turn on. "Unlock front door" → requires confirmation prompt. |
| 5.3 | Implement scheduled task system (cron-based agents) | 2.2 | Create daily 7AM briefing task → fires at 7AM → generates briefing → posts to Telegram. |
| 5.4 | Implement nightly backup system (encrypted, with rotation) | 1.3 | Run backup → GPG-encrypted tar of all Docker volumes + SQLite. 7-day rotation. Restore test passes. |
| 5.5 | Write comprehensive test suite (unit + integration) | All | `pytest` passes with >80% coverage on core modules. |
| 5.6 | Write documentation (setup guide, model guide, troubleshooting) | All | New user follows setup guide on fresh Ubuntu → AXIOM operational. |

---

## 3.2 Dependency Graph

```
Sprint 1 (Foundation)
  1.1 ──┬── 1.2 (parallel)
        ├── 1.3 ──── 1.4
        ├── 1.5      1.6
        │
Sprint 2 (Agent)
  1.6 ──── 2.1
  1.1 ──── 2.2 ──┬── 2.3
                  ├── 2.4
                  └── 2.6
  1.3 ──── 2.5

Sprint 3 (Memory)     Sprint 4 (Voice)        Sprint 5 (Channels)
  2.2 ── 3.1           1.3 ── 4.1              2.2 ── 5.1
  3.1 ── 3.2           4.1 ── 4.2              2.2 ── 5.2
  1.1 ── 3.3           1.3 ── 4.3              2.2 ── 5.3
  3.3 ── 3.4           4.x ── 4.4              1.3 ── 5.4
  3.1 ── 3.5           4.4 ── 4.5              All ── 5.5, 5.6
```

**Parallelizable:** Sprints 3 and 4 can run in parallel (Memory and Voice are independent subsystems).

---

## 3.3 Test Strategy

| Level | Coverage Target | Framework | What |
|-------|----------------|-----------|------|
| Unit | >80% of core modules | pytest | Router logic, memory tiering, tool allow-lists, agent ReAct loop |
| Integration | All service interactions | pytest + Docker | Ollama API calls, ChromaDB indexing, Mem0 persistence, HA API |
| E2E | Critical user flows | pytest + httpx | Full chat flow, voice pipeline, RAG query, scheduled task fire |
| Performance | All NFR targets | Custom benchmarks | tok/s, voice latency, RAG retrieval time, model swap time |
| Security | All threat model entries | Manual + automated | Shell injection attempts, HA safety device tests, auth bypass |

---

## 3.4 Rollback Plan

| Component | Rollback Strategy |
|-----------|-------------------|
| Ollama model update | `ollama run model:previous-tag` (old weights persist until deleted) |
| Open WebUI update | `docker compose pull open-webui && docker compose up -d` with pinned image tag |
| AXIOM code update | `git revert` or `git checkout v0.1.x` |
| Database migration | SQLite `.backup` before migration. Restore from nightly backup. |
| Docker Compose change | `git diff docker-compose.yml` before applying. Previous compose file in git history. |
| Learning optimization (v0.3) | Optimized prompts/weights stored as versioned files. `axiom rollback` restores previous version. |

---

## Appendix A: Optimization Stack Reference

| Technique | What It Does | AXIOM Version | Impact |
|-----------|-------------|---------------|--------|
| TurboQuant | 6x KV cache compression, zero accuracy loss | v0.2 | 4-8x longer context on same VRAM |
| EAGLE-3 | Speculative decoding, 2-3x speedup | v0.2 | Double effective tok/s |
| Unsloth Dynamic 2.0 | Per-layer adaptive quantization | v0.1 (model selection) | Best quality at any bit-width |
| Flash Attention 2 | Fused attention kernels | v0.1 (via Ollama/llama.cpp) | 2x attention speedup |
| GQA | Grouped query attention | v0.1 (model architecture) | Reduced KV cache by 8x |
| PowerInfer | GPU-CPU hybrid inference | v0.3 (experimental) | Run 70B+ models with CPU offload |
| Unsloth LoRA | Fine-tuning on consumer GPU | v0.3 | Personalize models to user |

## Appendix B: Cost Analysis

| Item | One-Time | Monthly | 3-Year Total |
|------|----------|---------|--------------|
| P620 + RTX 3090 (already owned) | $0 | - | $0 |
| Electricity (300W avg) | - | $25-37 | $900-1,332 |
| UPS (1500VA) | $250 | - | $250 |
| NVMe 2TB (if needed) | $150 | - | $150 |
| Cloud subscriptions | - | $0 | $0 |
| Software licenses | - | $0 | $0 |
| **TOTAL** | **$400** | **$25-37** | **$1,300-1,732** |

**vs. Cloud equivalent:** Claude Pro ($20) + ChatGPT Plus ($20) + Nabu Casa ($7.50) + ElevenLabs ($5) = $52.50/month = **$1,890 over 3 years** — and you still don't own your data.

---

*End of Specification — AXIOM v0.1 "First Light"*
