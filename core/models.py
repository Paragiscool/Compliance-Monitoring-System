from pydantic import BaseModel, Field
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
    """
    alert_id: str
    source_agent: str
    entity_id: str
    entity_type: str = Field(..., description="e.g., TRADER, APPLICANT, COMMUNICATION")
    risk_level: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    reason: str
    # Accept ISO strings OR datetime objects — agents emit strings, Pydantic accepts either
    timestamp: Union[datetime, str]

    def to_state_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict safe for the LangGraph state (all values JSON-serialisable)."""
        data = self.model_dump()
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        return data
