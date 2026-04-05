"""Tests for dashboard extensions (D-16, D-17)."""
import pytest


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 01-05")
@pytest.mark.asyncio
async def test_risk_reward():
    """D-16: Dashboard summary includes avg_risk_reward ratio."""
    # Expects: For BUY trade with fill=100, target=120, stop=90:
    #   risk = 100 - 90 = 10, reward = 120 - 100 = 20, ratio = 2.0
    # Expects: avg_risk_reward field present in DashboardSummaryResponse
    pass


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 01-05")
@pytest.mark.asyncio
async def test_r_multiple():
    """D-17: Dashboard summary includes avg_r_multiple."""
    # Expects: For BUY trade with fill=100, stop=90, pnl_pct=15.0:
    #   risk_pct = |100 - 90| / 100 * 100 = 10.0
    #   r_multiple = 15.0 / 10.0 = 1.5
    # Expects: avg_r_multiple field present in DashboardSummaryResponse
    pass
