import uuid
import os
from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from core.models import Alert, AlertList
from core.state import ComplianceState

load_dotenv()

_GOOGLE_KEY_PRESENT = (
    bool(os.getenv("GOOGLE_API_KEY"))
    and os.getenv("GOOGLE_API_KEY") != "your_google_api_key_here"
)


def _make_deterministic_alert(
    entity_id: str,
    entity_type: str,
    risk_level: str,
    reason: str,
    entities_involved: List[str] | None = None,
) -> Dict[str, Any]:
    """Helper to build a well-formed alert dict without calling the LLM."""
    return {
        "alert_id": f"ALERT_DET_{uuid.uuid4().hex[:8]}",
        "source_agent": "Transaction Monitor (Deterministic)",
        "entity_id": entity_id,
        "entity_type": entity_type,
        "risk_level": risk_level,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
        "entities_involved": entities_involved if entities_involved is not None else [entity_id],
        "linked_alert_ids": [],
    }


def get_transaction_monitor_node():
    """
    Factory that returns the Transaction Monitor LangGraph node.
    The LLM chain is created once and reused across all invocations.
    """

    chain = None

    if not _GOOGLE_KEY_PRESENT:
        print(
            "WARNING [TransactionMonitor]: GOOGLE_API_KEY is not set. "
            "LLM behavioral checks will be skipped."
        )
    else:
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.1-flash-lite",
            api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0,
        )
        # with_structured_output guarantees the LLM returns a list of Alert objects
        analyzer_llm = llm.with_structured_output(AlertList)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Tier-2 Bank Transaction Monitoring AI. 
Review the provided transactions. The data is grouped by Entity ID to help you detect time-series behavioral anomalies.

### CRITICAL DETECTION RULES ###
1. Wash Trading: The exact same entity rapidly buying and selling the same asset in a short time window. (Severity: CRITICAL)
2. Spoofing: Placing massive orders and immediately canceling them to manipulate the market. (Severity: CRITICAL)
3. BSA/AML Structuring: Any deposits, withdrawals, or transfers specifically hovering just below the $10,000 reporting threshold (e.g., $9,000 - $9,999). (Severity: MEDIUM for single instance, HIGH for cumulative instances over time).
4. Sanctions (OFAC): Any transaction involving known aliases of sanctioned individuals or entities. (Severity: CRITICAL).

### SEVERITY CALIBRATION EXAMPLES ###
- A single deposit of $9,900 -> Flag as MEDIUM (Potential Structuring).
- Five ATM withdrawals of $9,500 over five days -> Flag as HIGH (Cumulative Structuring / Velocity).
- A massive canceled 'Sell' order followed by a 'Buy' -> Flag as CRITICAL (Spoofing).
- An unverified loan -> Flag as HIGH (Do not escalate to CRITICAL unless there is cross-channel proof of fraud).

If anomalies are found, generate strict compliance alerts. 
Ensure you populate the 'entities_involved' field with the Entity ID."""),
            ("user", "Active Rules:\n{rules}\n\nGrouped Time-Series Transactions:\n{transactions}\n\n{negative_constraints}")
        ])
        chain = prompt | analyzer_llm

    def transaction_monitor_node(state: ComplianceState) -> Dict[str, Any]:
        print("--- AGENT 2: TRANSACTION MONITOR ---")

        transactions = state.get("raw_transactions", [])

        rules = state.get("active_rules", [])
        new_alerts: list[Dict[str, Any]] = []

        if not transactions:
            print("INFO [TransactionMonitor]: No transactions in state. Skipping.")
            return {"alerts": []}

        # ── 1. Deterministic Checks ──────────────────────────────────────────
        for tx in transactions:
            # Structuring detection: amounts just below the $10,000 BSA/AML reporting threshold
            amount = tx.get("amount", tx.get("price", 0) * tx.get("quantity", 0))
            if 9_000 <= amount < 10_000:
                new_alerts.append(
                    _make_deterministic_alert(
                        entity_id=tx.get("trader_id", tx.get("applicant_id", "UNKNOWN")),
                        entity_type="TRADER",
                        risk_level="MEDIUM",
                        reason=(
                            f"Potential structuring: transaction value ${amount:.2f} "
                            "falls just below the $10,000 reporting threshold."
                        ),
                        entities_involved=[
                            tx.get("trader_id", tx.get("applicant_id", "UNKNOWN"))
                        ],
                    )
                )

            # Suspicious loan: very high amount + low FICO score + already approved
            if (
                tx.get("loan_amount")
                and tx.get("loan_amount", 0) > 1_000_000
                and tx.get("risk_score", 850) < 500
                and tx.get("status") == "APPROVED"
            ):
                new_alerts.append(
                    _make_deterministic_alert(
                        entity_id=tx.get("applicant_id", "UNKNOWN"),
                        entity_type="APPLICANT",
                        risk_level="CRITICAL",
                        reason=(
                            f"Suspicious loan approval: amount ${tx['loan_amount']:,.0f} "
                            f"with FICO score {tx.get('risk_score')}. "
                            "Potential lending fraud or AML red flag."
                        ),
                        entities_involved=[tx.get("applicant_id", "UNKNOWN")],
                    )
                )

        # ── 2. Time-Series Grouping for LLM Analysis ─────────────────────────
        grouped_txs = defaultdict(list)
        for tx in transactions:
            # Safely extract the ID regardless of whether it's a loan or a trade
            entity_id = tx.get("client_id") or tx.get("trader_id") or tx.get("applicant_id") or tx.get("account_id") or "UNKNOWN"
            grouped_txs[entity_id].append(tx)

        # ── 3. LLM Behavioral Checks ─────────────────────────────────────────
        if chain:
            try:
                # Query ChromaDB for negative constraints
                negative_constraints = ""
                try:
                    from agent.regulatory_tracker import get_false_positives_db
                    import json
                    db = get_false_positives_db()
                    if db:
                        for entity_id, tx_list in grouped_txs.items():
                            tx_str = json.dumps(tx_list)
                            docs = db.similarity_search(tx_str, k=1)
                            for d in docs:
                                reason = d.metadata.get("human_reason", "")
                                negative_constraints += f"Warning for {entity_id}: A human previously rejected a similar case because '{reason}'. Consider downgrading the severity.\n"
                except Exception as e:
                    print(f"WARNING [TransactionMonitor]: Failed to query false_positives ChromaDB: {e}")

                print(
                    f"INFO [TransactionMonitor]: LLM analysis on "
                    f"{len(transactions)} transaction(s) grouped by {len(grouped_txs)} entities..."
                )
                llm_result: AlertList = chain.invoke(
                    {"rules": rules, "transactions": dict(grouped_txs), "negative_constraints": negative_constraints}
                )
                llm_alerts = llm_result.alerts if llm_result else []
                if llm_alerts:
                    # Use to_state_dict() to safely serialise datetime fields
                    new_alerts.extend([a.to_state_dict() for a in llm_alerts])
            except Exception as e:
                print(f"ERROR [TransactionMonitor]: LLM analysis failed: {e}")
        else:
            print("INFO [TransactionMonitor]: No Gemini API key — deterministic checks only.")

        print(f"INFO [TransactionMonitor]: Generated {len(new_alerts)} alert(s).")
        return {"alerts": new_alerts}

    return transaction_monitor_node
