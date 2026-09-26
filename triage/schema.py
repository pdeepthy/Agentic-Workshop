"""The shape of one triage decision, as set by TRIAGE_POLICY.md."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

Category = Literal["billing", "bug", "access", "performance", "how-to"]
Priority = Literal["P1", "P2", "P3", "P4"]
Route = Literal["billing-team", "bug-team", "access-team", "performance-team", "how-to-team"]

ROUTE_FOR_CATEGORY: dict[Category, Route] = {
    "billing": "billing-team",
    "bug": "bug-team",
    "access": "access-team",
    "performance": "performance-team",
    "how-to": "how-to-team",
}

# A sentence end followed by more text, or a capital with no space between, means a second sentence.
_SENTENCE_BREAK = re.compile(r"[.!?]['\")\]]*(\s+\S|[A-Z])")
_CLOSERS = "'\")]"


class TriageDecision(BaseModel):
    """A category, a priority, the category's route and a one-sentence rationale. Nothing else."""

    model_config = ConfigDict(extra="forbid", strict=True)

    # category must stay declared before route: the route check reads it.
    category: Category
    priority: Priority
    route: Route = Field(description="The team TRIAGE_POLICY.md pairs with the category, e.g. billing-team for billing.")
    rationale: str = Field(description="Exactly one sentence that names the policy rule applied.")

    @field_validator("route")
    @classmethod
    def route_matches_category(cls, route: str, info: ValidationInfo) -> str:
        category = info.data.get("category")
        if category is not None and route != ROUTE_FOR_CATEGORY[category]:
            raise ValueError(f"route for category {category!r} must be {ROUTE_FOR_CATEGORY[category]!r}, not {route!r}")
        return route

    @field_validator("rationale")
    @classmethod
    def rationale_is_one_sentence(cls, rationale: str) -> str:
        text = rationale.strip()
        if not any(c.isalnum() for c in text):
            raise ValueError("rationale must be a sentence with words in it, not empty")
        if "\n" in text:
            raise ValueError("rationale must be exactly one sentence on one line")
        if text.rstrip(_CLOSERS)[-1:] not in (".", "!", "?"):
            raise ValueError("rationale must be one sentence ending in '.', '!' or '?'")
        if _SENTENCE_BREAK.search(text):
            raise ValueError("rationale must be exactly one sentence")
        return text


def validate_decision(data: dict | str | bytes) -> TriageDecision:
    """Validate a decision given as a dict or a JSON string. Raises pydantic.ValidationError naming the bad field."""
    if isinstance(data, (str, bytes)):
        return TriageDecision.model_validate_json(data)
    return TriageDecision.model_validate(data)
