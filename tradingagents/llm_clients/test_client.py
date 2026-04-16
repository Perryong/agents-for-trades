"""Test/mock LLM client for verifying pipeline flow without API calls.

Returns instant mock responses so the full graph can be exercised end-to-end
without burning API credits or waiting for real LLM completions.
"""

import time
from typing import Any, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from .base_client import BaseLLMClient


# ---------------------------------------------------------------------------
# Mock responses keyed by partial prompt content
# ---------------------------------------------------------------------------

_MOCK_RESPONSES = {
    "market": (
        "## Market Analysis (TEST)\n\n"
        "Current market conditions show moderate volatility. "
        "The S&P 500 is trading near all-time highs with mixed breadth. "
        "Sector rotation favours technology and healthcare. "
        "Risk-on sentiment persists but caution warranted near resistance levels.\n\n"
        "**Signal: Neutral-to-Bullish**"
    ),
    "technical": (
        "## Technical Analysis (TEST)\n\n"
        "Price is trading above the 50-day and 200-day moving averages. "
        "RSI at 58 indicates moderate momentum without overbought conditions. "
        "MACD histogram is positive and expanding. "
        "Key support at the 20-day EMA, resistance at the recent swing high.\n\n"
        "**Signal: Bullish**"
    ),
    "social": (
        "## Social Media Sentiment (TEST)\n\n"
        "Social media sentiment is broadly positive with increasing mention volume. "
        "Reddit and Twitter show bullish retail interest. "
        "No significant negative catalysts detected in social feeds. "
        "Sentiment score: 0.65 (moderately positive).\n\n"
        "**Signal: Bullish**"
    ),
    "news": (
        "## News Analysis (TEST)\n\n"
        "Recent news coverage is neutral to positive. "
        "No major negative headlines or regulatory concerns. "
        "Earnings expectations are in line with consensus. "
        "Industry tailwinds from recent policy developments.\n\n"
        "**Signal: Neutral**"
    ),
    "fundamental": (
        "## Fundamentals Analysis (TEST)\n\n"
        "Revenue growth of 12% YoY with expanding margins. "
        "P/E ratio is in line with sector average. "
        "Strong balance sheet with low debt-to-equity. "
        "Free cash flow generation supports dividend and buyback programs.\n\n"
        "**Signal: Bullish**"
    ),
    "bull": (
        "## Bull Case (TEST)\n\n"
        "Bull Researcher: Strong technical setup with fundamental support. "
        "Multiple catalysts ahead including earnings and product launches. "
        "Institutional accumulation visible in volume patterns. "
        "Price target suggests 15-20% upside potential."
    ),
    "bear": (
        "## Bear Case (TEST)\n\n"
        "Bear Researcher: Valuation is stretched relative to historical averages. "
        "Macro headwinds from interest rate uncertainty. "
        "Insider selling has increased in recent quarters. "
        "Potential downside of 10-15% if support breaks."
    ),
    "research manager": (
        "## Investment Plan (TEST)\n\n"
        "After weighing bull and bear arguments, the evidence slightly favours "
        "a bullish stance. Technical momentum and fundamental strength outweigh "
        "valuation concerns. Recommend a measured long position with defined risk.\n\n"
        "**Recommendation: BUY with 2% position size, stop-loss at -5%**"
    ),
    "trader": (
        "## Trader Analysis (TEST)\n\n"
        "Entry: Current market price\n"
        "Target: +12% from entry\n"
        "Stop-Loss: -5% from entry\n"
        "Position Size: 2% of portfolio\n"
        "Risk/Reward: 2.4:1\n\n"
        "**Action: BUY**"
    ),
    "aggressive": (
        "## Aggressive Analyst (TEST)\n\n"
        "Aggressive Analyst: The setup presents a clear opportunity. "
        "Risk/reward is favourable at current levels. "
        "Recommend full position sizing with tight stops. "
        "Momentum indicators support immediate entry."
    ),
    "conservative": (
        "## Conservative Analyst (TEST)\n\n"
        "Conservative Analyst: While the setup has merit, caution is warranted. "
        "Prefer to wait for a pullback to support before entry. "
        "Reduce position size to 1% given current volatility. "
        "Consider scaling in over multiple sessions."
    ),
    "neutral": (
        "## Neutral Analyst (TEST)\n\n"
        "Neutral Analyst: Both sides present valid arguments. "
        "The technical and fundamental case supports a buy, "
        "but position sizing should reflect the macro uncertainty. "
        "A moderate position with clear risk management is appropriate."
    ),
    "risk": (
        "## Final Trade Decision (TEST)\n\n"
        "**Signal: BUY**\n\n"
        "After comprehensive analysis across all dimensions:\n"
        "- Market conditions: Supportive\n"
        "- Technical setup: Bullish\n"
        "- Fundamentals: Strong\n"
        "- Sentiment: Positive\n"
        "- Risk/Reward: 2.4:1\n\n"
        "**Entry:** Market price\n"
        "**Target:** +12%\n"
        "**Stop-Loss:** -5%\n"
        "**Position Size:** 2% of portfolio\n\n"
        "Confidence: 72%"
    ),
    "volatility": (
        "## Volatility Analysis (TEST)\n\n"
        "Current IV Rank: 45th percentile\n"
        "HV20: 28% | IV30: 32%\n"
        "Volatility Risk Premium: +4% (slightly elevated)\n"
        "Skew: Normal, no unusual put demand\n\n"
        "Environment favours selling premium or defined-risk spreads."
    ),
    "flow": (
        "## Options Flow Analysis (TEST)\n\n"
        "Unusual activity detected in near-term calls. "
        "Put/Call ratio: 0.75 (moderately bullish). "
        "Large block trades suggest institutional positioning. "
        "No significant dark pool prints detected."
    ),
    "strategy": (
        "## Options Strategy Selection (TEST)\n\n"
        "Given the bullish bias and moderate IV environment:\n"
        "**Recommended Strategy: Bull Call Spread**\n\n"
        "Rationale: Defined risk, reduced cost basis vs naked long call, "
        "benefits from directional move while limiting premium outlay."
    ),
    "pricing": (
        "## Options Pricing Analysis (TEST)\n\n"
        "Theoretical value aligns with market pricing. "
        "Edge: +0.05 (fair value). "
        "Spread is within normal bid-ask width. "
        "No significant mispricing detected."
    ),
    "legs": (
        "## Options Legs (TEST)\n\n"
        "Constructed order based on selected contracts.\n"
        "Net debit: $2.15 per spread\n"
        "Max profit: $2.85 per spread\n"
        "Max loss: $2.15 per spread\n"
        "Breakeven: Strike + net debit"
    ),
    "greeks": (
        "## Greeks Monitor (TEST)\n\n"
        "Position Greeks:\n"
        "Delta: +0.35\n"
        "Gamma: +0.02\n"
        "Theta: -0.08\n"
        "Vega: +0.12\n\n"
        "Net exposure is moderately bullish with manageable time decay."
    ),
}

