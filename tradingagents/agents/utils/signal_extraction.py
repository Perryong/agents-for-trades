"""Shared utility for extracting structured AgentSignal from LLM response content.

Used by all analyst agents to parse the JSON block appended to their prose reports.
"""

import json
import re

from tradingagents.agents.protocol import AgentSignal
from tradingagents.exceptions import AgentProtocolError


# Instruction appended to each analyst's system prompt
STRUCTURED_OUTPUT_INSTRUCTION = """

CRITICAL: At the very end of your report, you MUST append a JSON block with your structured signal assessment. Use this exact format:

```json
{
  "signal_direction": "bullish" or "bearish" or "neutral",
  "confidence": <number 0-100>,
  "time_horizon": "intraday" or "swing" or "position",
  "evidence": ["<key finding 1>", "<key finding 2>", ...],
  "data_freshness": "<ISO 8601 datetime of when data was fetched>",
  "valid_until": "<ISO 8601 datetime when this signal expires>"
}
```

The JSON block MUST be the last thing in your response. Do not add any text after it."""


def _extract_outermost_json(text: str) -> str | None:
    """Extract outermost JSON object using brace counting (handles nested structures)."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def extract_agent_signal_json(content: str) -> dict:
    """Extract AgentSignal JSON block from LLM response content.

    Looks for a fenced ```json block first, then falls back to a raw JSON
    object containing "signal_direction" at the end of the content.

    Raises:
        ValueError: If no AgentSignal JSON block is found.
    """
    if not content:
        raise ValueError("No AgentSignal JSON block found in empty response")

    # Try fenced ```json ... ``` block (use brace counting for nested JSON)
    fence_match = re.search(r"```json\s*", content)
    if fence_match:
        after_fence = content[fence_match.end():]
        json_str = _extract_outermost_json(after_fence)
        if json_str:
            return json.loads(json_str)

    # Fallback: find last JSON object containing signal_direction
    # Search from the end of content for the last { ... } block
    last_obj = None
    search_from = len(content)
    while search_from > 0:
        idx = content.rfind("{", 0, search_from)
        if idx == -1:
            break
        candidate = _extract_outermost_json(content[idx:])
        if candidate and "signal_direction" in candidate:
            try:
                last_obj = json.loads(candidate)
                break
            except json.JSONDecodeError:
                pass
        search_from = idx

    if last_obj:
        return last_obj

    raise ValueError("No AgentSignal JSON block found in response")


def parse_agent_signal(
    content: str, *, ticker: str, agent_name: str
) -> dict:
    """Extract and validate an AgentSignal from LLM response content.

    Returns the validated AgentSignal as a JSON-serializable dict.

    Raises:
        AgentProtocolError: If extraction or validation fails.
    """
    try:
        raw_signal = extract_agent_signal_json(content)
        signal = AgentSignal(**raw_signal)
        return signal.model_dump(mode="json")
    except Exception as exc:
        raise AgentProtocolError(
            f"{agent_name} analyst failed to produce valid AgentSignal: {exc}",
            ticker=ticker,
            agent_name=agent_name,
        ) from exc
