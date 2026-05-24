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

# Extended keyword lists grouped by violation category
_KEYWORD_RULES = {
    "Unauthorized Guarantee": [
        "guarantee", "guaranteed return", "100% return", "sure thing",
        "no risk", "zero risk", "i promise you", "definitely make money",
    ],
    "Off-Channel Communication": [
        "use whatsapp", "text me instead", "call my personal", "off the record",
        "don't email", "use signal", "not through work email",
    ],
    "Insider Information": [
        "heard from a board", "inside information", "before announcement",
        "they are acquiring", "merger next week", "not public yet",
    ],
    "High-Pressure Sales": [
        "last chance", "offer expires", "don't miss out", "you'll lose everything",
        "sign today", "act now", "if you don't invest now",
    ],
}


def _make_deterministic_alert(
    entity_id: str, entity_type: str, risk_level: str, reason: str
) -> Dict[str, Any]:
    return {
        "alert_id": f"ALERT_DET_{uuid.uuid4().hex[:8]}",
        "source_agent": "Communication Scanner (Deterministic)",
        "entity_id": entity_id,
        "entity_type": entity_type,
        "risk_level": risk_level,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }


def get_communication_scanner_node():
    """
    Factory that returns the Communication Scanner LangGraph node.
    Future: swap ChatOpenAI for ChatAnthropic (Claude 3.5 Sonnet) for
    superior nuance in analysing chat transcripts.
    """

    chain = None

    if not _OPENAI_KEY_PRESENT:
        print(
            "WARNING [CommScanner]: OPENAI_API_KEY is not set. "
            "LLM NLP checks will be skipped."
        )
    else:
        # Placeholder for future Claude 3.5 Sonnet routing:
        # from langchain_anthropic import ChatAnthropic
        # llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        analyzer_llm = llm.with_structured_output(list[Alert])

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a Tier-2 Bank Communication Compliance AI. "
                    "Review the provided employee communications against the active regulatory rules. "
                    "Detect insider trading chatter, unauthorized return guarantees, off-channel "
                    "communication attempts, aggressive sales tactics, or market manipulation hints. "
                    "Generate a compliance alert for EVERY violation found. "
                    "If no violations are present, return an EMPTY list — never fabricate alerts.",
                ),
                (
                    "user",
                    "Active Regulatory Rules:\n{rules}\n\n"
                    "Communications to Review:\n{communications}",
                ),
            ]
        )
        chain = prompt | analyzer_llm

    def communication_scanner_node(state: ComplianceState) -> Dict[str, Any]:
        print("--- AGENT 3: COMMUNICATION SCANNER ---")

        comm = state.get("current_communication")
        rules = state.get("active_rules", [])
        new_alerts: list[Dict[str, Any]] = []

        if not comm:
            print("INFO [CommScanner]: No communication in state. Skipping.")
            return {"alerts": []}

        content: str = comm.get("content", "").lower()
        sender_id: str = comm.get("sender_id", "UNKNOWN")
        channel: str = comm.get("channel", "UNKNOWN").upper()

        # ── 1. Deterministic Keyword Checks ──────────────────────────────────
        for violation_type, keywords in _KEYWORD_RULES.items():
            for kw in keywords:
                if kw in content:
                    # Off-channel violations are HIGH risk; others MEDIUM
                    level = "HIGH" if violation_type == "Off-Channel Communication" else "MEDIUM"
                    new_alerts.append(
                        _make_deterministic_alert(
                            entity_id=sender_id,
                            entity_type="COMMUNICATION",
                            risk_level=level,
                            reason=(
                                f"{violation_type} detected on {channel} channel. "
                                f"Flagged phrase: \"{kw}\"."
                            ),
                        )
                    )
                    break  # One alert per category, not per keyword

        # ── 2. LLM Nuanced NLP Analysis ──────────────────────────────────────
        if chain:
            try:
                print(
                    f"INFO [CommScanner]: LLM analysis on comm "
                    f"'{comm.get('comm_id', '?')}' with {len(rules)} rule(s)..."
                )
                llm_alerts: list[Alert] = chain.invoke(
                    {"rules": rules, "communications": [comm]}
                )
                if llm_alerts:
                    new_alerts.extend([a.to_state_dict() for a in llm_alerts])
            except Exception as e:
                print(f"ERROR [CommScanner]: LLM analysis failed: {e}")
        else:
            print("INFO [CommScanner]: No LLM configured — keyword checks only.")

        print(f"INFO [CommScanner]: Generated {len(new_alerts)} alert(s).")
        return {"alerts": new_alerts}

    return communication_scanner_node
