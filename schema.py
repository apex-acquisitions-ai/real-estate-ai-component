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


class SEOKeywordOpportunity(BaseModel):
    keyword: str
    search_volume: int
    keyword_difficulty: int = Field(description="Difficulty rating 0 to 100")
    cpc: float
    intent: str
    strategic_value: str = Field(description="Why this is a high-value term to target")

class LandingPageIdea(BaseModel):
    title: str
    slug: str
    target_keyword: str
    main_cta: str = Field(description="Primary lead magnet or call to action")
    suggested_structure: List[str] = Field(description="Structural sections of the landing page")

class BlogTopic(BaseModel):
    title: str
    target_keyword: str
    primary_intent: str
    key_talking_points: List[str]
    lead_magnet: str

class BacklinkCampaignIdea(BaseModel):
    domain: str = Field(description="The source referring domain or category (e.g. rentcast.io, biggerpockets.com)")
    authority_score: int = Field(description="Domain authority score from the backlink data (e.g. 70, 51)")
    strategic_angle: str = Field(description="Campaign angle to secure a backlink (e.g. affiliate partnership, calculator embed)")
    anchor_text_suggestion: str = Field(description="Optimal anchor text linking back to our platform")

class SEOStrategyResponse(BaseModel):
    executive_summary: str = Field(description="Overview of the organic SEO opportunity based on competitor data")
    top_keyword_opportunities: List[SEOKeywordOpportunity]
    suggested_landing_pages: List[LandingPageIdea]
    suggested_blog_topics: List[BlogTopic]
    suggested_backlink_campaigns: List[BacklinkCampaignIdea]

