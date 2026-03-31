# TESTING.md — Test Structure and Practices

## Framework

**Status:** No formal test framework. Manual smoke testing only.

- No pytest, unittest, or other test runner configured
- No test discovery configuration in `pyproject.toml`
- No CI test pipeline

## Existing Tests

### `test.py` (root)

Single manual smoke test:

```python
# Calls get_stock_stats_indicators_window with live network
# No assertions — passes if no exception raised
```

- **Coverage:** ~1 function in dataflows
- **Type:** Integration smoke test (requires live network + API keys)
- **Assertions:** None — relies on absence of exceptions
- **Automation:** Not wired to any runner

## Key Untested Areas (Risk-Ranked)

| Area | File | Risk | Why |
|------|------|------|-----|
| Vendor routing fallback | `tradingagents/dataflows/interface.py` | HIGH | Primary/fallback chain silently degrades |
| LLM client factory | `tradingagents/llm_clients/factory.py` | HIGH | String comparisons route to different providers — typos silently fail |
| Conditional graph logic | `tradingagents/graph/conditional_logic.py` | HIGH | Round-count boundaries drive LangGraph flow — off-by-one causes infinite loops |
| BM25 memory retrieval | `tradingagents/agents/utils/memory.py` | MEDIUM | Stateful index rebuild on each query — correctness unverified |
| Cache TTL & corruption fallback | `tradingagents/dataflows/yfinance_cache.py` | MEDIUM | TTL staleness and CSV corruption fallback paths untested |
| Model validation | `tradingagents/llm_clients/validators.py` | LOW | Static allowlist — easy to unit test |

## Recommended Test Patterns

Given the Python codebase style, recommended approach:

```python
# pytest (add to pyproject.toml)
[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Unit tests** — mock LLM calls and data fetches:
```python
from unittest.mock import patch, MagicMock

def test_vendor_routing_fallback():
    with patch("tradingagents.dataflows.interface.primary_provider") as mock:
        mock.side_effect = Exception("API down")
        result = get_stock_data("AAPL")
        # assert fallback was used
```

**Integration tests** — mark with `@pytest.mark.integration`, skip in CI unless keys present.

## Gaps Summary

- No assertions in existing test
- No mocking infrastructure
- No fixtures or factories
- No coverage measurement
- No CI integration
- All testing requires live API keys and network access
