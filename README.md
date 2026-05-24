# Compliance Monitoring System — Project 1B

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.1+-121212?style=for-the-badge&logo=chainlink&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-0.2+-1C3C3C?style=for-the-badge&logo=chainlink&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=for-the-badge&logo=openai&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Store-FF6B35?style=for-the-badge)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

**A production-grade multi-agent AI system for regulatory compliance monitoring at a Tier-2 global bank.**

</div>

---

## Overview

The **Compliance Monitoring System** is an end-to-end AI pipeline built with **LangGraph** that orchestrates four specialised AI agents to monitor regulatory compliance across trading operations, lending activities, and customer communications. The system is designed to meet the standards of real-world enforcement actions from **SEC**, **FCA**, **FINRA**, and **OFAC**.

This is not a demo — it is architected to handle production concerns: strict schema validation, deterministic rule checks before LLM calls, audit-grade tracing via LangSmith, and a Human-in-the-Loop (HITL) escalation path for high-severity cases.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Orchestrator                      │
│                                                             │
│   ┌──────────────────────┐                                  │
│   │  Agent 1             │  ← Queries ChromaDB (RAG)        │
│   │  Regulatory Tracker  │  ← Fetches SEC/FCA/FINRA/OFAC   │
│   └──────────┬───────────┘    rules relevant to current data│
│              │ active_rules injected into state             │
│              ▼                                              │
│   ┌──────────────────────┐                                  │
│   │  Agent 2             │  ← Deterministic threshold checks│
│   │  Transaction Monitor │  ← LLM wash-trade / AML analysis│
│   └──────────┬───────────┘                                  │
│              │ alerts appended to state                     │
│              ▼                                              │
│   ┌──────────────────────┐                                  │
│   │  Agent 3             │  ← Keyword NLP (25+ patterns)    │
│   │  Communication Scanner│ ← LLM insider trading / comms  │
│   └──────────┬───────────┘                                  │
│              │ alerts appended to state                     │
│              ▼                                              │
│   ┌──────────────────────┐                                  │
│   │  Conflict Resolution │  ← Severity ranking & merging   │
│   └──────────┬───────────┘                                  │
│         ┌────┴─────────────────┐                            │
│         ▼                     ▼                             │
│  ┌─────────────┐    ┌──────────────────┐                   │
│  │    HITL     │    │  Agent 4         │                   │
│  │  Escalation │───►│  Report Generator│──► Markdown/PDF   │
│  └─────────────┘    └──────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| **LangGraph** for orchestration | Provides stateful, interruptible graph execution — essential for HITL |
| **ChromaDB** for RAG | Runs entirely locally — zero cloud provisioning for regulation retrieval |
| **Hybrid Detection** | Deterministic rules first (fast, cheap) → LLM only for complex behavioural patterns (expensive) |
| **`operator.add` on state** | Allows agents to safely append alerts in parallel without overwriting each other |
| **`.with_structured_output(Alert)`** | Forces LLM to return validated Pydantic objects — prevents malformed JSON crashes |
| **Streamlit** for HITL Dashboard | Pure Python compliance officer UI that hooks directly into LangGraph's `interrupt()` nodes |

---

## The Four Agents

### Agent 1 — Regulatory Update Tracker
- **Purpose**: RAG engine that fetches jurisdiction-specific rules before any analysis begins
- **Tech**: ChromaDB + `MarkdownHeaderTextSplitter` + OpenAI Embeddings
- **Output**: Injects `active_rules` list into the shared `ComplianceState`
- **Coverage**: SEC, FCA, FINRA, OFAC

### Agent 2 — Transaction Monitor
- **Purpose**: Analyses trades and loan applications for financial crime patterns
- **Tech**: LangChain + GPT-4o with `.with_structured_output()`
- **Detects**:
  - Wash trading (same trader buy/sell within seconds)
  - Structuring (transactions just below $10,000 BSA reporting threshold)
  - Suspicious loan approvals (high amount + low FICO + already approved)
  - Sanctions evasion patterns

### Agent 3 — Communication Scanner
- **Purpose**: Scans emails, chats, and off-channel messages for compliance breaches
- **Tech**: Keyword NLP + GPT-4o (future: Claude 3.5 Sonnet for nuanced transcript analysis)
- **Detects**:
  - Off-channel communication (`"use WhatsApp"`, `"text me instead"`)
  - Unauthorized guarantees (`"I can guarantee a 15% return"`)
  - Insider trading hints (`"they are acquiring TechCorp next week"`)
  - High-pressure sales tactics (`"sign today or lose everything"`)

### Agent 4 — Report Generator *(Day 7)*
- **Purpose**: Synthesis engine that compiles all alerts into an audit-grade compliance report
- **Output**: Structured Markdown / PDF report with rule citations for compliance officers

