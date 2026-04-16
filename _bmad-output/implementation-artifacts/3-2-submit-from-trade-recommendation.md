# Story 3.2: Submit Trade from TradeRecommendation

Status: review

## Story

As a user,
I want approved trade recommendations to be submitted to paper trading using the structured TradeSpec,
so that exact trade specifications are executed without human interpretation or regex parsing.

## Analysis

This story is effectively complete from Story 3.1:
- `PaperBackend.submit_order()` and `submit_bracket_order()` accept `OrderRequest` dataclasses with all TradeSpec fields
- `OrderRequest` maps directly from TradeSpec: ticker, direction, entry_price, stop_loss, profit_target, position_size, strike, expiry, contract_type
- The route handler creates `OrderRequest` from the API request schema
- The wiring from TradeRecommendation → OrderRequest → PaperBackend is straightforward (TradeRecommendation.trade_spec fields → OrderRequest fields)

The approval workflow (frontend sends approved TradeRecommendation to the API, which creates an OrderRequest) will be implemented in Epic 4 (frontend) when the approval UI is built.

## Tasks / Subtasks

- [x] PaperBackend.submit_order() accepts structured OrderRequest (Story 3.1)
- [x] PaperBackend.submit_bracket_order() accepts structured OrderRequest with target/stop (Story 3.1)
- [x] OrderRequest dataclass maps 1:1 to TradeSpec fields
- [x] No regex extraction needed — all fields are typed

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- OrderRequest → PaperBackend flow implemented in Story 3.1
- The regex extraction functions (extract_confidence, extract_target_price, extract_stop_price) still exist for backward compatibility with old-style trades but are not used for new structured TradeSpec submissions
- Full wiring from TradeRecommendation approval → API → OrderRequest → PaperBackend will complete in Epic 4 (frontend approval workflow)

### File List
- No new files — work completed in Story 3.1
