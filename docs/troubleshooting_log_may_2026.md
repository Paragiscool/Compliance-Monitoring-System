# 🛠️ DevOps & Architecture Troubleshooting Log

*This document serves as an engineering post-mortem and knowledge base for architectural issues faced during the deployment and scaling of the LangGraph Compliance AI.*

---

## 1. GitHub Actions: 403 Checkout Error
**Symptom:** The CI/CD pipeline failed during the `actions/checkout` step with a `403 Forbidden` error.  
**Root Cause:** By default, GitHub repository tokens are restricted to read-only access for security. The workflow did not explicitly define the scope required to authenticate git operations or push to the GitHub Container Registry.  
**Resolution:** Added explicit token permission blocks to the workflow YAML:
```yaml
permissions:
  contents: read
  packages: write
```

## 2. GitHub Actions: CDN "Action Not Found" Outage
**Symptom:** The GitHub Actions pipeline failed instantly with `Error: Failed to download archive 'https://codeload.github.com/.../setup-buildx-action...' after 1 attempts.`  
**Root Cause:** A massive infrastructure outage on GitHub's end. The `codeload.github.com` CDN was caching a dead/corrupted commit SHA for standard Docker Action tags (e.g., `@v3`), causing a persistent 404/500 Internal Server Error.  
**Resolution (The "Bare Metal" Bypass):** Rather than waiting for GitHub to fix their CDN for third-party actions, we ripped out the broken abstract actions (`setup-buildx`, `metadata-action`) and wrote a pure, bare-metal bash script directly into the workflow. The runner natively executed `docker login`, `docker build`, and `docker push` using the pre-installed Docker daemon, successfully bypassing the outage.

## 3. LangGraph: SqliteSaver Context Manager Crash
**Symptom:** The Streamlit dashboard crashed with `KeyError: '__start__'` and later `Scan failed: '_GeneratorContextManager' object has no attribute 'get_next_version'`.  
**Root Cause:** A breaking API change in LangGraph version `0.2.x` and `langgraph-checkpoint-sqlite 1.0.x`. The preferred initialization method `SqliteSaver.from_conn_string()` acts as a context manager (`with` block) that immediately closes the database connection when the block ends. Because the Streamlit dashboard requires a persistent, globally available state machine, the connection was dying before the user could click "Run".  
**Resolution:** Reverted to explicit connection management. We instantiated `sqlite3.connect(..., check_same_thread=False)` directly and passed the raw persistent connection into the `SqliteSaver` constructor, keeping the database open for the lifetime of the dashboard.

## 4. Google GenAI API: 504 Deadline Exceeded (Burst Throttle)
**Symptom:** Clicking "Run Surveillance Scan" caused the system to hang, eventually throwing `Scan failed: Error embedding content: 504 Deadline Exceeded`. The dashboard showed `Gemini Embedding 1` usage spiking but failing, while `Gemini 2.5 Flash` hit the daily quota limit (22/20 RPD).  
**Root Cause:** 
1. **Model Quota Exhaustion:** The default `gemini-2.5-flash` model has a strict 20 Requests-Per-Day limit on the free tier, locking the system completely.
2. **Parallel Node Bursting:** LangGraph runs its agents concurrently. The `RegulatoryTracker` and `TransactionMonitor` both hit the Google Embedding API to search ChromaDB at the *exact same millisecond*. The free-tier servers cannot queue simultaneous bursts, causing them to drop the connection and return a generic `504 Timeout` rather than a standard `429 Rate Limit`.
**Resolution:**
* **LLM Fleet Upgrade:** Explicitly migrated all agents to `gemini-3.1-flash-lite`, which has a 500 RPD free tier limit.
* **Embedding Model Fix:** Updated the ChromaDB vector embeddings to explicitly use `models/gemini-embedding-2` instead of legacy/invalid names.
* **The "Jitter" Implementation:** To prevent simultaneous API slams, we added staggered `time.sleep()` micro-delays directly inside the execution nodes. `transaction_monitor` pauses for 1 second, and `regulatory_tracker` pauses for 2 seconds. This "anti-burst jitter" forces the parallel requests into an orderly queue, completely eliminating the 504 timeouts.
