import json
import random
import os
from datetime import datetime, timedelta
import uuid

# Directories
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'mock')
os.makedirs(DATA_DIR, exist_ok=True)

# Helper functions
def random_date(start_days_ago=30):
    start_date = datetime.now() - timedelta(days=start_days_ago)
    random_days = random.randrange(start_days_ago)
    return (start_date + timedelta(days=random_days)).isoformat()

def generate_trades(num_trades=50):
    symbols = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'AMZN', 'GME', 'AMC']
    traders = [f"TRADER_{i:03d}" for i in range(1, 11)]
    trades = []
    
    for _ in range(num_trades):
        trade = {
            "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
            "trader_id": random.choice(traders),
            "symbol": random.choice(symbols),
            "quantity": round(random.uniform(10, 1000), 2),
            "price": round(random.uniform(50, 500), 2),
            "timestamp": random_date(),
            "order_type": random.choice(["MARKET", "LIMIT"]),
            "asset_class": "EQUITY"
        }
        trades.append(trade)
    
    # Inject a wash trading scenario for TRADER_007 (same trader buying and selling same stock quickly)
    suspicious_symbol = "TSLA"
    wash_time = datetime.now() - timedelta(days=2)
    trades.extend([
        {
            "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
            "trader_id": "TRADER_007",
            "symbol": suspicious_symbol,
            "quantity": 500.0,
            "price": 200.0,
            "timestamp": wash_time.isoformat(),
            "order_type": "MARKET",
            "asset_class": "EQUITY"
        },
        {
            "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
            "trader_id": "TRADER_007",
            "symbol": suspicious_symbol,
            "quantity": -500.0, # Sell
            "price": 200.5,
            "timestamp": (wash_time + timedelta(seconds=5)).isoformat(),
            "order_type": "MARKET",
            "asset_class": "EQUITY"
        }
    ])
    
    with open(os.path.join(DATA_DIR, 'trades.json'), 'w') as f:
        json.dump(trades, f, indent=4)
    print(f"Generated {len(trades)} mock trades.")

def generate_loans(num_loans=20):
    applicants = [f"CUST_{i:04d}" for i in range(1, 21)]
    purposes = ["MORTGAGE", "BUSINESS", "PERSONAL", "AUTO", "REAL_ESTATE_INVESTMENT"]
    loans = []
    
    for i in range(num_loans):
        loan = {
            "application_id": f"LOAN_{uuid.uuid4().hex[:8]}",
            "applicant_id": applicants[i],
            "loan_amount": round(random.uniform(10000, 500000), 2),
            "interest_rate": round(random.uniform(3.5, 12.0), 2),
            "purpose": random.choice(purposes),
            "risk_score": random.randint(300, 850), # e.g. FICO
            "status": random.choice(["PENDING", "APPROVED", "REJECTED"]),
            "timestamp": random_date()
        }
        loans.append(loan)
        
    # Inject a suspicious loan (high amount, low risk score, business purpose)
    loans.append({
        "application_id": f"LOAN_{uuid.uuid4().hex[:8]}",
        "applicant_id": "CUST_9999",
        "loan_amount": 2500000.0,
        "interest_rate": 2.5, # Suspiciously low
        "purpose": "BUSINESS",
        "risk_score": 450, # Suspiciously low for approval
        "status": "APPROVED",
        "timestamp": random_date()
    })
    
    with open(os.path.join(DATA_DIR, 'loans.json'), 'w') as f:
        json.dump(loans, f, indent=4)
    print(f"Generated {len(loans)} mock loan applications.")

def generate_communications(num_comms=30):
    employees = [f"EMP_{i:03d}" for i in range(1, 15)]
    clients = [f"CLIENT_{i:03d}" for i in range(1, 20)]
    
    normal_messages = [
        "Can we schedule a call to discuss the portfolio?",
        "Please find the attached Q3 performance report.",
        "I need to update my address on file.",
        "What are your thoughts on the current market trends?",
        "Thank you for the update."
    ]
    
    suspicious_messages = [
        # Unauthorized Guarantee
        "I can guarantee a 15% return by next quarter if you invest now.",
        "There's absolutely no risk with this product, it's a sure thing.",
        # Insider Trading hint
        "I heard from a friend at the board that they are acquiring TechCorp next week. We should buy.",
        # High-pressure sales
        "If you don't sign today, the offer is gone forever. You're going to lose everything."
    ]
    
    comms = []
    
    for _ in range(num_comms):
        sender = random.choice(employees)
        receiver = random.choice(clients)
        comms.append({
            "comm_id": f"MSG_{uuid.uuid4().hex[:8]}",
            "sender_id": sender,
            "receiver_ids": [receiver],
            "channel": random.choice(["EMAIL", "CHAT"]),
            "timestamp": random_date(),
            "content": random.choice(normal_messages)
        })
        
    # Inject suspicious communications
    for msg in suspicious_messages:
        comms.append({
            "comm_id": f"MSG_{uuid.uuid4().hex[:8]}",
            "sender_id": random.choice(employees),
            "receiver_ids": [random.choice(clients)],
            "channel": random.choice(["EMAIL", "WHATSAPP"]),
            "timestamp": random_date(start_days_ago=5),
            "content": msg
        })
        
    with open(os.path.join(DATA_DIR, 'communications.json'), 'w') as f:
        json.dump(comms, f, indent=4)
    print(f"Generated {len(comms)} mock communications.")

if __name__ == "__main__":
    print("Generating Mock Data...")
    generate_trades()
    generate_loans()
    generate_communications()
    print(f"Data generation complete. Check {DATA_DIR}")
