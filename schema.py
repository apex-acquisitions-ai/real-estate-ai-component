from pydantic import BaseModel, Field
from typing import List, Optional

class PropertySummary(BaseModel):
    address: str
    sqft: int
    asking_price: float
    estimated_arv: float

class UnderwritingMetrics(BaseModel):
    rehab_tier: str = Field(description="Cosmetic, Standard, or Full Gut")
    rehab_cost_per_sqft: float
    total_estimated_rehab: float
    target_wholesale_fee: float
    max_allowable_offer_mao: float
    deal_spread: float
    is_viable_deal: bool

class OutreachAssets(BaseModel):
    suggested_opening_offer: float
    seller_sms_script: str
    seller_email_script: str

class DealEvaluationResponse(BaseModel):
    status: str = Field(description="SUCCESS, INCOMPLETE_DATA, or HIGH_RISK_DEAL")
    property_summary: PropertySummary
    underwriting_metrics: UnderwritingMetrics
    outreach_assets: OutreachAssets
    audit_flags: Optional[List[str]] = []

