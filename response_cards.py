from pydantic import BaseModel
from typing import List, Optional


class ClaimStatusCard(BaseModel):
    claim_id: str
    member_id: str
    status: str
    date_filed: str
    amount: Optional[float] = None
    notes: Optional[str] = None

    def to_markdown(self) -> str:
        lines = [
            "**Claim " + self.claim_id + "** - " + self.status,
            "- Member: " + self.member_id,
            "- Filed: " + self.date_filed,
        ]
        if self.amount is not None:
            lines.append("- Amount: USD " + format(self.amount, ",.2f"))
        if self.notes:
            lines.append("- Notes: " + self.notes)
        return "\n".join(lines)


class CoverageSummaryCard(BaseModel):
    plan_name: str
    tier: str
    monthly_premium: float
    covered_services: List[str]
    citations: List[str] = []

    def to_markdown(self) -> str:
        services = ", ".join(self.covered_services) if self.covered_services else "N/A"
        lines = [
            "**" + self.plan_name + "** (" + self.tier + ")",
            "- Monthly premium: USD " + format(self.monthly_premium, ",.2f"),
            "- Covered services: " + services,
        ]
        if self.citations:
            lines.append("- Sources: " + ", ".join(self.citations))
        return "\n".join(lines)