# Fallback for any unmatched prompt
_DEFAULT_RESPONSE = (
    "## Analysis (TEST)\n\n"
    "This is a test response from the mock LLM provider. "
    "The pipeline flow is working correctly. "
    "Replace with a real LLM provider for actual analysis."
)

_SIMULATE_DELAY = 0.3  # seconds per call — enough to see progress without waiting


def _match_response(prompt_text: str) -> str:
    """Match prompt content to a mock response."""
    lower = prompt_text.lower()
    for key, response in _MOCK_RESPONSES.items():
        if key in lower:
            return response
    return _DEFAULT_RESPONSE


class MockChatModel(BaseChatModel):
    """A fake chat model that returns canned responses for pipeline testing."""

    model_name: str = "test-mock"

    @property
    def _llm_type(self) -> str:
        return "test-mock"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        time.sleep(_SIMULATE_DELAY)

        # Build prompt text from all messages for matching
        prompt_text = " ".join(
            m.content if isinstance(m.content, str) else str(m.content)
            for m in messages
        )
        response_text = _match_response(prompt_text)

        message = AIMessage(content=response_text)
        return ChatResult(generations=[ChatGeneration(message=message)])

    def bind_tools(self, tools: Any, **kwargs: Any) -> "MockChatModel":
        """Accept bind_tools calls — return self since we never emit tool_calls."""
        return self


class TestClient(BaseLLMClient):
    """Test/mock client for pipeline flow verification."""

    def __init__(self, model: str = "test-mock", base_url: Optional[str] = None, **kwargs):
        super().__init__(model, base_url, **kwargs)

    def get_llm(self) -> Any:
        """Return a MockChatModel instance."""
        llm = MockChatModel()
        # Pass through callbacks if provided
        if "callbacks" in self.kwargs:
            llm.callbacks = self.kwargs["callbacks"]
        return llm

    def validate_model(self) -> bool:
        return True
