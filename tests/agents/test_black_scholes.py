"""Unit tests for Black-Scholes call_price and put_price functions.

All tests use stdlib-only implementation (no scipy).
Benchmark values verified: call=8.3976, put=6.5343 for S=K=150, T=0.25, r=0.05, q=0.0, sigma=0.25
"""
import math
import pytest

from tradingagents.agents.options.utils.black_scholes import call_price, put_price


# ---------------------------------------------------------------------------
# Benchmark parameters
# ---------------------------------------------------------------------------
S = 150.0
K = 150.0
T = 0.25
r = 0.05
q = 0.0
sigma = 0.25

CALL_BENCHMARK = 8.3976
PUT_BENCHMARK = 6.5343
TOLERANCE = 0.01  # 1%


# ---------------------------------------------------------------------------
# Test 1: call_price benchmark
# ---------------------------------------------------------------------------

def test_call_price_benchmark():
    """call_price(150, 150, 0.25, 0.05, 0.0, 0.25) must be within 1% of 8.3976."""
    result = call_price(S, K, T, r, q, sigma)
    assert abs(result - CALL_BENCHMARK) / CALL_BENCHMARK < TOLERANCE, (
        f"call_price benchmark failed: got {result:.4f}, expected {CALL_BENCHMARK:.4f} +/- 1%"
    )


# ---------------------------------------------------------------------------
# Test 2: put_price benchmark
# ---------------------------------------------------------------------------

def test_put_price_benchmark():
    """put_price(150, 150, 0.25, 0.05, 0.0, 0.25) must be within 1% of 6.5343."""
    result = put_price(S, K, T, r, q, sigma)
    assert abs(result - PUT_BENCHMARK) / PUT_BENCHMARK < TOLERANCE, (
        f"put_price benchmark failed: got {result:.4f}, expected {PUT_BENCHMARK:.4f} +/- 1%"
    )


# ---------------------------------------------------------------------------
# Test 3: Put-call parity
# ---------------------------------------------------------------------------

def test_call_put_parity():
    """call - put approx equals S*exp(-q*T) - K*exp(-r*T) (put-call parity)."""
    c = call_price(S, K, T, r, q, sigma)
    p = put_price(S, K, T, r, q, sigma)
    parity_rhs = S * math.exp(-q * T) - K * math.exp(-r * T)
    assert abs((c - p) - parity_rhs) < 0.01, (
        f"Put-call parity violated: call-put={c-p:.4f}, S*exp(-qT)-K*exp(-rT)={parity_rhs:.4f}"
    )


# ---------------------------------------------------------------------------
# Test 4: T=0 call returns intrinsic value (no exception)
# ---------------------------------------------------------------------------

def test_t_zero_call():
    """call_price(150, 140, 0.0, 0.05, 0.0, 0.25) returns intrinsic 10.0, no ZeroDivisionError."""
    result = call_price(150.0, 140.0, 0.0, 0.05, 0.0, 0.25)
    # Intrinsic: max(S - K, 0) = max(150 - 140, 0) = 10.0
    assert abs(result - 10.0) < 0.01, (
        f"T=0 call should return intrinsic 10.0, got {result:.4f}"
    )


# ---------------------------------------------------------------------------
# Test 5: T=0 put OTM returns 0.0
# ---------------------------------------------------------------------------

def test_t_zero_put_otm():
    """put_price(150, 140, 0.0, 0.05, 0.0, 0.25) returns 0.0 (OTM put at expiry)."""
    result = put_price(150.0, 140.0, 0.0, 0.05, 0.0, 0.25)
    # Intrinsic for put: max(K - S, 0) = max(140 - 150, 0) = 0.0
    assert abs(result - 0.0) < 0.01, (
        f"T=0 OTM put should return 0.0, got {result:.4f}"
    )


# ---------------------------------------------------------------------------
# Test 6: sigma=0 call returns max(S*exp(-qT) - K*exp(-rT), 0)
# ---------------------------------------------------------------------------

def test_sigma_zero():
    """call_price with sigma=0 returns max(S*exp(-qT) - K*exp(-rT), 0)."""
    result = call_price(150.0, 140.0, 0.25, 0.05, 0.0, 0.0)
    expected = max(150.0 * math.exp(0.0) - 140.0 * math.exp(-0.05 * 0.25), 0.0)
    assert abs(result - expected) < 0.01, (
        f"sigma=0 call should return {expected:.4f}, got {result:.4f}"
    )


# ---------------------------------------------------------------------------
# Test 7: Deep ITM call > 95
# ---------------------------------------------------------------------------

def test_deep_itm_call():
    """call_price(200, 100, 0.5, 0.05, 0.0, 0.30) should return value > 95 (deep ITM)."""
    result = call_price(200.0, 100.0, 0.5, 0.05, 0.0, 0.30)
    assert result > 95.0, (
        f"Deep ITM call (S=200, K=100) should be > 95, got {result:.4f}"
    )


# ---------------------------------------------------------------------------
# Test 8: Deep OTM call close to 0
# ---------------------------------------------------------------------------

def test_deep_otm_call():
    """call_price(100, 200, 0.5, 0.05, 0.0, 0.30) should return value close to 0."""
    result = call_price(100.0, 200.0, 0.5, 0.05, 0.0, 0.30)
    assert result < 1.0, (
        f"Deep OTM call (S=100, K=200) should be close to 0, got {result:.4f}"
    )


# ---------------------------------------------------------------------------
# Test 9: Dividend yield reduces call price
# ---------------------------------------------------------------------------

def test_dividend_yield_reduces_call():
    """call_price with q=0.03 should be less than call_price with q=0.0."""
    call_no_div = call_price(150.0, 150.0, 0.25, 0.05, 0.0, 0.25)
    call_with_div = call_price(150.0, 150.0, 0.25, 0.05, 0.03, 0.25)
    assert call_with_div < call_no_div, (
        f"Higher dividend yield should reduce call price: "
        f"q=0.0 gives {call_no_div:.4f}, q=0.03 gives {call_with_div:.4f}"
    )


# ---------------------------------------------------------------------------
# Test 10: Function signature accepts r parameter (no default — callers supply)
# ---------------------------------------------------------------------------

def test_risk_free_rate_default():
    """call_price and put_price must accept r parameter explicitly (no built-in default)."""
    import inspect
    call_sig = inspect.signature(call_price)
    put_sig = inspect.signature(put_price)

    # r should be a required parameter (no default)
    r_param_call = call_sig.parameters.get("r")
    r_param_put = put_sig.parameters.get("r")

    assert r_param_call is not None, "call_price must have 'r' parameter"
    assert r_param_put is not None, "put_price must have 'r' parameter"

    assert r_param_call.default is inspect.Parameter.empty, (
        "call_price 'r' parameter must have no default (config supplies 0.05 at call site)"
    )
    assert r_param_put.default is inspect.Parameter.empty, (
        "put_price 'r' parameter must have no default (config supplies 0.05 at call site)"
    )
