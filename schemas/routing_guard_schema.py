from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# INPUT SCHEMA
# ============================================================

class RoutingGuardInput(BaseModel):
    """
    Generic input schema for the Supervisor Dispatch Guard.

    This schema is intentionally tool-agnostic.
    It can be used by OCR tools, thickness analyzers,
    engineering calculators, flaw detectors, etc.
    """

    tool_name: str = Field(
        ...,
        min_length=1,
        description="Name of the tool or pipeline stage requesting dispatch."
    )

    status: str = Field(
        ...,
        min_length=1,
        description="Current status of the tool or pipeline stage."
    )

    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0."
    )

    requires_human_confirmation: bool = Field(
        default=False,
        description="Whether the upstream process explicitly requires human confirmation."
    )

    critical_safety_breach: bool = Field(
        default=False,
        description="Whether a critical safety condition has been detected."
    )

    allow_human_override: bool = Field(
        default=False,
        description="Whether the human engineer is allowed to correct parameters and rerun."
    )

    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters or extracted values associated with the current operation."
    )

    reason: Optional[str] = Field(
        default=None,
        description="Explanation for the current status or human-review requirement."
    )

    confidence_threshold: float = Field(
        default=0.85,
        gt=0.0,
        le=1.0,
        description="Minimum confidence required for automatic dispatch."
    )


# ============================================================
# HUMAN GATE ACTION
# ============================================================

class HumanGateAction(BaseModel):
    """
    Represents an action available to the human engineer.
    """

    action: str = Field(
        ...,
        description="Available human action."
    )

    description: str = Field(
        ...,
        description="Explanation of the action."
    )


# ============================================================
# OUTPUT SCHEMA
# ============================================================

class RoutingGuardOutput(BaseModel):
    """
    Output schema for the Supervisor Dispatch Guard.
    """

    routing_verdict: str = Field(
        ...,
        description="Final routing decision made by the guard."
    )

    dispatch_allowed: bool = Field(
        ...,
        description="Whether downstream automated execution is allowed."
    )

    human_confirmation_required: bool = Field(
        ...,
        description="Whether human engineer confirmation is required."
    )

    human_override_allowed: bool = Field(
        ...,
        description="Whether the engineer may correct parameters and rerun."
    )

    tool_name: str = Field(
        ...,
        description="Tool that requested dispatch."
    )

    confidence: Optional[float] = Field(
        default=None,
        description="Confidence score received from the upstream process."
    )

    confidence_threshold: float = Field(
        ...,
        description="Confidence threshold used by the guard."
    )

    critical_safety_breach: bool = Field(
        ...,
        description="Whether a critical safety breach was detected."
    )

    reason: str = Field(
        ...,
        description="Reason for the routing decision."
    )

    allowed_actions: List[HumanGateAction] = Field(
        default_factory=list,
        description="Actions available to the human engineer."
    )