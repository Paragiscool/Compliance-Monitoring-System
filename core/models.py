from pydantic.v1 import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime


class TradeTransaction(BaseModel):
    transaction_id: str
    trader_id: str
    symbol: str
    quantity: float
    price: float
    timestamp: Union[datetime, str]
    order_type: str = Field(..., description="e.g., MARKET, LIMIT")
    asset_class: str = Field(..., description="e.g., EQUITY, FIXED_INCOME, CRYPTO")


class LoanApplication(BaseModel):
    application_id: str
    applicant_id: str
    loan_amount: float
    interest_rate: float
    purpose: str
    risk_score: int
    status: str
    timestamp: Union[datetime, str]


class Communication(BaseModel):
    comm_id: str
    sender_id: str
    receiver_ids: List[str]
    channel: str = Field(..., description="e.g., EMAIL, CHAT, WHATSAPP")
    timestamp: Union[datetime, str]
    content: str


class RegulatoryRule(BaseModel):
    rule_id: str
    jurisdiction: str = Field(..., description="e.g., SEC, FCA, FINRA, OFAC")
    description: str
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value pairs defining strict thresholds if applicable"
    )
    # effective_date is optional so we can create rules without it (e.g., from RAG retrieval)
    effective_date: Optional[Union[datetime, str]] = None


class Alert(BaseModel):
    """
    Canonical alert model used by all agents.
    All fields that the LLM must populate are kept simple (str) to avoid
    serialisation mismatches when converting to/from state dicts.

    Day 9 additions:
      entities_involved  — all entity IDs implicated by this alert
                           (enables cross-agent entity matching in the Correlation Engine)
      linked_alert_ids   — for META-ALERTs only: the original alert IDs that were correlated
    """
    alert_id: str
    source_agent: str
    entity_id: str
    entity_type: str = Field(..., description="e.g., TRADER, APPLICANT, COMMUNICATION, CORRELATED_ENTITY")
    risk_level: str  = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    reason: str
    # Accept ISO strings OR datetime objects — agents emit strings, Pydantic accepts either
    timestamp: Union[datetime, str]

    # ── Day 9: Correlation Engine fields ─────────────────────────────────────
    entities_involved: List[str] = Field(
        default_factory=list,
        description="All entity IDs implicated by this alert (e.g., trader, employee, client). "
                    "Used by the Correlation Engine to detect multi-channel violations.",
    )
    linked_alert_ids: List[str] = Field(
        default_factory=list,
        description="For META-ALERTs: the original alert_ids that were correlated. Empty for regular alerts.",
    )

    def to_state_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict safe for the LangGraph state (all values JSON-serialisable)."""
        data = self.dict()
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        return data


class AlertList(BaseModel):
    """Wrapper so Gemini with_structured_output can return a list of Alert objects."""
    alerts: List[Alert] = Field(..., description="List of compliance alerts. Can be empty if no violations are found.")

