import streamlit as st
import json
from core.orchestrator import app as graph_app

st.set_page_config(page_title="Compliance HITL", layout="wide")
st.title("🛡️ Compliance Officer Dashboard")

# --- SIDEBAR: Case Management & Controls ---
with st.sidebar:
    st.header("Case Management")
    # Allow the user to define their own Thread ID
    case_id = st.text_input("Investigation Case ID", value="case_001")
    
    # Update the session state configuration dynamically
    if "active_threads" not in st.session_state:
        st.session_state.active_threads = {}
    
    if case_id not in st.session_state.active_threads:
        st.session_state.active_threads[case_id] = case_id
        
    st.session_state.thread_config = {"configurable": {"thread_id": st.session_state.active_threads[case_id]}}
    
    st.divider()
    st.header("System Controls")
    run_scan = st.button("▶️ Run Surveillance Scan")
    
# --- LOGIC: Fetch Data & Run Scan ---
def load_mock_data():
    with open("data/mock_transactions.json", "r") as f:
        transactions = json.load(f)
    with open("data/mock_communications.json", "r") as f:
        communications = json.load(f)
    return transactions, communications

if run_scan:
    # Check if the thread already has state (meaning it was run before)
    _current_state = graph_app.get_state(st.session_state.thread_config)
    if _current_state and _current_state.values.get("alerts"):
        import time
        new_thread = f"{case_id}_run_{int(time.time())}"
        st.session_state.active_threads[case_id] = new_thread
        st.session_state.thread_config = {"configurable": {"thread_id": new_thread}}

    with st.spinner(f"Agents are scanning ledgers for {case_id}..."):
        transactions, communications = load_mock_data()
        
        initial_state = {
            "raw_transactions": transactions,
            "raw_communications": communications,
            "active_regulatory_rules": [],
            "alerts": [],
            "requires_human_review": False,
            "human_decision": "",
            "final_audit_report": ""
        }
        
        # Run the graph. It will save the state to SQLite under the provided case_id
        graph_app.invoke(initial_state, config=st.session_state.thread_config)
        st.success(f"Scan Complete! {case_id} is awaiting Human Review.")

# --- MAIN DISPLAY: Resume & Review ---
st.subheader(f"Active Alerts: {case_id}")

# This will natively query the SQLite database for the state of the active Case ID!
current_state = graph_app.get_state(st.session_state.thread_config)

if current_state and current_state.values:
    alerts = current_state.values.get("alerts", [])
    
    if not alerts:
        st.info("No alerts generated yet. Click 'Run Surveillance Scan' to begin.")
    else:
        # Display the alerts in a clean format
        for alert in alerts:
            # Highlight META-ALERTs from the Correlation Engine
            if alert.get("risk_level", "LOW") == "CRITICAL":
                st.error(f"🚨 **{alert.get('risk_level')} ALERT** - {alert.get('source_agent')}\n\n**Entities:** {', '.join(alert.get('entities_involved', []))}\n\n{alert.get('reason')}")
            else:
                st.warning(f"⚠️ **{alert.get('risk_level')} ALERT** - {alert.get('source_agent')}\n\n**Entities:** {', '.join(alert.get('entities_involved', []))}\n\n{alert.get('reason')}")

        # Check if the graph is paused waiting for HITL
        if current_state.next and "report_generator" in current_state.next:
            st.divider()
            st.subheader("Human-In-The-Loop Review")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Approve & Generate Report", use_container_width=True):
                    with st.spinner("Resuming graph and generating report..."):
                        # Update the state to reflect human approval
                        graph_app.update_state(
                            st.session_state.thread_config,
                            {"human_feedback": "APPROVED"},
                            as_node="hitl_placeholder"
                        )
                        # Resume the graph
                        graph_app.invoke(None, config=st.session_state.thread_config)
                        st.rerun()
                        
            with col2:
                reject_reason = st.text_input("Reason for Rejection (Required):", placeholder="e.g., Known corporate transfer...")
                if st.button("❌ Reject & Teach AI", type="secondary", use_container_width=True):
                    if not reject_reason:
                        st.error("You must provide a reason so the AI can learn from this false positive.")
                    else:
                        with st.spinner("Dismissing alerts and teaching AI..."):
                            # 1. Save the context and reason to ChromaDB
                            import uuid
                            from agent.regulatory_tracker import get_false_positives_db
                            db = get_false_positives_db()
                            if db is not None:
                                for alert in alerts:
                                    context = f"Alert Reason: {alert.get('reason')}"
                                    metadata = {"human_reason": reject_reason, "source_agent": alert.get("source_agent")}
                                    db.add_texts(
                                        texts=[f"{context} | Human Rejection Reason: {reject_reason}"],
                                        metadatas=[metadata],
                                        ids=[f"FP_{uuid.uuid4().hex[:8]}"]
                                    )
                            
                            # 2. Update the state to reflect rejection
                            graph_app.update_state(
                                st.session_state.thread_config,
                                {"human_feedback": f"REJECTED: {reject_reason}"},
                                as_node="hitl_placeholder"
                            )
                            # Resume the graph
                            graph_app.invoke(None, config=st.session_state.thread_config)
                            st.rerun()
                        
        # Display the final report if it exists and graph is finished
        final_report = current_state.values.get("report_content")
        if final_report and not current_state.next:
            st.divider()
            st.subheader("Final Audit Report")
            st.markdown(final_report)
