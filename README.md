# 🛡️ Enterprise AI Compliance Monitoring System

<p align="center">
  <img src="https://img.shields.io/badge/LangGraph-0.2.28-blue?style=for-the-badge&logo=langchain" />
  <img src="https://img.shields.io/badge/LLM-Gemini_3.1_Flash--Lite-orange?style=for-the-badge&logo=google" />
  <img src="https://img.shields.io/badge/Embeddings-Gemini_Embedding_2-yellow?style=for-the-badge&logo=google" />
  <img src="https://img.shields.io/badge/VectorDB-ChromaDB_0.5-green?style=for-the-badge" />
  <img src="https://img.shields.io/badge/UI-Streamlit_1.35-red?style=for-the-badge&logo=streamlit" />
  <img src="https://img.shields.io/badge/CI/CD-GitHub_Actions-black?style=for-the-badge&logo=github" />
  <img src="https://img.shields.io/badge/Container-Docker-2496ED?style=for-the-badge&logo=docker" />
  <img src="https://img.shields.io/badge/Resilience-Tenacity-purple?style=for-the-badge" />
</p>

An autonomous, **multi-agent surveillance architecture** designed to detect complex financial crimes — including **Insider Trading**, **Wash Trading**, **BSA/AML Structuring**, **Spoofing**, and **Sanctions Evasion** — across high-frequency transaction ledgers and off-channel employee communications.

This system moves beyond legacy deterministic rules engines by utilizing **LangGraph stateful orchestration**, **ReAct tool-calling**, **semantic correlation**, **RAG-powered regulatory retrieval**, and an **adaptive Human-in-the-Loop (HITL) feedback loop** with persistent ChromaDB learning.

---

## Table of Contents