---

## Project Structure

```
Project1B-ComplianceMonitoringSystem/
│
├── agent/                         # The four AI agents
│   ├── __init__.py
│   ├── regulatory_tracker.py      # Agent 1: RAG-based rule fetcher
│   ├── transaction_monitor.py     # Agent 2: Trade & loan anomaly detector
│   ├── communication_scanner.py   # Agent 3: Email/chat NLP scanner
│   └── llm_wrapper.py             # Reusable LLM wrapper with retry logic
│
├── core/                          # Orchestration & shared schemas
│   ├── __init__.py
│   ├── state.py                   # ComplianceState TypedDict (LangGraph state)
│   ├── models.py                  # Pydantic models: Alert, TradeTransaction, etc.
│   └── orchestrator.py            # LangGraph graph builder & topology
│
├── data/
│   ├── mock/                      # Generated synthetic bank data
│   │   ├── trades.json            # 52 mock trades incl. wash trading scenario
│   │   ├── loans.json             # 21 mock loans incl. AML red flag
│   │   └── communications.json    # 34 mock comms incl. insider trading hints
│   └── regulations/
│       └── mock_regulations.md    # Mock SEC/FINRA/OFAC/FCA rule documents
│
├── scripts/
│   ├── __init__.py
│   ├── generate_mock_data.py      # Generates all synthetic datasets
│   └── ingest_regulations.py      # Embeds regulation docs into ChromaDB
│
├── .env.example                   # Template for all required API keys
├── .gitignore                     # Excludes .env, chroma_db/, __pycache__/
├── requirements.txt               # All Python dependencies
└── README.md                      # This file
```

---

## Quickstart

### Prerequisites
- Python 3.11+
- An OpenAI API key (for embeddings and GPT-4o analysis)
- A LangSmith API key (for audit-grade observability — optional but recommended)

### 1. Clone & Install

```bash
git clone https://github.com/Paragiscool/Compliance-Monitoring-System.git
cd Compliance-Monitoring-System
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and fill in your actual API keys
```

Required keys in `.env`:
```
OPENAI_API_KEY=sk-...
LANGCHAIN_API_KEY=ls-...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=Compliance_Monitoring_System_Project1B
```

### 3. Generate Mock Data

```bash
python scripts/generate_mock_data.py
```

This creates synthetic trades, loans, and communications in `data/mock/` with injected compliance violations.

### 4. Ingest Regulations into ChromaDB

```bash
python -m scripts.ingest_regulations
```

This embeds the regulatory documents into a local ChromaDB vector store so the Regulatory Tracker can perform RAG retrieval.

### 5. Run the Orchestrator

```bash
python -m core.orchestrator
```

This runs a smoke test that flows a suspicious trade + communication through all four agents and prints the resulting compliance report.

---

## Development Roadmap

| Phase | Days | Status | Focus |
|---|---|---|---|
| **Phase 1** | Days 1–3 | ✅ Complete | State schema, mock data, LangGraph core topology |
| **Phase 2** | Days 4–8 | 🔄 In Progress | Agent engineering (1–3 done, Report Generator next) |
| **Phase 3** | Days 9–11 | 📋 Planned | Inter-agent protocols, conflict resolution, HITL |
| **Phase 4** | Days 12–14 | 📋 Planned | 20 real-world validation scenarios (SEC/FCA/FINRA/OFAC) |
| **Phase 5** | Day 15 | 📋 Planned | Audit review, LangSmith observability, documentation |

### Validation Scenarios (Phase 4)
The system will be validated against 20 synthetic datasets mirroring real enforcement actions:

- **SEC**: Off-channel communications fines (WhatsApp, Signal)
- **FINRA**: Churning and unsuitable lending recommendations
- **OFAC**: Sanctions evasion via obscured wire transfers and shell companies
- **FCA**: Market abuse and spoofing scenarios

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Orchestration** | LangGraph, LangChain |
| **Primary LLM** | OpenAI GPT-4o |
| **Comms LLM** *(planned)* | Anthropic Claude 3.5 Sonnet |
| **Embeddings** | OpenAI `text-embedding-ada-002` |
| **Vector Store** | ChromaDB (local) |
| **Schema Validation** | Pydantic v2 |
| **Observability** | LangSmith |
| **HITL Dashboard** | Streamlit *(Day 11)* |
| **Language** | Python 3.11+ |

---

## Contributing

This project is under active development as part of a 15-day sprint. Each day's work is tracked in the implementation plan. Issues and PRs are welcome.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
Built as <strong>Project 1B</strong> — Production-Grade Multi-Agent AI Compliance System
</div>
