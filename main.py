"""
main.py  -  Day 9: Correlation Engine Integration Test
=======================================================
Full end-to-end pipeline runner for the Compliance Monitoring System.

Day 9 scenario: TRADER_007 appears in BOTH a suspicious trade (wash trading)
AND a suspicious WhatsApp communication (unauthorized guarantee + off-channel).
The Correlation Engine should detect this multi-channel intersection and generate
a CRITICAL META-ALERT linking both findings.

Run:
    python main.py
"""

import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths -------------------------------------------------------------------
BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data" / "mock"
REPORT_OUT = BASE_DIR / "compliance_report_output.md"


# --- Helpers -----------------------------------------------------------------

def load_json(filename: str) -> list:
    path = DATA_DIR / filename
    if not path.exists():
        print(f"WARNING: {path} not found. Skipping.")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Day 9 KEY CHANGE: Inject a semantic cross-entity scenario.
# TRADER_007 executes a huge NVDA buy right after SPOUSE_001 texts a broker.
# ---------------------------------------------------------------------------
SEMANTIC_TRADE = {
    "transaction_id": "TX_SEMANTIC_01",
    "trader_id": "TRADER_007",
    "symbol": "NVDA",
    "order_type": "MARKET",
    "asset_class": "EQUITY",
    "action": "BUY",
    "quantity": 1000,
    "price": 900.00,
    "amount": 900000.00,
    "timestamp": "2026-05-25T14:30:00Z"
}


def pick_suspicious_loan(loans: list) -> dict | None:
    """
    Returns CUST_9999's suspicious loan: $2.5M approved at FICO 450.
    """
    susp = next((l for l in loans if l.get("applicant_id") == "CUST_9999"), None)
    return susp or (loans[0] if loans else None)


# ---------------------------------------------------------------------------
# Day 9 KEY CHANGE: Inject a communication from a different entity (SPOUSE_001)
# ---------------------------------------------------------------------------
SEMANTIC_COMM = {
    "comm_id": "MSG_SPOUSE_01",
    "sender_id": "SPOUSE_001",
    "receiver_ids": ["EXTERNAL_BROKER"],
    "channel": "SMS",
    "content": "Hey, TRADER_007 just gave me the nod. Go heavy on NVDA right now before the earnings call.",
    "timestamp": "2026-05-25T14:28:00Z"
}


# --- Banner ------------------------------------------------------------------

def print_banner():
    print("\n" + "=" * 70)
    print("  COMPLIANCE MONITORING SYSTEM  |  Day 9: Correlation Engine")
    print("  Powered by LangGraph + Gemini 2.5 Flash")
    print("=" * 70)
    print(f"  Run timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Report output : {REPORT_OUT}")
    print("=" * 70 + "\n")


# --- Main --------------------------------------------------------------------