- [System Architecture Overview](#-system-architecture-overview)
- [LangGraph Deep Dive](#-langgraph-deep-dive)
  - [What is LangGraph?](#what-is-langgraph)
  - [Graph Topology](#graph-topology)
  - [ComplianceState Schema](#compliancestate-schema)
  - [State Reducers & Accumulation](#state-reducers--accumulation)
  - [Conditional Routing](#conditional-routing)
  - [Interrupt & Resume (HITL)](#interrupt--resume-hitl)
- [Agent Architecture](#-agent-architecture)
  - [Agent 1: Regulatory Tracker (RAG)](#agent-1-regulatory-tracker-rag)
  - [Agent 2: Transaction Monitor](#agent-2-transaction-monitor)
  - [Agent 3: Communication Scanner (ReAct)](#agent-3-communication-scanner-react)
  - [Agent 4: Correlation Engine (Semantic)](#agent-4-correlation-engine-semantic)
  - [Agent 5: Report Generator](#agent-5-report-generator)
- [Resilience Engineering](#-resilience-engineering)
  - [Tenacity Retry Architecture](#tenacity-retry-architecture)
  - [Local Embedding Fallback (Adapter Pattern)](#local-embedding-fallback-adapter-pattern)
  - [Embedding Call Flow](#embedding-call-flow)
- [Persistent State & Memory](#-persistent-state--memory)
- [Adaptive Learning Loop](#-adaptive-learning-loop)
- [CI/CD Pipeline & Deployment](#-cicd-pipeline--deployment)
  - [Docker Architecture](#docker-architecture)
  - [GitHub Actions Pipeline](#github-actions-pipeline)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Performance Metrics](#-performance-metrics)
- [Troubleshooting](#-troubleshooting)

---

## 🏗️ System Architecture Overview

The full end-to-end pipeline — from raw data ingestion through autonomous multi-agent analysis to human-reviewed audit reports:

```mermaid
graph TB
    subgraph INPUT["📥 Data Ingestion Layer"]
        TX[("🏦 Transaction Ledger<br/>(mock_transactions.json)")]
        COMM[("💬 Communication Feeds<br/>(mock_communications.json)")]
        REG[("📜 Regulatory Corpus<br/>(mock_regulations.md)")]
    end

    subgraph VECTOR["🧠 Vector Store Layer"]
        CHROMA_REG[("ChromaDB<br/>Regulatory Rules")]
        CHROMA_FP[("ChromaDB<br/>False Positives")]
    end

    subgraph LANGGRAPH["⚙️ LangGraph Orchestrator"]
        direction TB
        A1["🔍 Agent 1: Regulatory Tracker<br/>(RAG Retrieval)"]
        A2["📊 Agent 2: Transaction Monitor<br/>(Deterministic + LLM)"]
        A3["🔎 Agent 3: Communication Scanner<br/>(ReAct Tool-Calling)"]
        A4["🔗 Agent 4: Correlation Engine<br/>(Semantic Fusion)"]
        ROUTER{"🔀 Conditional Router<br/>escalation_status?"}
        HITL["⏸️ HITL Interrupt<br/>(interrupt_before)"]
        A5["📝 Agent 5: Report Generator<br/>(LLM Synthesis)"]
    end

    subgraph PERSIST["💾 Persistence Layer"]
        SQLITE[("SQLite<br/>Checkpoints & State")]
    end

    subgraph UI["🖥️ Streamlit Dashboard"]
        DASH["Compliance Officer UI"]
        APPROVE["✅ Approve"]
        REJECT["❌ Reject & Teach"]
    end

    REG -->|"ingest_regulations.py"| CHROMA_REG
    TX --> A1
    COMM --> A1
    CHROMA_REG -->|"Similarity Search"| A1
    A1 -->|"active_rules"| A2
    A2 -->|"alerts (append)"| A3
    CHROMA_FP -.->|"Negative Constraints"| A2
    CHROMA_FP -.->|"Negative Constraints"| A3
    A3 -->|"alerts (append)"| A4
    A4 --> ROUTER
    ROUTER -->|"ESCALATED / PENDING_REVIEW"| HITL
    ROUTER -->|"NONE"| A5
    HITL -->|"interrupt_before"| SQLITE
    SQLITE --> DASH
    DASH --> APPROVE
    DASH --> REJECT
    APPROVE -->|"Resume Graph"| A5
    REJECT -->|"Embed Feedback"| CHROMA_FP
    REJECT -->|"Resume Graph"| A5
    A5 -->|"report_content"| SQLITE
    HITL --> A5

    style INPUT fill:#1a1a2e,stroke:#16213e,color:#e0e0e0
    style VECTOR fill:#0f3460,stroke:#533483,color:#e0e0e0
    style LANGGRAPH fill:#162447,stroke:#1f4068,color:#e0e0e0
    style PERSIST fill:#1b1b2f,stroke:#1a1a2e,color:#e0e0e0
    style UI fill:#1e3163,stroke:#0f3460,color:#e0e0e0
```

---

## 🧬 LangGraph Deep Dive

### What is LangGraph?

**LangGraph** is a framework for building **stateful, multi-step AI agent workflows** as directed graphs. Unlike simple LLM chains, LangGraph provides:

| Feature | Chain (LangChain) | Graph (LangGraph) |
|---|---|---|
| Execution model | Linear pipeline | Directed graph with cycles |
| State management | Ephemeral | Persistent (`TypedDict` + checkpointer) |
| Branching | Manual `if/else` | `add_conditional_edges()` |
| Human oversight | External wrapper | Native `interrupt_before` / `interrupt_after` |
| Resumability | ❌ Not built-in | ✅ Resume from any checkpoint |
| Concurrency | ❌ Sequential only | ✅ Fan-out/fan-in support |

In this project, LangGraph serves as the **central nervous system** — orchestrating 5 specialized agents, managing shared mutable state, routing based on risk severity, and pausing execution for human review.

### Graph Topology

The compiled graph is a **sequential pipeline with a conditional branch**. Here is the exact topology as defined in `core/orchestrator.py`:

```mermaid
graph TD
    START(("▶️ START")):::startEnd

    RT["🔍 regulatory_tracker<br/><i>RAG retrieval from ChromaDB</i>"]:::agent
    TM["📊 transaction_monitor<br/><i>Deterministic + LLM analysis</i>"]:::agent
    CS["🔎 communication_scanner<br/><i>ReAct tool-calling agent</i>"]:::agent
    CR["🔗 conflict_resolution<br/><i>Semantic correlation engine</i>"]:::agent
    HITL["⏸️ hitl_placeholder<br/><i>Human review node</i>"]:::hitl
    RG["📝 report_generator<br/><i>LLM audit synthesis</i>"]:::agent

    END_NODE(("⏹️ END")):::startEnd

    START --> RT
    RT -->|"add_edge"| TM
    TM -->|"add_edge"| CS
    CS -->|"add_edge"| CR

    CR -->|"ESCALATED /<br/>PENDING_REVIEW"| HITL
    CR -->|"NONE"| RG

    HITL -->|"add_edge"| RG
    RG -->|"add_edge"| END_NODE

    classDef startEnd fill:#e74c3c,stroke:#c0392b,color:#fff,stroke-width:2px
    classDef agent fill:#2c3e50,stroke:#3498db,color:#ecf0f1,stroke-width:2px
    classDef hitl fill:#8e44ad,stroke:#9b59b6,color:#ecf0f1,stroke-width:3px,stroke-dasharray:5 5
```

**Key LangGraph API calls that build this graph:**

```python
# core/orchestrator.py — build_orchestrator()

workflow = StateGraph(ComplianceState)             # 1. Create graph with typed state

workflow.add_node("regulatory_tracker",    ...)    # 2. Register each agent as a node
workflow.add_node("transaction_monitor",   ...)
workflow.add_node("communication_scanner", ...)
workflow.add_node("conflict_resolution",   ...)
workflow.add_node("hitl_placeholder",      ...)
workflow.add_node("report_generator",      ...)

workflow.set_entry_point("regulatory_tracker")     # 3. Define entry point

workflow.add_edge("regulatory_tracker",    "transaction_monitor")    # 4. Sequential edges
workflow.add_edge("transaction_monitor",   "communication_scanner")
workflow.add_edge("communication_scanner", "conflict_resolution")

workflow.add_conditional_edges(                    # 5. Conditional routing
    "conflict_resolution",
    _route_after_conflict_resolution,              #    Router function
    {
        "hitl_placeholder": "hitl_placeholder",    #    HIGH/CRITICAL → pause
        "report_generator": "report_generator",    #    NONE → skip HITL
    },
)

workflow.add_edge("hitl_placeholder", "report_generator")  # 6. HITL → Report
workflow.add_edge("report_generator", END)                 # 7. Report → END

app = workflow.compile(                            # 8. Compile with checkpoint
    checkpointer=SqliteSaver(conn),
    interrupt_before=["report_generator"]          # 9. Pause BEFORE report generation
)
```

### ComplianceState Schema

Every node reads from and writes to a single **shared state object**. LangGraph passes this `TypedDict` between nodes automatically:

```mermaid
classDiagram
    class ComplianceState {
        +Optional~Dict~ current_transaction
        +Optional~Dict~ current_loan
        +Optional~Dict~ current_communication
        +List~Dict~ raw_transactions
        +List~Dict~ raw_communications
        +List~Dict~ active_rules
        +Annotated~List~Dict~~ alerts ← operator.add
        +Annotated~List~str~~ flagged_entities ← operator.add
        +List~Dict~ regulatory_updates
        +str escalation_status
        +Optional~str~ human_feedback
        +Optional~str~ report_content
    }

    class RegulatoryTracker {
        writes: active_rules
    }
    class TransactionMonitor {
        writes: alerts (appended)
    }
    class CommunicationScanner {
        writes: alerts (appended)
    }
    class CorrelationEngine {
        writes: alerts, escalation_status, flagged_entities
    }
    class HITLPlaceholder {
        writes: human_feedback
    }
    class ReportGenerator {
        writes: report_content
    }

    ComplianceState <|-- RegulatoryTracker
    ComplianceState <|-- TransactionMonitor
    ComplianceState <|-- CommunicationScanner
    ComplianceState <|-- CorrelationEngine
    ComplianceState <|-- HITLPlaceholder
    ComplianceState <|-- ReportGenerator
```

### State Reducers & Accumulation

LangGraph's **state reducer** mechanism is critical to how alerts accumulate across agents without overwriting:

```python
# core/state.py
from typing import Annotated
import operator

class ComplianceState(TypedDict):
    # Standard fields — LAST WRITE WINS
    active_rules: List[Dict[str, Any]]       # Overwritten by regulatory_tracker
    escalation_status: str                    # Overwritten by conflict_resolution

    # Annotated fields — APPEND-ONLY ACCUMULATION via operator.add
    alerts: Annotated[List[Dict], operator.add]          # []+[a1]+[a2]+[meta] = all alerts
    flagged_entities: Annotated[List[str], operator.add]  # Union of all flagged IDs
```

```mermaid
graph LR
    subgraph "alerts Accumulation (operator.add)"
        S0["Initial State<br/>alerts = [ ]"]
        S1["After Transaction Monitor<br/>alerts = [ALERT_DET_1]"]
        S2["After Comm Scanner<br/>alerts = [ALERT_DET_1, ALERT_COMM_1]"]
        S3["After Correlation Engine<br/>alerts = [ALERT_DET_1, ALERT_COMM_1, META_1]"]
    end

    S0 -->|"return {'alerts': [ALERT_DET_1]}"| S1
    S1 -->|"return {'alerts': [ALERT_COMM_1]}"| S2
    S2 -->|"return {'alerts': [META_1]}"| S3

    style S0 fill:#2c3e50,color:#ecf0f1
    style S1 fill:#e67e22,color:#ecf0f1
    style S2 fill:#e74c3c,color:#ecf0f1
    style S3 fill:#8e44ad,color:#ecf0f1
```

> **Why this matters:** Without `operator.add`, each agent's `return {"alerts": [...]}` would **overwrite** the previous alerts. The `Annotated` reducer ensures every agent's output is **appended** to the growing list.

### Conditional Routing

After the Correlation Engine scores all alerts, a **router function** decides the execution path:

```mermaid
graph TD
    CR["conflict_resolution<br/>returns escalation_status"]
    ROUTER{"_route_after_conflict_resolution()"}
    HITL["hitl_placeholder<br/>(Human Review)"]
    RG["report_generator<br/>(Auto-approve)"]

    CR --> ROUTER
    ROUTER -->|"status == ESCALATED<br/>or PENDING_REVIEW"| HITL
    ROUTER -->|"status == NONE"| RG

    style ROUTER fill:#f39c12,stroke:#e67e22,color:#2c3e50,stroke-width:3px
```

```python
# core/orchestrator.py
def _route_after_conflict_resolution(state: ComplianceState) -> str:
    status = state.get("escalation_status", "NONE")
    if status in ("ESCALATED", "PENDING_REVIEW"):
        return "hitl_placeholder"    # → Pause for human review
    return "report_generator"        # → Generate report automatically
```

### Interrupt & Resume (HITL)

LangGraph's `interrupt_before` is the mechanism powering the Human-in-the-Loop review. The graph **pauses** before `report_generator`, saves its full state to SQLite, and waits for the Streamlit UI to resume it:

```mermaid
sequenceDiagram
    participant User as 👤 Compliance Officer
    participant UI as 🖥️ Streamlit Dashboard
    participant Graph as ⚙️ LangGraph Engine
    participant SQLite as 💾 SQLite Checkpointer

    User->>UI: Click "Run Surveillance Scan"
    UI->>Graph: graph_app.invoke(initial_state, config)
    Graph->>Graph: Execute: regulatory_tracker → transaction_monitor → communication_scanner → conflict_resolution
    Graph->>Graph: Router: escalation_status = "ESCALATED"

    Note over Graph,SQLite: 🛑 interrupt_before=["report_generator"]<br/>Graph PAUSES here

    Graph->>SQLite: Save full state (alerts, rules, entities)
    Graph-->>UI: Returns (graph is paused)
    UI->>SQLite: Fetch state via graph_app.get_state(config)
    UI->>User: Display alerts + HITL review panel

    alt ✅ Approve
        User->>UI: Click "Approve & Generate Report"
        UI->>Graph: graph_app.update_state(config, {"human_feedback": "APPROVED"})
        UI->>Graph: graph_app.invoke(None, config)
        Graph->>Graph: Execute: report_generator
        Graph->>SQLite: Save final state with report_content
        Graph-->>UI: Returns
        UI->>User: Display Final Audit Report
    else ❌ Reject & Teach
        User->>UI: Enter reason + Click "Reject & Teach AI"
        UI->>UI: Embed rejection context into ChromaDB false_positives
        UI->>Graph: graph_app.update_state(config, {"human_feedback": "REJECTED: ..."})
        UI->>Graph: graph_app.invoke(None, config)
        Graph->>Graph: Execute: report_generator (generates rejection report)
        Graph-->>UI: Returns
        UI->>User: Display Rejection Report
    end
```

---

## 🤖 Agent Architecture

### Agent 1: Regulatory Tracker (RAG)

**File:** `agent/regulatory_tracker.py`  
**Purpose:** Retrieves relevant compliance rules from ChromaDB based on the type of data in the current scan (trades, loans, communications).

```mermaid
graph LR
    subgraph "Regulatory Tracker Node"
        STATE["ComplianceState"]
        QUERY["Build Context Queries<br/>'wash trading market abuse'<br/>'lending AML fraud'<br/>'off-channel insider trading'"]
        EMBED["Embed Query<br/>(Gemini Embedding 2<br/>→ ONNX Fallback)"]
        CHROMA[("ChromaDB<br/>Regulatory Rules")]
        DEDUP["Deduplicate<br/>by page_content"]
        OUTPUT["Return:<br/>active_rules[]"]
    end

    STATE -->|"Check state keys"| QUERY
    QUERY --> EMBED
    EMBED -->|"Similarity Search k=3"| CHROMA
    CHROMA --> DEDUP
    DEDUP --> OUTPUT
```

### Agent 2: Transaction Monitor

**File:** `agent/transaction_monitor.py`  
**Purpose:** Two-layer detection — deterministic rule checks run first (zero-latency), then the LLM performs behavioral analysis on time-series grouped transactions.

```mermaid
graph TD
    subgraph "Transaction Monitor Node"
        direction TB
        TX["Raw Transactions"]

        subgraph DET["Layer 1: Deterministic Checks (No LLM)"]
            STRUCT["💰 Structuring Detection<br/>$9,000 ≤ amount < $10,000<br/>→ MEDIUM alert"]
            LOAN["🏦 Suspicious Loan Detection<br/>amount > $1M + FICO < 500 + APPROVED<br/>→ CRITICAL alert"]
        end

        subgraph LLM_LAYER["Layer 2: LLM Behavioral Analysis"]
            GROUP["Group by entity_id<br/>(time-series arrays)"]
            FP_CHECK["Query ChromaDB<br/>false_positives<br/>(negative constraints)"]
            GEMINI["Gemini 3.1 Flash-Lite<br/>with_structured_output(AlertList)<br/>Temperature: 0.0"]
        end

        MERGE["Merge Deterministic<br/>+ LLM Alerts"]
    end

    TX --> DET
    TX --> GROUP
    DET --> MERGE
    GROUP --> FP_CHECK
    FP_CHECK --> GEMINI
    GEMINI --> MERGE

    style DET fill:#27ae60,stroke:#2ecc71,color:#ecf0f1
    style LLM_LAYER fill:#2980b9,stroke:#3498db,color:#ecf0f1
```

### Agent 3: Communication Scanner (ReAct)

**File:** `agent/communication_scanner.py`  
**Purpose:** A full **ReAct agent** that can autonomously decide to call tools. If an employee mentions a stock ticker, the agent **stops reasoning**, queries the transaction ledger via a tool, and incorporates the results before making its final judgment.

```mermaid
graph TD
    subgraph "Communication Scanner — ReAct Agent Loop"
        MSGS["Employee Communications"]
        SYS["System Prompt:<br/>'If a ticker is mentioned,<br/>use query_transactions tool'"]

        subgraph REACT_LOOP["ReAct Agent Loop"]
            LLM1["🧠 LLM Pass 1: Reason<br/>(llm.bind_tools)"]
            DECIDE{"Tool call<br/>requested?"}
            TOOL["🔧 query_transactions(ticker)<br/>Search transaction ledger"]
            LLM2["🧠 LLM Pass 2: Re-evaluate<br/>with tool results"]
        end

        STRUCT_OUT["Structured Output Pass<br/>with_structured_output(AlertList)"]
        OUTPUT["Return: alerts[]"]
    end

    MSGS --> SYS
    SYS --> LLM1
    LLM1 --> DECIDE
    DECIDE -->|"Yes: tool_calls present"| TOOL
    TOOL -->|"ToolMessage"| LLM2
    LLM2 --> STRUCT_OUT
    DECIDE -->|"No: direct answer"| STRUCT_OUT
    STRUCT_OUT --> OUTPUT

    style REACT_LOOP fill:#8e44ad,stroke:#9b59b6,color:#ecf0f1
    style TOOL fill:#e74c3c,stroke:#c0392b,color:#ecf0f1
```

**Example ReAct execution:**

```
Message: "TRADER_007 just gave me the nod. Go heavy on NVDA right now."

🧠 LLM Pass 1: "I see ticker NVDA mentioned. I should check the ledger."
   → tool_call: query_transactions(ticker="NVDA")

🔧 Tool Result: [{"trader_id": "TRADER_007", "symbol": "NVDA", "quantity": 1000, ...}]

🧠 LLM Pass 2: "CONFIRMED — TRADER_007 bought 1000 shares of NVDA within minutes
    of SPOUSE_001's message. This is insider tipping. CRITICAL."
```

### Agent 4: Correlation Engine (Semantic)

**File:** `core/orchestrator.py` → `conflict_resolution_node()`  
**Purpose:** Cross-references alerts from different agents to detect **coordinated multi-channel breaches** that no single agent could identify alone.

```mermaid
graph LR
    subgraph "Correlation Engine"
        A_TX["Transaction Alerts<br/>(from Agent 2)"]
        A_COMM["Communication Alerts<br/>(from Agent 3)"]
        FUSE["🧠 Gemini LLM<br/>'Find semantic links<br/>across different alerts'"]
        META["META-ALERT<br/>CRITICAL severity<br/>linked_alert_ids: [A1, A2]<br/>entities_involved: [TRADER_007, SPOUSE_001]"]
        SCORE["Calculate Escalation<br/>CRITICAL→ESCALATED<br/>HIGH→PENDING_REVIEW<br/>*→NONE"]
    end

    A_TX --> FUSE
    A_COMM --> FUSE
    FUSE -->|"Correlated events found"| META
    FUSE -->|"No correlations"| SCORE
    META --> SCORE

    style META fill:#c0392b,stroke:#e74c3c,color:#ecf0f1,stroke-width:3px
```

### Agent 5: Report Generator

**File:** `core/orchestrator.py` → `report_generator_node()`  
**Purpose:** Synthesizes all alerts, rules, and human feedback into a professional Markdown audit report.

| Section | Content |
|---|---|
| Executive Summary | Lead with coordinated breach findings |
| Regulatory Framework | Cite each rule by jurisdiction/ID |
| Coordinated Breach Analysis | META-ALERT evidence chains |
| Individual Findings | One sub-section per entity_id |
| Risk Matrix | Entity \| Violation \| Source \| Level \| Action |
| Recommended Actions | Prioritized by severity |
| Conclusion | Overall verdict |

---

## 🔧 Resilience Engineering

### Tenacity Retry Architecture

Every external API call is wrapped with **tenacity** decorators for automatic retry with exponential backoff:

```mermaid
graph TD
    subgraph "Tenacity Retry Policy"
        CALL["API Call<br/>(embedding / LLM)"]
        ATTEMPT{"Attempt N<br/>of 3"}
        WAIT["⏳ Exponential Backoff<br/>2ˢ → 4ˢ → 8ˢ<br/>(capped at 60s)"]
        SUCCESS["✅ Success<br/>Return result"]
        EXHAUST["❌ All 3 attempts failed"]
        FALLBACK["🔄 Fallback to<br/>Local ONNX Embedding"]
    end

    CALL --> ATTEMPT
    ATTEMPT -->|"Success"| SUCCESS
    ATTEMPT -->|"504 / Timeout / Exception"| WAIT
    WAIT --> ATTEMPT
    ATTEMPT -->|"Attempt 3 failed"| EXHAUST
    EXHAUST --> FALLBACK

    style WAIT fill:#e67e22,stroke:#d35400,color:#ecf0f1
    style FALLBACK fill:#27ae60,stroke:#2ecc71,color:#ecf0f1
    style EXHAUST fill:#c0392b,stroke:#e74c3c,color:#ecf0f1
```

**Three wrapped functions in `regulatory_tracker.py`:**

```python
@retry(wait=wait_exponential(min=2, max=60), stop=stop_after_attempt(3))
def _embed_query_with_retry(emb, text):       # Smoke-test on startup
    ...

@retry(...)
def _retriever_invoke_with_retry(retriever, query):  # Every RAG search
    ...

@retry(...)
def _similarity_search_with_retry(db, text, k):      # Every false-positive lookup
    ...
```

### Local Embedding Fallback (Adapter Pattern)

When the Gemini Embedding API is unavailable (504 timeouts, rate limits, no API key), the system automatically falls back to **ChromaDB's built-in ONNXMiniLM-L6-V2** — a local sentence-transformer that runs entirely on CPU with zero API calls:

```mermaid
graph TD
    subgraph "Embedding Resolution Strategy"
        START["Need embeddings"]
        TRY_GEMINI["Try: GoogleGenerativeAIEmbeddings<br/>(models/gemini-embedding-2)"]
        SMOKE["Smoke test: embed_query('test')"]
        GEMINI_OK["✅ Use Gemini Embeddings"]
        RETRY["RetryError after 3 attempts"]
        ADAPTER["_LocalEmbeddingAdapter"]

        subgraph ADAPTER_DETAIL["Adapter Pattern (Bridge)"]
            ONNX["chromadb.DefaultEmbeddingFunction()<br/>(ONNXMiniLM_L6_V2)"]
            BRIDGE_Q[".embed_query(text)<br/>→ self._fn(#91;text#93;)#91;0#93;"]
            BRIDGE_D[".embed_documents(texts)<br/>→ list(self._fn(texts))"]
        end

        LOCAL_OK["✅ Use Local ONNX Embeddings<br/>(No API needed)"]
    end

    START --> TRY_GEMINI
    TRY_GEMINI --> SMOKE
    SMOKE -->|"Success"| GEMINI_OK
    SMOKE -->|"504 / Timeout"| RETRY
    RETRY --> ADAPTER
    ADAPTER --> ONNX
    ONNX --> BRIDGE_Q
    ONNX --> BRIDGE_D
    ADAPTER --> LOCAL_OK

    style GEMINI_OK fill:#27ae60,color:#ecf0f1
    style LOCAL_OK fill:#2980b9,color:#ecf0f1
    style RETRY fill:#c0392b,color:#ecf0f1
```

> **Why an adapter?** ChromaDB's `DefaultEmbeddingFunction` uses the signature `fn(texts: List[str]) → List[List[float]]` (a callable). LangChain's `Chroma` vectorstore expects `.embed_query()` / `.embed_documents()` methods. The `_LocalEmbeddingAdapter` class bridges these two interfaces.

### Embedding Call Flow

Complete flow showing how every embedding call is protected across all agents:

```mermaid
flowchart TB
    subgraph "Agent Call Sites"
        RT["regulatory_tracker<br/>retriever.invoke(query)"]
        TM["transaction_monitor<br/>db.similarity_search(tx_str)"]
        CS["communication_scanner<br/>db.similarity_search(comm_str)"]
    end

    subgraph "Tenacity Layer"
        R1["_retriever_invoke_with_retry()"]
        R2["_similarity_search_with_retry()"]
        R3["_similarity_search_with_retry()"]
    end

    subgraph "Embedding Backend"
        GEMINI["Gemini Embedding 2<br/>(Cloud API)"]
        ONNX["ONNXMiniLM_L6_V2<br/>(Local CPU)"]
    end

    RT --> R1
    TM --> R2
    CS --> R3
    R1 --> GEMINI
    R2 --> GEMINI
    R3 --> GEMINI
    GEMINI -->|"504 / timeout<br/>after 3 retries"| ONNX
```

---

## 💾 Persistent State & Memory

Two persistence layers ensure no data is lost across restarts:

```mermaid
graph LR
    subgraph "SQLite Checkpointer"
        SQLITE[("checkpoints.sqlite")]
        STATE["Full ComplianceState<br/>per thread_id"]
        THREAD["Thread IDs:<br/>case_001, case_001_run_1716820505"]
    end

    subgraph "ChromaDB Vector Store"
        CHROMA[("chroma_db/")]
        REGS["Collection: langchain<br/>(6 regulatory chunks)"]
        FPS["Collection: false_positives<br/>(human rejection embeddings)"]
    end

    STATE --> SQLITE
    THREAD --> SQLITE
    REGS --> CHROMA
    FPS --> CHROMA
```

| Store | Technology | Purpose | Persistence |
|---|---|---|---|
| `checkpoints.sqlite` | SQLite via `SqliteSaver` | Full graph state per case ID (alerts, rules, human feedback, reports) | Bind-mounted Docker volume |
| `chroma_db/` (langchain collection) | ChromaDB 0.5 | Regulation rule chunks for RAG retrieval | Bind-mounted Docker volume |
| `chroma_db/` (false_positives collection) | ChromaDB 0.5 | Human rejection reasons, embedded for negative constraint injection | Bind-mounted Docker volume |

---

## 🔄 Adaptive Learning Loop

When a Compliance Officer rejects alerts, the system **learns** from the feedback:

```mermaid
graph TD
    subgraph "Scan N: First Encounter"
        ALERT1["⚠️ Alert: 'Large transfer $50K<br/>between corporate accounts'"]
        OFFICER1["👤 Officer: REJECT<br/>'Known monthly corporate transfer'"]
        EMBED1["Embed rejection into ChromaDB:<br/>'Alert Reason: Large transfer...<br/>Human Rejection: Known monthly corporate transfer'"]
    end

    subgraph "Scan N+1: Next Encounter"
        SIMILAR["Similar transaction detected"]
        QUERY_FP["Query false_positives collection<br/>(similarity_search)"]
        CONSTRAINT["Inject negative constraint:<br/>'A human previously rejected a similar<br/>case because Known monthly corporate transfer.<br/>Consider downgrading the severity.'"]
        LLM["🧠 LLM receives constraint<br/>in prompt context"]
        RESULT["Alert downgraded or suppressed"]
    end

    ALERT1 --> OFFICER1
    OFFICER1 --> EMBED1
    EMBED1 -.->|"Persisted in ChromaDB"| QUERY_FP
    SIMILAR --> QUERY_FP
    QUERY_FP --> CONSTRAINT
    CONSTRAINT --> LLM
    LLM --> RESULT

    style EMBED1 fill:#8e44ad,stroke:#9b59b6,color:#ecf0f1
    style RESULT fill:#27ae60,stroke:#2ecc71,color:#ecf0f1
```

---

## 🚀 CI/CD Pipeline & Deployment

### Docker Architecture

```mermaid
graph TB
    subgraph "Docker Container: ai-compliance-monitor"
        subgraph "Security"
            USER["👤 appuser (non-root)<br/>UID: system"]
        end

        subgraph "Application"
            STREAMLIT["Streamlit Server<br/>:8501"]
            APP["app.py → orchestrator → agents"]
        end

        subgraph "Health"
            HC["healthcheck: curl /_stcore/health<br/>interval: 30s, retries: 3"]
        end
    end

    subgraph "Host Machine"
        SECRET["🔑 gemini_api_key.txt<br/>(Docker Secret)"]
        SQLITE_HOST["checkpoints.sqlite<br/>(bind mount)"]
        CHROMA_HOST["chroma_db/<br/>(bind mount)"]
    end

    subgraph "Registry"
        GHCR["ghcr.io/paragiscool/<br/>compliance-monitoring-system:latest"]
    end

    SECRET -->|"/run/secrets/google_api_key"| APP
    SQLITE_HOST -->|"/app/checkpoints.sqlite"| APP
    CHROMA_HOST -->|"/app/chroma_db"| APP
    APP --> GHCR

    style USER fill:#e74c3c,stroke:#c0392b,color:#ecf0f1
    style HC fill:#27ae60,stroke:#2ecc71,color:#ecf0f1
```

### GitHub Actions Pipeline

```mermaid
graph LR
    subgraph "GitHub Actions: Docker Image CI"
        PUSH["Push to main"]
        CHECKOUT["actions/checkout@v4"]
        LOGIN["docker login ghcr.io<br/>(GITHUB_TOKEN)"]
        BUILD["docker build -t<br/>ghcr.io/paragiscool/compliance-monitoring-system:latest"]
        DEPLOY["docker push<br/>ghcr.io/paragiscool/compliance-monitoring-system:latest"]
    end

    PUSH --> CHECKOUT
    CHECKOUT --> LOGIN
    LOGIN --> BUILD
    BUILD --> DEPLOY

    style PUSH fill:#2c3e50,color:#ecf0f1
    style DEPLOY fill:#27ae60,color:#ecf0f1
```

> **"Bare Metal Bypass" strategy:** The CI/CD workflow uses raw `docker build` and `docker push` commands instead of third-party GitHub Actions, eliminating dependency on external action maintainers and CDN availability.

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/Paragiscool/Compliance-Monitoring-System.git
cd Compliance-Monitoring-System

# Create the API key secret (optional — system works without it via local fallback)
echo -n "YOUR_GEMINI_API_KEY" > gemini_api_key.txt

# Build and start
docker compose up --build -d

# Ingest regulations into ChromaDB (first time only)
docker exec ai-compliance-monitor python -m scripts.ingest_regulations

# Open the dashboard
# → http://localhost:8501
```

### Option 2: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# Ingest regulations
python -m scripts.ingest_regulations

# Launch the dashboard
streamlit run app.py
```

---

## 📁 Project Structure

```
📦 Compliance-Monitoring-System
├── 🖥️  app.py                          # Streamlit HITL Dashboard
├── 🐳  Dockerfile                       # Multi-stage container build
├── 🐳  docker-compose.yml               # Orchestration with secrets + volumes
├── 📋  requirements.txt                 # Pinned Python dependencies + tenacity
│
├── ⚙️  core/
│   ├── orchestrator.py                  # LangGraph StateGraph builder + all nodes
│   ├── state.py                         # ComplianceState TypedDict with reducers
│   └── models.py                        # Pydantic models: Alert, AlertList, etc.
│
├── 🤖 agent/
│   ├── regulatory_tracker.py            # RAG retrieval + tenacity retry + ONNX fallback
│   ├── transaction_monitor.py           # Deterministic + LLM transaction analysis
│   ├── communication_scanner.py         # ReAct tool-calling agent
│   └── llm_wrapper.py                   # RobustLLM with role-based temperature configs
│
├── 📊 data/
│   ├── mock_transactions.json           # Sample trade + loan records
│   ├── mock_communications.json         # Sample employee communications
│   ├── regulations/mock_regulations.md  # SEC, FINRA, OFAC, wash trading rules
│   ├── validation_suite.json            # 20-scenario golden dataset
│   └── red_team_suite.json              # Adversarial test cases
│
├── 🔧 scripts/
│   ├── ingest_regulations.py            # ChromaDB vectorstore builder
│   ├── generate_mock_data.py            # Synthetic data generator
│   ├── generate_validation_suite.py     # Golden dataset builder
│   ├── generate_red_team_suite.py       # Adversarial scenario builder
│   └── run_validation_harness.py        # Automated accuracy testing
│
├── 💾 checkpoints.sqlite               # LangGraph persistent state
├── 🧠 chroma_db/                       # ChromaDB vectorstore (regulations + false positives)
│
├── 📖 docs/
│   └── troubleshooting_log_may_2026.md  # Engineering post-mortem
├── 📖 DEPLOYMENT.md                     # Full deployment guide
│
└── 🔄 .github/workflows/
    └── docker-publish.yml               # CI/CD: Build → Push to GHCR
```

---

## 📊 Performance Metrics

Validated against a **20-scenario golden dataset** featuring complex insider-tipping, OFAC structuring edge-cases, and false-positive NLP trigger tests:

| Metric | Value |
|---|---|
| Detection Accuracy | 85% (baseline) → ~100% post-tuning |
| False Positive Rate | 0% on contextual "Clean" scenarios |
| Deterministic Check Latency | < 1ms per transaction |
| LLM Analysis (Gemini 3.1 Flash-Lite) | ~2–5s per batch |
| Local ONNX Embedding Fallback | ~200ms per query |
| Container Health Check | Every 30s, auto-restart after 3 failures |

---

## 🔧 Troubleshooting

| Issue | Solution |
|---|---|
| `504 Deadline Exceeded` | Tenacity auto-retries 3× → falls back to local ONNX embeddings |
| `'ONNXMiniLM_L6_V2' has no attribute 'embed_query'` | Fixed via `_LocalEmbeddingAdapter` bridge class |
| `PermissionError: /home/appuser` | ONNX model path redirected to `/tmp/chroma_cache` |
| ChromaDB `TypeError: object of type 'int' has no len()` | Delete `chroma_db/` and re-ingest (version mismatch) |
| `No rules retrieved from ChromaDB` | Run `docker exec ai-compliance-monitor python -m scripts.ingest_regulations` |
| Port 8501 in use | Change host port in `docker-compose.yml`: `"8502:8501"` |
| Container exits immediately | Check: `docker compose logs compliance-system` |

> 📖 **Full engineering post-mortem:** [docs/troubleshooting_log_may_2026.md](docs/troubleshooting_log_may_2026.md)  
> 📖 **Detailed deployment guide:** [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 📜 License

This project is developed for educational purposes as part of a portfolio demonstration of production-grade AI engineering.

---

<p align="center">
  <i>Built with 🧠 LangGraph · 🤖 Gemini · 🛡️ ChromaDB · 🐳 Docker</i>
  <br/>
  <i>Maintained by the Compliance AI Team — May 2026</i>
</p>
