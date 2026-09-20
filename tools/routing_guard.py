from schemas.routing_guard_schema import (
    RoutingGuardInput,
    RoutingGuardOutput,
    HumanGateAction,
)


# ============================================================
# CONSTANTS
# ============================================================

CONFIRM_UNEDITED = "CONFIRM_UNEDITED"
CORRECT_AND_RERUN = "CORRECT_AND_RERUN"
REJECT_AND_HALT = "REJECT_AND_HALT"


# ============================================================
# MAIN SUPERVISOR DISPATCH GUARD
# ============================================================

def supervisor_dispatch_guard(
    input_data: RoutingGuardInput,
) -> RoutingGuardOutput:
    """
    Generic Supervisor Dispatch Guard.

    This tool determines whether a pipeline operation can
    continue automatically or requires human intervention.

    It is intentionally independent of any specific tool.

    It can protect:

    - OCR extraction
    - UT thickness analysis
    - Engineering calculations
    - Corrosion analysis
    - Flaw detection
    - Remaining-life calculations
    - Other high-risk inspection operations
    """

    # ========================================================
    # 1. CRITICAL SAFETY BREACH
    # ========================================================

    if input_data.critical_safety_breach:

        actions = [
            HumanGateAction(
                action=REJECT_AND_HALT,
                description=(
                    "Reject the operation and halt the pipeline "
                    "because a critical safety breach was detected."
                ),
            )
        ]

        if input_data.allow_human_override:

            actions.append(
                HumanGateAction(
                    action=CORRECT_AND_RERUN,
                    description=(
                        "Correct the underlying parameters or issue "
                        "and rerun the operation after engineering review."
                    ),
                )
            )

        return RoutingGuardOutput(

            routing_verdict="DISPATCH_BLOCKED_CRITICAL_SAFETY_BREACH",

            dispatch_allowed=False,

            human_confirmation_required=True,

            human_override_allowed=(
                input_data.allow_human_override
            ),

            tool_name=input_data.tool_name,

            confidence=input_data.confidence,

            confidence_threshold=(
                input_data.confidence_threshold
            ),

            critical_safety_breach=True,

            reason=(
                "A critical safety breach was detected. "
                "Automated dispatch is blocked."
            ),

            allowed_actions=actions,
        )

    # ========================================================
    # 2. EXPLICIT HUMAN CONFIRMATION REQUIRED
    # ========================================================

    if input_data.requires_human_confirmation:

        actions = [
            HumanGateAction(
                action=CONFIRM_UNEDITED,
                description=(
                    "Confirm that the extracted or calculated "
                    "parameters are correct without modification."
                ),
            ),
            HumanGateAction(
                action=REJECT_AND_HALT,
                description=(
                    "Reject the operation and halt the pipeline."
                ),
            ),
        ]

        if input_data.allow_human_override:

            actions.insert(
                1,
                HumanGateAction(
                    action=CORRECT_AND_RERUN,
                    description=(
                        "Correct inaccurate parameters and rerun "
                        "the operation."
                    ),
                ),
            )

        return RoutingGuardOutput(

            routing_verdict=(
                "DISPATCH_BLOCKED_AWAITING_HUMAN_CONFIRMATION"
            ),

            dispatch_allowed=False,

            human_confirmation_required=True,

            human_override_allowed=(
                input_data.allow_human_override
            ),

            tool_name=input_data.tool_name,

            confidence=input_data.confidence,

            confidence_threshold=(
                input_data.confidence_threshold
            ),

            critical_safety_breach=False,

            reason=(
                input_data.reason
                or "Human confirmation is required before dispatch."
            ),

            allowed_actions=actions,
        )

    # ========================================================
    # 3. LOW CONFIDENCE
    # ========================================================

    if (
        input_data.confidence is not None
        and input_data.confidence
        < input_data.confidence_threshold
    ):

        actions = [
            HumanGateAction(
                action=CONFIRM_UNEDITED,
                description=(
                    "Review the low-confidence result and "
                    "confirm that the parameters are correct."
                ),
            ),
            HumanGateAction(
                action=REJECT_AND_HALT,
                description=(
                    "Reject the low-confidence result and "
                    "halt the pipeline."
                ),
            ),
        ]

        if input_data.allow_human_override:

            actions.insert(
                1,
                HumanGateAction(
                    action=CORRECT_AND_RERUN,
                    description=(
                        "Correct inaccurate parameters and rerun "
                        "the operation."
                    ),
                ),
            )

        return RoutingGuardOutput(

            routing_verdict=(
                "DISPATCH_BLOCKED_LOW_CONFIDENCE"
            ),

            dispatch_allowed=False,

            human_confirmation_required=True,

            human_override_allowed=(
                input_data.allow_human_override
            ),

            tool_name=input_data.tool_name,

            confidence=input_data.confidence,

            confidence_threshold=(
                input_data.confidence_threshold
            ),

            critical_safety_breach=False,

            reason=(
                f"Confidence score "
                f"{input_data.confidence:.2f} is below "
                f"the required threshold "
                f"{input_data.confidence_threshold:.2f}."
            ),

            allowed_actions=actions,
        )

    # ========================================================
    # 4. EVERYTHING IS SAFE TO DISPATCH
    # ========================================================

    return RoutingGuardOutput(

        routing_verdict="DISPATCH_ALLOWED",

        dispatch_allowed=True,

        human_confirmation_required=False,

        human_override_allowed=False,

        tool_name=input_data.tool_name,

        confidence=input_data.confidence,

        confidence_threshold=(
            input_data.confidence_threshold
        ),

        critical_safety_breach=False,

        reason=(
            "No human confirmation requirement, "
            "low-confidence condition, or critical "
            "safety breach was detected."
        ),

        allowed_actions=[],
    )