# Story 9.1: Screener Registry and Strategy Interface

Status: review

## Story

As a developer,
I want a registry pattern for screener strategies with a common interface,
so that new strategies can be added without modifying the API or UI.

## Acceptance Criteria

1. **Given** the current screener has a single hardcoded strategy **When** the registry pattern is implemented **Then** a `ScreenerStrategy` protocol is defined in `tradingagents/agents/screener/registry.py` with method `screen(config, llm) → ScreenerResult`

2. **And** each strategy is registered by name (e.g., "momentum", "vcp", "canslim")

3. **And** `POST /api/screen` accepts a `strategy` parameter to select which screener to run

4. **And** the existing momentum+volume screener is refactored to implement the protocol as "momentum" strategy

5. **And** a factory function `get_strategy(name)` returns the appropriate strategy implementation

6. **And** tests verify strategy registration, selection, and fallback to default

## Tasks / Subtasks

- [x] Task 1: Create ScreenerStrategy protocol and registry (AC: #1, #2, #5)
  - [x] Create `tradingagents/agents/screener/registry.py`
  - [x] Define `ScreenerStrategy` Protocol: `def screen(self, config: dict, llm) -> ScreenerResult`
  - [x] Define `ScreenerInfo` dataclass: name, display_name, description
  - [x] Create `_registry: dict[str, tuple[ScreenerInfo, ScreenerStrategy]]` module-level dict
  - [x] Create `register_strategy(name, info, strategy)` function
  - [x] Create `get_strategy(name) -> ScreenerStrategy` function (raises KeyError if unknown)
  - [x] Create `list_strategies() -> list[ScreenerInfo]` function
  - [x] Default fallback: if name not found and name == "", return "momentum"
- [x] Task 2: Refactor existing screener as "momentum" strategy (AC: #4)
  - [x] Create `tradingagents/agents/screener/strategies/momentum.py`
  - [x] Extract `run_screener` logic into a `MomentumStrategy` class implementing the protocol
  - [x] Register as "momentum" in registry with display_name="Momentum & Volume", description="Signal-based momentum and volume screening with LLM ranking"
  - [x] Keep `run_screener()` in `screener_agent.py` as a backward-compatible wrapper that delegates to the registry
- [x] Task 3: Update API to accept strategy parameter (AC: #3)
  - [x] Add `strategy: str = "momentum"` field to `ScreenRequest` in `api/schemas.py`
  - [x] Update `POST /api/screen` in `api/screener_routes.py` to look up strategy from registry
  - [x] Add `GET /api/screen/strategies` endpoint returning list of available strategies
- [x] Task 4: Update frontend useScreener hook (AC: #3)
  - [x] Add `strategy` parameter to `runScreen()` in `frontend/src/hooks/useScreener.ts`
  - [x] Pass strategy in POST body
  - [x] Add `ScreenerStrategy` type to `frontend/src/types.ts`
- [x] Task 5: Write tests (AC: #6)
  - [x] Test: register strategy, retrieve by name
  - [x] Test: list_strategies returns all registered
  - [x] Test: get_strategy with unknown name raises KeyError
  - [x] Test: momentum strategy produces ScreenerResult (using mock LLM)
  - [x] Test: API accepts strategy parameter
- [x] Task 6: Build verification
  - [x] Backend tests pass
  - [x] Frontend tsc + vite build clean

## Dev Notes

### Architecture & Approach

**Registry pattern** — similar to how agent protocol works. Each strategy implements a protocol, registers with a name, and the API/UI selects by name.

```python
# tradingagents/agents/screener/registry.py

from typing import Protocol, runtime_checkable
from dataclasses import dataclass

@runtime_checkable
class ScreenerStrategy(Protocol):
    def screen(self, config: dict, llm) -> "ScreenerResult": ...

@dataclass
class ScreenerInfo:
    name: str
    display_name: str
    description: str

_registry: dict[str, tuple[ScreenerInfo, ScreenerStrategy]] = {}

def register_strategy(name: str, info: ScreenerInfo, strategy: ScreenerStrategy) -> None:
    _registry[name] = (info, strategy)

def get_strategy(name: str) -> ScreenerStrategy:
    if not name:
        name = "momentum"
    if name not in _registry:
        raise KeyError(f"Unknown screener strategy: {name}")
    return _registry[name][1]

def list_strategies() -> list[ScreenerInfo]:
    return [info for info, _ in _registry.values()]
```

**Existing code refactor:** The current `run_screener(config, llm)` in `screener_agent.py` becomes a thin wrapper:
```python
def run_screener(config, llm):
    from .registry import get_strategy
    strategy = get_strategy("momentum")
    return strategy.screen(config, llm)
```

The actual logic moves to `strategies/momentum.py` as a `MomentumStrategy` class.

### File Locations

| File | Action | Purpose |
|------|--------|---------|
| `tradingagents/agents/screener/registry.py` | NEW | Strategy protocol + registry |
| `tradingagents/agents/screener/strategies/__init__.py` | NEW | Strategies package |
| `tradingagents/agents/screener/strategies/momentum.py` | NEW | Refactored momentum strategy |
| `tradingagents/agents/screener/screener_agent.py` | MODIFY | Delegate to registry |
| `tradingagents/agents/screener/__init__.py` | MODIFY | Auto-register strategies on import |
| `api/schemas.py` | MODIFY | Add strategy to ScreenRequest |
| `api/screener_routes.py` | MODIFY | Use registry, add strategies endpoint |
| `frontend/src/hooks/useScreener.ts` | MODIFY | Accept strategy param |
| `frontend/src/types.ts` | MODIFY | Add ScreenerStrategyInfo type |
| `tests/agents/test_screener_registry.py` | NEW | Registry tests |

### Previous Story Context

The existing screener was built in GSD milestone v1.1 (phases 08-11). Key patterns:
- `screener_data.py` fetches OHLCV and computes signals (volume, momentum, unusual activity)
- `screener_agent.py` uses LLM to rank candidates
- `ScreenerResult` and `TopPick` are the output models
- API uses `ScreenRequest` with max_picks, universe, llm_provider, quick_think_llm

### Anti-Patterns to Avoid

- **DO NOT** break the existing `run_screener()` function signature — it's called from `screener_routes.py`
- **DO NOT** add VCP/CANSLIM/Earnings strategies in this story — that's Stories 9.2-9.4
- **DO NOT** change ScreenerResult or TopPick models — all strategies must output the same shape
- **DO NOT** add new pip dependencies — pure Python protocol/registry pattern

### References

- [Source: tradingagents/agents/screener/screener_agent.py — existing screener]
- [Source: api/screener_routes.py — API endpoint]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 9.1]
- [Source: tradingagents/agents/protocol.py — Protocol pattern reference]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Completion Notes List

- Created ScreenerStrategy Protocol + ScreenerInfo dataclass in registry.py
- Registry functions: register_strategy, get_strategy, list_strategies, get_strategy_info
- Empty string fallback → "momentum" default
- Refactored existing screener into MomentumStrategy class in strategies/momentum.py
- Auto-registration on import via strategies/__init__.py
- Updated run_screener() as backward-compatible wrapper delegating to registry
- Added strategy param to ScreenRequest schema and POST /api/screen
- Added GET /api/screen/strategies endpoint returning available strategies
- Updated useScreener hook with strategy + maxPicks params
- Added ScreenerStrategyInfo type to frontend types.ts
- 6 registry tests all passing

### Change Log

- 2026-04-16: Story 9.1 implemented — screener registry with strategy protocol

### File List

- `tradingagents/agents/screener/registry.py` — NEW: Protocol + registry
- `tradingagents/agents/screener/strategies/__init__.py` — NEW: Auto-register package
- `tradingagents/agents/screener/strategies/momentum.py` — NEW: Refactored momentum strategy
- `tradingagents/agents/screener/__init__.py` — MODIFIED: Re-exports + auto-import strategies
- `tradingagents/agents/screener/screener_agent.py` — MODIFIED: run_screener delegates to registry
- `api/schemas.py` — MODIFIED: Added strategy field to ScreenRequest
- `api/screener_routes.py` — MODIFIED: Uses registry, added GET /api/screen/strategies
- `frontend/src/hooks/useScreener.ts` — MODIFIED: Added strategy + maxPicks params
- `frontend/src/types.ts` — MODIFIED: Added ScreenerStrategyInfo type
- `tests/agents/test_screener_registry.py` — NEW: 6 registry tests
