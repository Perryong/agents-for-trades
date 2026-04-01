"""Black-Scholes option pricing — stdlib only (no scipy).

Implements call_price and put_price using math.erf for the normal CDF.
"""
import math


def _norm_cdf(x: float) -> float:
    """Cumulative distribution function of the standard normal distribution."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


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
