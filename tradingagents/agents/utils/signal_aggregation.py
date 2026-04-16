"""Signal aggregation utility for the risk judge.

Computes weighted confidence, identifies majority direction, and builds
a reasoning chain with dissent flags from structured AgentSignal dicts.
"""

from tradingagents.agents.protocol import AgentSignalSummary


def aggregate_signals(
    signals: dict[str, dict | None],
    weights: dict[str, float] | None = None,
) -> tuple[float, list[AgentSignalSummary], str]:
    """Aggregate structured agent signals into overall assessment.

    Args:
        signals: Dict mapping agent_name → AgentSignal dict (or None if agent didn't produce output).
        weights: Optional dict mapping agent_name → weight (default 1.0 for all).

    Returns:
        Tuple of (overall_confidence, reasoning_chain, majority_direction).
        - overall_confidence: Weighted average confidence (0-100).
        - reasoning_chain: List of AgentSignalSummary with dissent flags.
        - majority_direction: "bullish", "bearish", or "neutral".
    """
    # Filter out None signals
    active = {k: v for k, v in signals.items() if v is not None}

    if not active:
        return 0.0, [], "neutral"

    # Count weighted direction votes
    direction_votes: dict[str, float] = {"bullish": 0.0, "bearish": 0.0, "neutral": 0.0}
    for name, signal in active.items():
        w = weights.get(name, 1.0) if weights else 1.0
        direction_votes[signal["signal_direction"]] += w

    # Majority direction (max weighted votes)
    majority = max(direction_votes, key=direction_votes.get)

    # Weighted confidence
    total_weight = 0.0
    weighted_conf = 0.0
    for name, signal in active.items():
        w = weights.get(name, 1.0) if weights else 1.0
        weighted_conf += signal["confidence"] * w
        total_weight += w

    overall_confidence = weighted_conf / total_weight if total_weight > 0 else 0.0

    # Build reasoning chain with dissent flags
    chain = []
    for name, signal in active.items():
        is_dissenting = signal["signal_direction"] != majority
        chain.append(
            AgentSignalSummary(
                agent_name=name,
                signal_direction=signal["signal_direction"],
                confidence=signal["confidence"],
                evidence=signal.get("evidence", []),
                is_dissenting=is_dissenting,
            )
        )

    return overall_confidence, chain, majority