def main():
    print_banner()

    # 1. Load mock data (loans only - trade is injected as CORRELATED_TRADE)
    print("[+] Loading mock data...")
    loans  = load_json("loans.json")
    print(f"   {len(loans)} loans loaded | trade + comm are injected Day 9 scenarios\n")

    # 2. Select the suspicious records
    time_series_trades = [SEMANTIC_TRADE]
    suspicious_loan  = pick_suspicious_loan(loans)
    injected_comm    = SEMANTIC_COMM

    print("[*] Selected records for Day 9 semantic correlated pipeline:")
    print(f"   Trade  : {SEMANTIC_TRADE['transaction_id']} | "
          f"{SEMANTIC_TRADE['trader_id']} | {SEMANTIC_TRADE['symbol']} | "
          f"qty={SEMANTIC_TRADE['quantity']} @ ${SEMANTIC_TRADE['price']} ")
    if suspicious_loan:
        print(f"   Loan   : {suspicious_loan.get('application_id')} | "
              f"{suspicious_loan.get('applicant_id')} | "
              f"${suspicious_loan.get('loan_amount'):,.0f} | "
              f"FICO={suspicious_loan.get('risk_score')} | {suspicious_loan.get('status')}")
    print(f"   Comm   : {injected_comm['comm_id']} | "
          f"{injected_comm['sender_id']} -> {injected_comm['receiver_ids']} | "
          f"Channel={injected_comm['channel']}")
    print(f"           Content: \"{injected_comm['content'][:80]}...\"")
    print()
    print("[!] Day 9 KEY: Semantic Correlation.")
    print("    SPOUSE_001 texts about TRADER_007 & NVDA. TRADER_007 trades NVDA.")
    print("    Semantic Correlation Engine intersection expected: META-ALERT.\n")

    # 3. Build initial state
    from core.state import ComplianceState

    initial_state: ComplianceState = {
        "current_transaction":   None,
        "current_loan":          suspicious_loan,
        "current_communication": injected_comm,
        "raw_transactions":      ([suspicious_loan] if suspicious_loan else []) + time_series_trades,
        "raw_communications":    [injected_comm] if injected_comm else [],
        "active_rules":          [],
        "flagged_entities":      [],
        "alerts":                [],
        "regulatory_updates":    [],
        "escalation_status":     "NONE",
        "human_feedback":        None,
        "report_content":        None,
    }

    # 4. Build and stream the orchestrator
    print("[~] Building LangGraph orchestrator...")
    from core.orchestrator import build_orchestrator
    app = build_orchestrator()
    print("   Orchestrator compiled. Streaming execution...\n")
    print("-" * 70)

    final_state = {}
    step_count  = 0

    for step_output in app.stream(initial_state):
        step_count += 1
        node_name = list(step_output.keys())[0]
        node_data = step_output[node_name]

        print(f"\n[STEP {step_count}] >> Node: {node_name.upper()}")
        print("-" * 70)

        for key, val in node_data.items():
            if key == "alerts" and isinstance(val, list):
                print(f"  {key}: {len(val)} item(s)")
                for alert in val:
                    is_meta = "META" in alert.get("source_agent", "")
                    tag = "[META-ALERT]" if is_meta else "[alert]"
                    print(f"    {tag} {alert.get('risk_level','?')} | "
                          f"{alert.get('entity_id','?')} | "
                          f"{alert.get('alert_id','?')}")
                    if is_meta:
                        print(f"           Linked: {alert.get('linked_alert_ids', [])}")
            elif isinstance(val, list):
                print(f"  {key}: {len(val)} item(s)")
            elif isinstance(val, str) and len(val) > 120:
                print(f"  {key}: {val[:120]}...")
            elif val is not None:
                print(f"  {key}: {val}")

        for key, val in node_data.items():
            if isinstance(val, list) and key in final_state and isinstance(final_state[key], list):
                final_state[key] = final_state[key] + val
            else:
                final_state[key] = val

    print("\n" + "-" * 70)

    # Count META-ALERTs in final state
    all_alerts = final_state.get("alerts", [])
    meta_count = sum(1 for a in all_alerts if "META" in a.get("source_agent", ""))
    print(f"[OK] Pipeline complete! {step_count} nodes executed.")
    print(f"     Total alerts: {len(all_alerts)} "
          f"({len(all_alerts) - meta_count} base + {meta_count} META-ALERT(s))")

    # 5. Extract and write the report
    report = final_state.get("report_content") or ""

    if not report:
        print("[!] No report content generated. Check agent logs above.")
        return

    REPORT_OUT.write_text(report, encoding="utf-8")
    print(f"\n[REPORT] Audit report written to: {REPORT_OUT}")
    print("\n" + "=" * 70)
    print("  REPORT PREVIEW (first 1200 chars)")
    print("=" * 70)
    print(report[:1200])
    if len(report) > 1200:
        print(f"\n... [{len(report) - 1200} more characters - open compliance_report_output.md]")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
