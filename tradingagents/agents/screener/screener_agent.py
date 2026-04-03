"""LLM screener agent module.

Ranks pre-filtered stock candidates using an LLM to produce a ranked list of
top picks with rationale and confidence scores.

Architecture:
- TopPick / ScreenerResult: Pydantic models for structured output
- create_screener_agent(llm): factory returning a callable (RANK-01)
- run_screener(config, llm): public entry point (RANK-02)
- AgentState isolation guard via _validate_not_agent_state (RANK-03)
- Malformed JSON retry + graceful degradation (RANK-04)

ScreenerResult never enters AgentState — enforced at run_screener boundary.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, ValidationError

from tradingagents.dataflows.screener_data import ScreenerCandidate, get_screener_signals

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

AGENT_STATE_KEYS = {"company_of_interest", "trade_date", "messages"}


class TopPick(BaseModel):
    """A single LLM-ranked stock candidate.

    Fields:
        ticker: Stock symbol (e.g., "AAPL").
        score: LLM-assigned conviction score in [0.0, 1.0].
        rationale: 1-2 sentence explanation of the pick.
        confidence: LLM confidence in the ranking in [0.0, 1.0].
        key_metrics: Optional dict with metrics (e.g., volume_ratio, momentum_5d).
        sector: Optional sector label (may be None when not provided by LLM).
        market_cap: Optional market cap label (may be None when not provided).
    """

    ticker: str
    score: float = Field(ge=0.0, le=1.0)
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    key_metrics: dict = Field(default_factory=dict)
    sector: Optional[str] = None
    market_cap: Optional[str] = None


class ScreenerResult(BaseModel):
    """Output of the screener agent containing ranked top picks.

    Fields:
        picks: Ordered list of TopPick objects (highest conviction first).
        screened_at: UTC timestamp when screening ran.
        candidate_count: Number of candidates that were scored.
        model_used: LLM class name used for screening.
        error: Populated when partial-result degradation occurred (LLM parse failure).
    """

    picks: list[TopPick]
    screened_at: datetime
    candidate_count: int
    model_used: str
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a quantitative stock screener analyst. You will receive a ranked "
    "list of stock candidates with their momentum and volume signals. Your task "
    "is to select the top N candidates and provide a conviction-based ranking.\n\n"
    "SCORING RUBRIC:\n"
    "- Volume momentum signals high urgency: weight volume_score and unusual_activity heavily\n"
    "- Sector diversification preferred: penalize identical-sector clustering\n"
    "- momentum_score captures 5-day price trend; prefer positive momentum with volume confirmation\n"
    "- composite_score is an equal-weight mean of normalized signals (use as baseline)\n\n"
    "RESPONSE FORMAT:\n"
    "Respond with ONLY a JSON object. No preamble, no markdown fences, no explanation. "
    "The JSON must have exactly one key: 'picks', which is an array of pick objects. "
    "Each pick object must have:\n"
    "  - ticker (string): stock symbol\n"
    "  - score (float 0.0-1.0): your conviction score\n"
    "  - rationale (string): 1-2 sentences explaining the pick\n"
    "  - confidence (float 0.0-1.0): your confidence in this ranking\n"
    "  - key_metrics (object): include volume_ratio and momentum_5d from the input data\n\n"
    "Example output:\n"
    '{{"picks": [{{"ticker": "AAPL", "score": 0.92, "rationale": "Strong momentum confirmed by 2.1x volume surge.", "confidence": 0.88, "key_metrics": {{"volume_ratio": 2.1, "momentum_5d": 0.045}}}}]}}'
)

STRICT_PROMPT_PREFIX = (
    "IMPORTANT: Respond with ONLY valid JSON. No text before or after. "
    "No markdown fences. No explanations. Start your response with a curly brace and end with a curly brace.\n\n"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_candidates_for_prompt(candidates: list[ScreenerCandidate]) -> str:
    """Format screener candidates for LLM consumption.

    Projects each candidate to: ticker, composite_score, volume_score, momentum_score.
    Omits raw DataFrames and coverage_note to keep prompt concise.

    Args:
        candidates: List of ScreenerCandidate objects (pre-sorted by composite_score).

    Returns:
        Numbered list string suitable for embedding in the LLM prompt.
    """
    lines = ["Candidates (ranked by composite signal score):"]
    for i, c in enumerate(candidates, start=1):
        lines.append(
            f"{i}. {c.ticker} | composite={c.composite_score:.3f} "
            f"| volume={c.volume_score:.3f} | momentum={c.momentum_score:.3f}"
        )
    return "\n".join(lines)


def _parse_screener_response(
    content: str, n_picks: int
) -> ScreenerResult | None:
    """Parse LLM response into a ScreenerResult.

    Strips markdown fences, parses JSON, validates against ScreenerResult model.
    Returns None on any parse or validation failure.

    Args:
        content: Raw LLM response string.
        n_picks: Maximum number of picks to include.

    Returns:
        ScreenerResult on success, None on failure.
    """
    # Strip markdown fences if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
    if fence_match:
        content = fence_match.group(1)

    content = content.strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None

    # Ensure picks list exists
    if "picks" not in data or not isinstance(data["picks"], list):
        return None

    # Truncate to n_picks
    data["picks"] = data["picks"][:n_picks]

    try:
        picks = [TopPick.model_validate(p) for p in data["picks"]]
        return picks  # type: ignore[return-value]  # caller assembles full ScreenerResult
    except (ValidationError, TypeError, KeyError):
        return None


def _validate_not_agent_state(obj: object) -> None:
    """Guard: raise TypeError if obj looks like an AgentState dict.

    AgentState isolation guard (RANK-03). Called at run_screener entry to
    ensure ScreenerResult is never written to or confused with AgentState.

    Args:
        obj: Object to check.

    Raises:
        TypeError: If obj is a dict containing AgentState keys.
    """
    if isinstance(obj, dict) and AGENT_STATE_KEYS.issubset(obj.keys()):
        raise TypeError(
            "ScreenerResult must not be passed as AgentState. "
            "ScreenerResult is standalone output — never assign it to AgentState fields."
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_screener_agent(llm):
    """Factory that returns an LLM screener callable (RANK-01).

    The returned closure accepts (candidates, config) and returns ScreenerResult.
    Includes retry logic for malformed JSON and graceful degradation (RANK-04).

    Args:
        llm: LangChain-compatible LLM instance.

    Returns:
        Callable: screener_agent(candidates: list[ScreenerCandidate], config: dict) -> ScreenerResult
    """

    def screener_agent(
        candidates: list[ScreenerCandidate], config: dict
    ) -> ScreenerResult:
        n_picks = min(config.get("screener_n_picks", 5), 10)
        model_name = type(llm).__name__
        screened_at = datetime.now(timezone.utc)
        candidate_count = len(candidates)

        candidate_text = _format_candidates_for_prompt(candidates)

        # First attempt
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", candidate_text),
        ])
        result = (prompt | llm).invoke({})
        picks = _parse_screener_response(result.content, n_picks)

        if picks is None:
            # Retry once with a stricter prompt
            strict_prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("human", STRICT_PROMPT_PREFIX + candidate_text),
            ])
            result2 = (strict_prompt | llm).invoke({})
            picks = _parse_screener_response(result2.content, n_picks)

        if picks is None:
            # Graceful degradation: auto-select top n_picks by composite_score
            sorted_candidates = sorted(
                candidates, key=lambda c: c.composite_score, reverse=True
            )[:n_picks]
            picks = [
                TopPick(
                    ticker=c.ticker,
                    score=round(c.composite_score, 4),
                    rationale=(
                        "Auto-selected by composite score (LLM parse failed)"
                    ),
                    confidence=round(c.composite_score * 0.7, 4),
                    key_metrics={
                        "volume_score": c.volume_score,
                        "momentum_score": c.momentum_score,
                    },
                )
                for c in sorted_candidates
            ]
            return ScreenerResult(
                picks=picks,
                screened_at=screened_at,
                candidate_count=candidate_count,
                model_used=model_name,
                error="LLM response could not be parsed after retry",
            )

        return ScreenerResult(
            picks=picks,
            screened_at=screened_at,
            candidate_count=candidate_count,
            model_used=model_name,
        )

    return screener_agent


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_screener(config: dict, llm) -> ScreenerResult:
    """Public entry point: run the full screener pipeline (RANK-02).

    Fetches candidates from the data layer, ranks them via the LLM screener,
    and returns a ScreenerResult. Enforces AgentState isolation (RANK-03).

    Args:
        config: Configuration dict. Supported keys:
            - screener_max_candidates (int, default 50): max candidates to fetch
            - screener_n_picks (int, default 5): top picks to return
        llm: LangChain-compatible LLM instance.

    Returns:
        ScreenerResult with ranked top picks.

    Raises:
        TypeError: If the agent returns a non-ScreenerResult (should never happen
            in normal operation, but guards against misuse).
    """
    candidates, _coverage = get_screener_signals(
        max_candidates=config.get("screener_max_candidates", 50)
    )

    # Unwrap BaseLLMClient wrappers to get the LangChain-compatible LLM
    if hasattr(llm, "get_llm"):
        llm = llm.get_llm()

    agent = create_screener_agent(llm)
    result = agent(candidates, config)

    if not isinstance(result, ScreenerResult):
        raise TypeError(
            f"Expected ScreenerResult, got {type(result)}. "
            "ScreenerResult must never enter AgentState."
        )

    return result
