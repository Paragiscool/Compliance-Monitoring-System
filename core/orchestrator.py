"""
core/orchestrator.py

Builds and returns the compiled LangGraph application for the
Compliance Monitoring System.

Graph Topology:
  regulatory_tracker
        │
        ▼
  transaction_monitor
        │
        ▼
  communication_scanner
        │
        ▼
  conflict_resolution
        │
   ┌────┴────────────┐
   ▼                 ▼
hitl_placeholder   report_generator ──► END
        │
        ▼
  report_generator ──► END
"""

from typing import Dict, Any
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END

from core.state import ComplianceState
from agent.regulatory_tracker import get_regulatory_tracker_node
from agent.transaction_monitor import get_transaction_monitor_node
from agent.communication_scanner import get_communication_scanner_node

load_dotenv()


# ── Stub nodes (to be replaced in Days 7/10/11) ──────────────────────────────

def conflict_resolution_node(state: ComplianceState) -> Dict[str, Any]:
    """
    Evaluates all accumulated alerts and determines whether the case needs
    human escalation (HITL) or can proceed directly to report generation.
    """
    print("--- AGENT: CONFLICT RESOLUTION ---")
    alerts = state.get("alerts", [])

    severity_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

    # Find the highest severity across all alerts
    max_severity = "NONE"
    max_rank = 0
    for alert in alerts:
        level = alert.get("risk_level", "LOW").upper()
        rank = severity_rank.get(level, 0)
        if rank > max_rank:
            max_rank = rank
            max_severity = level

    # Determine escalation status
    if max_rank >= 4:  # CRITICAL
        escalation = "ESCALATED"
    elif max_rank >= 3:  # HIGH
        escalation = "PENDING_REVIEW"
    else:
        escalation = "NONE"

    print(
        f"INFO [ConflictResolution]: {len(alerts)} alert(s). "
        f"Max severity: {max_severity}. Escalation: {escalation}."
    )
    return {
        "escalation_status": escalation,
        "flagged_entities": [
            a.get("entity_id", "UNKNOWN") for a in alerts
        ],
    }


def hitl_placeholder_node(state: ComplianceState) -> Dict[str, Any]:
    """
    Placeholder for Human-in-the-Loop (Day 11).
    In the full build this will use LangGraph's interrupt() to pause execution
    and surface the case to the Streamlit Compliance Officer Dashboard.
    """
    print("--- HITL PLACEHOLDER (Day 11 implementation pending) ---")
    print(f"  Escalation status: {state.get('escalation_status')}")
    print(f"  Flagged entities:  {state.get('flagged_entities')}")
    # For now, auto-approve to let execution continue
    return {"human_feedback": "AUTO_APPROVED_FOR_TESTING"}


def report_generator_node(state: ComplianceState) -> Dict[str, Any]:
    """
    Stub report generator (Day 7 will replace this with the full synthesis engine).
    """
    print("--- AGENT 4: REPORT GENERATOR (stub) ---")
    alerts = state.get("alerts", [])
    escalation = state.get("escalation_status", "NONE")

    lines = [
        "# Compliance Monitoring Report",
        f"**Escalation Status**: {escalation}",
        f"**Total Alerts**: {len(alerts)}",
        "",
        "## Alerts",
    ]
    for i, alert in enumerate(alerts, 1):
        lines.append(
            f"{i}. [{alert.get('risk_level', 'N/A')}] "
            f"{alert.get('source_agent', '?')} — {alert.get('reason', '?')}"
        )

    report = "\n".join(lines)
    print(report)
    return {"report_content": report}


# ── Router ───────────────────────────────────────────────────────────────────

def _route_after_conflict_resolution(state: ComplianceState) -> str:
    """
    Routes to HITL for CRITICAL/HIGH alerts; direct to report for everything else.
    """
    status = state.get("escalation_status", "NONE")
    if status in ("ESCALATED", "PENDING_REVIEW"):
        return "hitl_placeholder"
    return "report_generator"


# ── Graph Builder ─────────────────────────────────────────────────────────────

def build_orchestrator():
    """
    Compiles and returns the LangGraph application.
    Call once at startup and reuse the compiled app.
    """
    workflow = StateGraph(ComplianceState)

    # Register nodes
    workflow.add_node("regulatory_tracker",    get_regulatory_tracker_node())
    workflow.add_node("transaction_monitor",   get_transaction_monitor_node())
    workflow.add_node("communication_scanner", get_communication_scanner_node())
    workflow.add_node("conflict_resolution",   conflict_resolution_node)
    workflow.add_node("hitl_placeholder",      hitl_placeholder_node)
    workflow.add_node("report_generator",      report_generator_node)

    # Sequential edges
    workflow.set_entry_point("regulatory_tracker")
    workflow.add_edge("regulatory_tracker",    "transaction_monitor")
    workflow.add_edge("transaction_monitor",   "communication_scanner")
    workflow.add_edge("communication_scanner", "conflict_resolution")

    # Conditional edge: escalate or report directly
    workflow.add_conditional_edges(
        "conflict_resolution",
        _route_after_conflict_resolution,
        {
            "hitl_placeholder": "hitl_placeholder",
            "report_generator": "report_generator",
        },
    )

    # HITL always leads to report after human review
    workflow.add_edge("hitl_placeholder", "report_generator")
    workflow.add_edge("report_generator", END)

    return workflow.compile()


# ── Quick smoke-test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = build_orchestrator()
    print("[OK] Orchestrator compiled successfully. Running smoke test...\n")

    initial_state: ComplianceState = {
        "current_transaction": {
            "transaction_id": "TEST_TX_123",
            "trader_id": "TRADER_007",
            "symbol": "TSLA",
            "quantity": 500,
            "price": 200.0,
            "timestamp": "2026-05-22T10:00:00",
            "order_type": "MARKET",
            "asset_class": "EQUITY",
        },
        "current_loan": None,
        "current_communication": {
            "comm_id": "TEST_MSG_456",
            "sender_id": "EMP_001",
            "receiver_ids": ["CLIENT_007"],
            "channel": "WHATSAPP",
            "timestamp": "2026-05-22T11:00:00",
            "content": "I can guarantee a 15% return. Don't use email, text me instead.",
        },
        "active_rules": [],
        "flagged_entities": [],
        "alerts": [],
        "regulatory_updates": [],
        "escalation_status": "NONE",
        "human_feedback": None,
        "report_content": None,
    }

    for step_output in app.stream(initial_state):
        node_name = list(step_output.keys())[0]
        print(f"\n[STEP: {node_name}]")
        print("----")
