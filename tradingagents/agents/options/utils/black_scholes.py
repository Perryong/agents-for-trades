"""Black-Scholes option pricing and Greeks — stdlib only (no scipy).

Implements pricing and Greeks using math.erf for the normal CDF/PDF.
"""
import math


def _norm_cdf(x: float) -> float:
    """Cumulative distribution function of the standard normal distribution."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def _norm_pdf(x: float) -> float:
    """Probability density function of the standard normal distribution."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _d1_d2(S: float, K: float, T: float, r: float, q: float, sigma: float):
    """Compute d1 and d2 for Black-Scholes."""
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return d1, d2, sqrt_T


def greeks(S: float, K: float, T: float, r: float, q: float, sigma: float,
           option_type: str = "call") -> dict:
    """Compute Black-Scholes Greeks for a single option.

    Returns dict with keys: delta, gamma, theta, vega, price.
    """
    if T <= 0.0 or sigma <= 0.0 or S <= 0.0 or K <= 0.0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "price": 0.0}

    d1, d2, sqrt_T = _d1_d2(S, K, T, r, q, sigma)
    exp_qT = math.exp(-q * T)
    exp_rT = math.exp(-r * T)
    pdf_d1 = _norm_pdf(d1)

    # Gamma and Vega are the same for calls and puts
    gamma = exp_qT * pdf_d1 / (S * sigma * sqrt_T)
    vega = S * exp_qT * pdf_d1 * sqrt_T / 100.0  # per 1% vol move

    if option_type == "call":
        delta = exp_qT * _norm_cdf(d1)
        theta = (
            -S * exp_qT * pdf_d1 * sigma / (2 * sqrt_T)
            - r * K * exp_rT * _norm_cdf(d2)
            + q * S * exp_qT * _norm_cdf(d1)
        ) / 365.0  # per day
        price = call_price(S, K, T, r, q, sigma)
    else:
        delta = -exp_qT * _norm_cdf(-d1)
        theta = (
            -S * exp_qT * pdf_d1 * sigma / (2 * sqrt_T)
            + r * K * exp_rT * _norm_cdf(-d2)
            - q * S * exp_qT * _norm_cdf(-d1)
        ) / 365.0  # per day
        price = put_price(S, K, T, r, q, sigma)

    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 4),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
        "price": round(price, 4),
    }


def call_price(S: float, K: float, T: float, r: float, q: float, sigma: float) -> float:
    """Black-Scholes call option price.

    Parameters
    ----------
    S : float
        Underlying spot price.
    K : float
        Strike price.
    T : float
        Time to expiry in years.
    r : float
        Risk-free interest rate (annualised, continuously compounded).
    q : float
        Dividend yield (annualised, continuously compounded).
    sigma : float
        Implied volatility (annualised).

    Returns
    -------
    float
        Theoretical call option price.
    """
    if T <= 0.0 or sigma <= 0.0:
        return max(S * math.exp(-q * T) - K * math.exp(-r * T), 0.0)

    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    return S * math.exp(-q * T) * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)


def put_price(S: float, K: float, T: float, r: float, q: float, sigma: float) -> float:
    """Black-Scholes put option price.

    Parameters
    ----------
    S : float
        Underlying spot price.
    K : float
        Strike price.
    T : float
        Time to expiry in years.
    r : float
        Risk-free interest rate (annualised, continuously compounded).
    q : float
        Dividend yield (annualised, continuously compounded).
    sigma : float
        Implied volatility (annualised).

    Returns
    -------
    float
        Theoretical put option price.
    """
    if T <= 0.0 or sigma <= 0.0:
        return max(K * math.exp(-r * T) - S * math.exp(-q * T), 0.0)

    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    return K * math.exp(-r * T) * _norm_cdf(-d2) - S * math.exp(-q * T) * _norm_cdf(-d1)
