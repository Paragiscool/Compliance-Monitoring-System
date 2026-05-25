from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator

class ComplianceState(TypedDict):
    """
    Global state for the Compliance Monitoring LangGraph.
    This state object is passed between the different agents in the graph.
    """
    # Raw Data Context
    current_transaction: Optional[Dict[str, Any]]
    current_loan: Optional[Dict[str, Any]]
    current_communication: Optional[Dict[str, Any]]
    raw_transactions: List[Dict[str, Any]]
    raw_communications: List[Dict[str, Any]]
    
    # Agent Outputs
    active_rules: List[Dict[str, Any]]
    
    # We use Annotated with operator.add to append items to the list across nodes
    flagged_entities: Annotated[List[str], operator.add]
    alerts: Annotated[List[Dict[str, Any]], operator.add]
    
    # Regulatory context
    regulatory_updates: List[Dict[str, Any]]
    
    # Escalation and Resolution
    escalation_status: str # e.g., "NONE", "PENDING_REVIEW", "ESCALATED", "RESOLVED"
    human_feedback: Optional[str]
    
    # Reporting
    report_content: Optional[str]
