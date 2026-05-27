import uuid
import os
import json
from datetime import datetime
from typing import Dict, Any, List

from dotenv import load_dotenv
from tenacity import RetryError
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from core.models import Alert, AlertList
from core.state import ComplianceState

load_dotenv()

_GOOGLE_KEY_PRESENT = (
    bool(os.getenv("GOOGLE_API_KEY"))
    and os.getenv("GOOGLE_API_KEY") != "your_google_api_key_here"
)

def get_communication_scanner_node():
    """
    Factory that returns the Communication Scanner LangGraph node.
    Upgraded to a ReAct Agent (Day 10 Interactivity).
    """
    
    def communication_scanner_node(state: ComplianceState) -> Dict[str, Any]:
        print("--- AGENT 3: COMMUNICATION SCANNER (Tool-Enhanced) ---")
        
        communications = state.get("raw_communications", [])
        transactions = state.get("raw_transactions", [])
        rules = state.get("active_rules", [])
        
        if not communications:
            print("INFO [CommScanner]: No raw communications in state. Skipping.")
            return {"alerts": []}

        if not _GOOGLE_KEY_PRESENT:
            print("WARNING [CommScanner]: No Google API Key. Returning empty alerts.")
            return {"alerts": []}

        # 1. Equip the Agent with a Tool to query the other silo
        @tool
        def query_transactions(ticker: str) -> str:
            """Use this tool to search the transaction ledger for recent trades involving a specific ticker symbol (e.g., 'NVDA', 'TSLA')."""
            matches = [tx for tx in transactions if tx.get("symbol") == ticker]
            print(f"  > INFO [CommScanner Tool]: query_transactions called with ticker='{ticker}'. Found {len(matches)} match(es).")
            if not matches:
                return f"No recent transactions found for {ticker}."
            return json.dumps(matches)

        # Initialize Gemini
        llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0)
        
        # 2. First Pass: Bind the tool so Gemini can reason and search
        llm_with_tools = llm.bind_tools([query_transactions])
        
        # Query ChromaDB for negative constraints
        negative_constraints = ""
        try:
            from agent.regulatory_tracker import get_false_positives_db, _similarity_search_with_retry
            db = get_false_positives_db()
            if db:
                from collections import defaultdict
                grouped_comms = defaultdict(list)
                for c in communications:
                    grouped_comms[c.get("sender_id", "UNKNOWN")].append(c)

                for sender_id, comm_list in grouped_comms.items():
                    comm_str = json.dumps(comm_list)
                    try:
                        docs = _similarity_search_with_retry(db, comm_str, k=1)
                    except RetryError as re:
                        print(f"WARNING [CommScanner]: similarity_search exhausted retries for {sender_id}: {re.last_attempt.exception()}")
                        docs = []
                    for d in docs:
                        reason = d.metadata.get("human_reason", "")
                        negative_constraints += f"Warning for {sender_id}: A human previously rejected a similar case because '{reason}'. Consider downgrading the severity.\n"
        except Exception as e:
            print(f"WARNING [CommScanner]: Failed to query false_positives ChromaDB: {e}")

        system_prompt = f"""You are a Tier-2 Bank Communication Surveillance AI.
Review the following employee communications against these rules:
{json.dumps([r for r in rules])}

CRITICAL INSTRUCTION: If an employee mentions a specific stock ticker or asset, 
you MUST use the `query_transactions` tool to check if a correlating trade occurred. 
If a trade corroborates a suspicious message, elevate the risk to CRITICAL and mention the trade in your reason.
Set entity_id to the exact sender_id from the communication data.
Populate entities_involved with the sender_id AND all receiver_ids found in the communication.
Set linked_alert_ids to an empty list [].

Negative Constraints:
{negative_constraints}
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Communications to review:\n{json.dumps(communications)}")
        ]

        # Let the agent think and potentially call the tool
        try:
            print("INFO [CommScanner]: Analyzing communications and reasoning...")
            ai_msg = llm_with_tools.invoke(messages)
            messages.append(ai_msg)

            # 3. Execute the tool if the agent requested it
            if ai_msg.tool_calls:
                for tool_call in ai_msg.tool_calls:
                    # Execute the python function
                    tool_output = query_transactions.invoke(tool_call["args"])
                    # Append the tool's response back to the conversation history
                    messages.append(ToolMessage(content=tool_output, tool_call_id=tool_call["id"]))
                
                # Give the LLM one more chance to reason now that it has the tool's data
                print("INFO [CommScanner]: Tool executed. Re-evaluating with new data...")
                ai_msg = llm_with_tools.invoke(messages)
                messages.append(ai_msg)

            # 4. Final Pass: Force the finalized reasoning into our strict Pydantic JSON schema
            structured_llm = llm.with_structured_output(AlertList)
            final_output = structured_llm.invoke(messages)

            new_alerts = []
            if final_output and hasattr(final_output, 'alerts'):
                for alert in final_output.alerts:
                    # Make sure alert has an ID and correctly set source agent
                    if not alert.alert_id or alert.alert_id.startswith("META"):
                        alert.alert_id = f"ALERT_COMM_{uuid.uuid4().hex[:8].upper()}"
                    alert.source_agent = "Communication Scanner (Tool-Enhanced)"
                    new_alerts.append(alert.to_state_dict())

            print(f"INFO [CommScanner]: Generated {len(new_alerts)} alert(s).")
            return {"alerts": new_alerts}
            
        except Exception as e:
            print(f"ERROR [CommScanner]: LLM agent loop failed: {e}")
            return {"alerts": []}

    return communication_scanner_node
