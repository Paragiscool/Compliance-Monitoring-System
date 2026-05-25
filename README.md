# 🛡️ Enterprise AI Compliance Monitoring System

An autonomous, multi-agent surveillance system built to detect complex financial crimes (Insider Trading, Wash Trading, Structuring, and Spoofing) across both transaction ledgers and employee communication channels.

Powered by **LangGraph**, **Google Gemini**, and **Streamlit**, this system moves beyond deterministic rules engines by utilizing semantic correlation, time-series reasoning, and an adaptive human-in-the-loop feedback system.

## 🏗️ System Architecture

* **UI Interface:** Streamlit
* **Agent Orchestration:** LangGraph (Stateful multi-agent routing)
* **LLM Engine:** Google Gemini (`gemini-3.1-flash-lite` via LangChain)
* **Vector Store (RAG & Learning):** ChromaDB
* **State Persistence:** SQLite (`SqliteSaver` Checkpointer)

## ✨ Core Features

1. **Multi-Agent Orchestration:** 
   - **Regulatory Tracker (Agent 1):** Ingests SEC/FINRA/OFAC rules into ChromaDB and performs RAG retrieval.
   - **Transaction Monitor (Agent 2):** Stateful time-series analysis to catch sequence-based market manipulation (e.g., Wash Trading).
   - **Communication Scanner (Agent 3):** A ReAct (Reason + Act) tool-calling agent that scans emails/chats and dynamically queries the transaction ledger to corroborate suspicious intent.
2. **Semantic Correlation Engine:** Evaluates isolated alerts from different data silos and fuses them into `CRITICAL META-ALERTS` if it detects cross-entity coordination (e.g., a spouse's text message correlating with a trader's execution).
3. **Enterprise Fault Tolerance:** Utilizes LangGraph's SQLite Checkpointer to save graph states by `Case ID`. Server crashes or restarts will never result in lost investigations.
4. **Human-in-the-Loop (HITL):** Graph execution safely pauses before final reporting, waiting for a human Compliance Officer to approve or reject the findings via the Streamlit dashboard.
5. **Adaptive Learning Loop:** Human rejections (False Positives) are embedded and stored in ChromaDB. The agents dynamically query this history to inject negative constraints into their prompts, ensuring the AI learns from human feedback.

## 🚀 How to Run

**1. Clone and Install Dependencies:**
```bash
git clone https://github.com/yourusername/Project1B-ComplianceMonitoringSystem.git
cd Project1B-ComplianceMonitoringSystem
pip install -r requirements.txt
```

**2. Configure Environment:**
Create a `.env` file in the root directory and add your Google Gemini API key:
```
GOOGLE_API_KEY=your_gemini_api_key_here
```

**3. Run the Dashboard:**
```bash
streamlit run app.py
```

## 🧪 Validation & Testing
The system includes an automated test harness (`scripts/run_validation_harness.py`) that blasts a 20-scenario "Golden Dataset" through the engine. It currently achieves an 85%+ Accuracy Rate against complex false-positive triggers and multi-leg financial crime scenarios.
