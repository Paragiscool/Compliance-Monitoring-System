import json
import os

def generate_validation_data():
    scenarios = []

    # --- SEC SCENARIOS (Insider Trading & Off-Channel) ---
    scenarios.append({
        "scenario_id": "SEC_001",
        "expected_result": "CRITICAL",
        "description": "Spouse tips off trader via SMS before earnings call.",
        "transactions": [{"tx_id": "T1", "trader_id": "TRADER_A", "symbol": "AAPL", "action": "BUY", "qty": 5000, "price": 150.0, "timestamp": "2026-06-01T10:05:00Z"}],
        "communications": [{"msg_id": "M1", "sender_id": "SPOUSE_A", "channel": "SMS", "content": "AAPL earnings are going to crush it today. TRADER_A says buy now.", "timestamp": "2026-06-01T10:00:00Z"}]
    })

    scenarios.append({
        "scenario_id": "SEC_002",
        "expected_result": "CRITICAL",
        "description": "CEO texts board member on Signal about unannounced merger.",
        "transactions": [{"tx_id": "T2", "trader_id": "BOARD_MEM_1", "symbol": "TGT", "action": "BUY", "qty": 10000, "price": 120.0, "timestamp": "2026-06-01T11:15:00Z"}],
        "communications": [{"msg_id": "M2", "sender_id": "CEO_01", "channel": "SIGNAL", "content": "Merger with TGT is finalized. Announcing Tuesday. Off the record.", "timestamp": "2026-06-01T11:00:00Z"}]
    })

    scenarios.append({
        "scenario_id": "SEC_003",
        "expected_result": "HIGH",
        "description": "Broker guarantees 100% return on a penny stock via WhatsApp.",
        "transactions": [],
        "communications": [{"msg_id": "M3", "sender_id": "BROKER_XYZ", "channel": "WHATSAPP", "content": "I promise you a 100% guaranteed return on this OTC stock. Zero risk.", "timestamp": "2026-06-02T09:30:00Z"}]
    })

    scenarios.append({
        "scenario_id": "SEC_004",
        "expected_result": "CRITICAL",
        "description": "Trader brags on Telegram about front-running a massive client order.",
        "transactions": [
            {"tx_id": "T3", "trader_id": "TRADER_X", "symbol": "AMZN", "action": "BUY", "qty": 500, "price": 3000.0, "timestamp": "2026-06-02T13:59:00Z"},
            {"tx_id": "T4", "trader_id": "CLIENT_WHALE", "symbol": "AMZN", "action": "BUY", "qty": 50000, "price": 3005.0, "timestamp": "2026-06-02T14:00:00Z"}
        ],
        "communications": [{"msg_id": "M4", "sender_id": "TRADER_X", "channel": "TELEGRAM", "content": "Just saw a huge block order for AMZN. I'm stepping in front of it.", "timestamp": "2026-06-02T13:55:00Z"}]
    })

    scenarios.append({
        "scenario_id": "SEC_005",
        "expected_result": "HIGH",
        "description": "Employee shares inside information about a clinical trial.",
        "transactions": [],
        "communications": [{"msg_id": "M5", "sender_id": "ANALYST_01", "channel": "EMAIL", "content": "Heard from a board member that the FDA trial failed. Not public yet. Dump the stock.", "timestamp": "2026-06-03T10:00:00Z"}]
    })

    # --- FINRA SCENARIOS (Wash Trading) ---
    scenarios.append({
        "scenario_id": "FINRA_001",
        "expected_result": "CRITICAL",
        "description": "Classic wash trade: Buy and sell same asset within 3 seconds.",
        "transactions": [
            {"tx_id": "T5", "trader_id": "TRADER_B", "symbol": "TSLA", "action": "BUY", "qty": 1000, "price": 200.0, "timestamp": "2026-06-02T14:00:00Z"},
            {"tx_id": "T6", "trader_id": "TRADER_B", "symbol": "TSLA", "action": "SELL", "qty": 1000, "price": 200.0, "timestamp": "2026-06-02T14:00:03Z"}
        ],
        "communications": []
    })

    scenarios.append({
        "scenario_id": "FINRA_002",
        "expected_result": "HIGH",
        "description": "Churning: High frequency buying and selling of same mutual fund in one day.",
        "transactions": [
            {"tx_id": "T7", "trader_id": "BROKER_J", "symbol": "VFX", "action": "BUY", "qty": 500, "price": 100.0, "timestamp": "2026-06-03T10:00:00Z"},
            {"tx_id": "T8", "trader_id": "BROKER_J", "symbol": "VFX", "action": "SELL", "qty": 500, "price": 100.0, "timestamp": "2026-06-03T10:30:00Z"},
            {"tx_id": "T9", "trader_id": "BROKER_J", "symbol": "VFX", "action": "BUY", "qty": 500, "price": 100.0, "timestamp": "2026-06-03T11:00:00Z"},
            {"tx_id": "T10", "trader_id": "BROKER_J", "symbol": "VFX", "action": "SELL", "qty": 500, "price": 100.0, "timestamp": "2026-06-03T11:30:00Z"}
        ],
        "communications": []
    })

    scenarios.append({
        "scenario_id": "FINRA_003",
        "expected_result": "CRITICAL",
        "description": "Wash Trade across linked accounts (Husband buys, Wife sells instantly).",
        "transactions": [
            {"tx_id": "T11", "trader_id": "HUSBAND_01", "symbol": "GME", "action": "BUY", "qty": 2000, "price": 25.0, "timestamp": "2026-06-04T15:00:00Z"},
            {"tx_id": "T12", "trader_id": "WIFE_01", "symbol": "GME", "action": "SELL", "qty": 2000, "price": 25.0, "timestamp": "2026-06-04T15:00:02Z"}
        ],
        "communications": []
    })

    scenarios.append({
        "scenario_id": "FINRA_004",
        "expected_result": "HIGH",
        "description": "Unauthorized trading: Broker uses high-pressure sales tactics.",
        "transactions": [],
        "communications": [{"msg_id": "M6", "sender_id": "BROKER_K", "channel": "SMS", "content": "This is your last chance. Offer expires in 10 minutes. If you don't invest now you'll lose everything.", "timestamp": "2026-06-05T09:00:00Z"}]
    })

    scenarios.append({
        "scenario_id": "FINRA_005",
        "expected_result": "CRITICAL",
        "description": "Spoofing: Massive canceled order followed by execution on the other side.",
        "transactions": [
            {"tx_id": "T13", "trader_id": "SPOOFER_1", "symbol": "AMC", "action": "BUY", "qty": 100000, "price": 15.0, "timestamp": "2026-06-06T10:00:00Z", "status": "CANCELED"},
            {"tx_id": "T14", "trader_id": "SPOOFER_1", "symbol": "AMC", "action": "SELL", "qty": 5000, "price": 15.5, "timestamp": "2026-06-06T10:00:05Z"}
        ],
        "communications": []
    })

    # --- OFAC SCENARIOS (Structuring & Sanctions) ---
    scenarios.append({
        "scenario_id": "OFAC_001",
        "expected_result": "MEDIUM",
        "description": "Structuring deposits just below the $10,000 threshold.",
        "transactions": [
            {"tx_id": "T15", "trader_id": "TRADER_C", "symbol": "USD", "action": "DEPOSIT", "qty": 1, "price": 9999.0, "timestamp": "2026-06-03T09:00:00Z"},
            {"tx_id": "T16", "trader_id": "TRADER_C", "symbol": "USD", "action": "DEPOSIT", "qty": 1, "price": 9999.0, "timestamp": "2026-06-03T11:00:00Z"}
        ],
        "communications": []
    })

    scenarios.append({
        "scenario_id": "OFAC_002",
        "expected_result": "CRITICAL",
        "description": "Wire transfer initiated to an entity on the SDN list.",
        "transactions": [
            {"tx_id": "T17", "trader_id": "CUST_555", "symbol": "USD", "action": "WIRE", "qty": 1, "price": 50000.0, "timestamp": "2026-06-07T12:00:00Z", "counterparty": "SANCTIONED_ENTITY_LTD"}
        ],
        "communications": []
    })

    scenarios.append({
        "scenario_id": "OFAC_003",
        "expected_result": "HIGH",
        "description": "5 consecutive ATM withdrawals of $9,500 over 5 days.",
        "transactions": [
            {"tx_id": f"T{18+i}", "trader_id": "CUST_777", "symbol": "USD", "action": "WITHDRAWAL", "qty": 1, "price": 9500.0, "timestamp": f"2026-06-{10+i:02d}T09:00:00Z"} for i in range(5)
        ],
        "communications": []
    })

    scenarios.append({
        "scenario_id": "OFAC_004",
        "expected_result": "CRITICAL",
        "description": "Trade involving a sanctioned oligarch's known alias.",
        "transactions": [
            {"tx_id": "T23", "trader_id": "OLIGARCH_ALIAS_X", "symbol": "GOLD", "action": "BUY", "qty": 100, "price": 2000.0, "timestamp": "2026-06-15T14:00:00Z"}
        ],
        "communications": []
    })

    scenarios.append({
        "scenario_id": "OFAC_005",
        "expected_result": "HIGH",
        "description": "Suspicious unverified loan approval.",
        "transactions": [
            {"tx_id": "LOAN_001", "entity_id": "CUST_999", "type": "LOAN_ORIGINATION", "amount": 5000000.0, "status": "APPROVED", "risk_factors": {"fico_score": 500, "employment": "UNVERIFIED"}, "timestamp": "2026-06-16T11:00:00"}
        ],
        "communications": []
    })

    # --- CONTROL SCENARIOS (Clean Data for False Positives) ---
    scenarios.append({
        "scenario_id": "CLEAN_001",
        "expected_result": "CLEAN",
        "description": "Normal, legal market making activity and routine email.",
        "transactions": [{"tx_id": "T24", "trader_id": "TRADER_D", "symbol": "MSFT", "action": "BUY", "qty": 100, "price": 400.0, "timestamp": "2026-06-04T12:00:00Z"}],
        "communications": [{"msg_id": "M7", "sender_id": "TRADER_D", "channel": "EMAIL", "content": "Let's grab lunch at 12:30 after the morning meetings.", "timestamp": "2026-06-04T11:45:00Z"}]
    })

    scenarios.append({
        "scenario_id": "CLEAN_002",
        "expected_result": "CLEAN",
        "description": "Standard payroll deposit and vacation email.",
        "transactions": [{"tx_id": "T25", "trader_id": "EMP_005", "symbol": "USD", "action": "DEPOSIT", "qty": 1, "price": 4500.0, "timestamp": "2026-06-15T08:00:00Z"}],
        "communications": [{"msg_id": "M8", "sender_id": "EMP_005", "channel": "EMAIL", "content": "I will be on vacation next week. Please contact HR for urgent issues.", "timestamp": "2026-06-15T09:00:00Z"}]
    })

    scenarios.append({
        "scenario_id": "CLEAN_003",
        "expected_result": "CLEAN",
        "description": "Client buys index fund and holds.",
        "transactions": [{"tx_id": "T26", "trader_id": "CLIENT_RETAIL", "symbol": "SPY", "action": "BUY", "qty": 10, "price": 500.0, "timestamp": "2026-06-20T10:00:00Z"}],
        "communications": []
    })

    scenarios.append({
        "scenario_id": "CLEAN_004",
        "expected_result": "CLEAN",
        "description": "False Positive trigger word test: 'guaranteed' delivery.",
        "transactions": [],
        "communications": [{"msg_id": "M9", "sender_id": "VENDOR_MGR", "channel": "EMAIL", "content": "The vendor guaranteed the server delivery by Friday morning. No risk of delay.", "timestamp": "2026-06-21T14:00:00Z"}]
    })

    scenarios.append({
        "scenario_id": "CLEAN_005",
        "expected_result": "CLEAN",
        "description": "False Positive trigger word test: 'inside information' joke.",
        "transactions": [],
        "communications": [{"msg_id": "M10", "sender_id": "DEV_TEAM", "channel": "SLACK", "content": "I have inside information that there are donuts in the breakroom right now.", "timestamp": "2026-06-22T09:15:00Z"}]
    })

    os.makedirs("data", exist_ok=True)
    with open("data/validation_suite.json", "w") as f:
        json.dump(scenarios, f, indent=4)
    print(f"Validation suite generated at data/validation_suite.json with {len(scenarios)} scenarios.")

if __name__ == "__main__":
    generate_validation_data()
