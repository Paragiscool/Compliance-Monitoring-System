import uuid
import os
from datetime import datetime
from typing import Dict, Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from core.models import Alert
from core.state import ComplianceState

load_dotenv()

_OPENAI_KEY_PRESENT = (
    bool(os.getenv("OPENAI_API_KEY"))
    and os.getenv("OPENAI_API_KEY") != "your_openai_api_key_here"
)


def _make_deterministic_alert(entity_id: str, entity_type: str, risk_level: str, reason: str) -> Dict[str, Any]:
    """Helper to build a well-formed alert dict without calling the LLM."""
    return {
        "alert_id": f"ALERT_DET_{uuid.uuid4().hex[:8]}",
        "source_agent": "Transaction Monitor (Deterministic)",
        "entity_id": entity_id,
        "entity_type": entity_type,
        "risk_level": risk_level,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }


def get_transaction_monitor_node():
    """
    Factory that returns the Transaction Monitor LangGraph node.
    The LLM chain is created once and reused across all invocations.
    """

    chain = None

    if not _OPENAI_KEY_PRESENT:
        print(
            "WARNING [TransactionMonitor]: OPENAI_API_KEY is not set. "
            "LLM behavioral checks will be skipped."
        )
    else:
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        # with_structured_output guarantees the LLM returns a list of Alert objects
        analyzer_llm = llm.with_structured_output(list[Alert])

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a Tier-2 Bank Transaction Monitoring AI. "
                    "Review the provided transactions (trades or loans) against the active "
                    "regulatory rules. Identify wash trading, churning, sanctions evasion, "
                    "structuring, or suspicious loan approvals. "
                    "Generate a compliance alert for EVERY anomaly found. "
                    "If no anomalies are found, return an EMPTY list — never fabricate alerts.",
                ),
                (
                    "user",
                    "Active Regulatory Rules:\n{rules}\n\nTransactions to Review:\n{transactions}",
                ),
            ]
        )
        chain = prompt | analyzer_llm

    def transaction_monitor_node(state: ComplianceState) -> Dict[str, Any]:
        print("--- AGENT 2: TRANSACTION MONITOR ---")

        transactions: list[Dict[str, Any]] = []
        if state.get("current_transaction"):
            transactions.append(state["current_transaction"])
        if state.get("current_loan"):
            transactions.append(state["current_loan"])

        rules = state.get("active_rules", [])
        new_alerts: list[Dict[str, Any]] = []

        if not transactions:
            print("INFO [TransactionMonitor]: No transactions in state. Skipping.")
            return {"alerts": []}

        # ── 1. Deterministic Checks ──────────────────────────────────────────
        for tx in transactions:
            # Structuring detection: amounts just below the $10,000 BSA/AML reporting threshold
            amount = tx.get("price", 0) * tx.get("quantity", 0)
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
                    )
                )

        # ── 2. LLM Behavioral Checks ─────────────────────────────────────────
        if chain:
            try:
                print(
                    f"INFO [TransactionMonitor]: LLM analysis on "
                    f"{len(transactions)} transaction(s) with {len(rules)} rule(s)..."
                )
                llm_alerts: list[Alert] = chain.invoke(
                    {"rules": rules, "transactions": transactions}
                )
                if llm_alerts:
                    # Use to_state_dict() to safely serialise datetime fields
                    new_alerts.extend([a.to_state_dict() for a in llm_alerts])
            except Exception as e:
                print(f"ERROR [TransactionMonitor]: LLM analysis failed: {e}")
        else:
            print("INFO [TransactionMonitor]: No LLM configured — deterministic checks only.")

        print(f"INFO [TransactionMonitor]: Generated {len(new_alerts)} alert(s).")
        return {"alerts": new_alerts}

    return transaction_monitor_node
