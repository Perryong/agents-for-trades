from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd
import yfinance as yf

from .yfinance_cache import get_cached_dataframe
from .yfinance_session import yf_session


MARKET_DATA_CACHE_TTL_SECONDS = 6 * 60 * 60


_LEVEL_RULES: Dict[str, Tuple[str, str, str, str]] = {
    "1h": ("1D", "4h", "Day", "4H"),
    "4h": ("1W", "1D", "Week", "Day"),
    "1d": ("1ME", "1W", "Month", "Week"),
}


def _download_cached(symbol: str, interval: str, period: str) -> pd.DataFrame:
    def _fetch() -> pd.DataFrame:
        data = yf.download(
            symbol,
            interval=interval,
            period=period,
            progress=False,
            multi_level_index=False,
            auto_adjust=False,
            session=yf_session(),
        )
        if data.empty:
            return data
        return data.reset_index()

    data = get_cached_dataframe(
        prefix="technical_ohlcv",
        payload={"symbol": symbol.upper(), "interval": interval, "period": period},
        max_age_seconds=MARKET_DATA_CACHE_TTL_SECONDS,
        fetcher=_fetch,
    )

    if data.empty:
        return data

    if "Date" not in data.columns and "Datetime" in data.columns:
        data["Date"] = data["Datetime"]

    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data = data.dropna(subset=["Date"]).set_index("Date")

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
    return data


def _resample_4h(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.resample("4h")
        .agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        })
        .dropna()
    )


def _add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - df["Close"].shift(1)).abs(),
            (df["Low"] - df["Close"].shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    df["XO_Fast"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["XO_Slow"] = df["Close"].ewm(span=25, adjust=False).mean()
    df["XO_Bull"] = (df["XO_Fast"] > df["XO_Slow"]) & (df["XO_Fast"].shift(1) <= df["XO_Slow"].shift(1))
    df["XO_Bear"] = (df["XO_Fast"] < df["XO_Slow"]) & (df["XO_Fast"].shift(1) >= df["XO_Slow"].shift(1))

    rsi = df["RSI"]
    rsi_min = rsi.rolling(14).min()
    rsi_max = rsi.rolling(14).max()
    stoch = 100 * (rsi - rsi_min) / (rsi_max - rsi_min)
    df["StochRSI_K"] = stoch.rolling(3).mean()
    df["StochRSI_D"] = df["StochRSI_K"].rolling(3).mean()

    df["StochRSI_CrossUp"] = (df["StochRSI_K"].shift(1) <= df["StochRSI_D"].shift(1)) & (df["StochRSI_K"] > df["StochRSI_D"])
    df["StochRSI_CrossDown"] = (df["StochRSI_K"].shift(1) >= df["StochRSI_D"].shift(1)) & (df["StochRSI_K"] < df["StochRSI_D"])

    return df


def _prev_high_low(df: pd.DataFrame, rule: str) -> Tuple[float, float]:
    resampled = df["Close"].resample(rule).ohlc()
    if len(resampled) >= 2:
        return float(resampled["high"].iloc[-2]), float(resampled["low"].iloc[-2])
    return float(df["High"].max()), float(df["Low"].min())


def _levels(df: pd.DataFrame, interval: str) -> Dict[str, float]:
    major_rule, minor_rule, major_label, minor_label = _LEVEL_RULES.get(interval, ("1D", "4h", "Day", "4H"))
    major_high, major_low = _prev_high_low(df, major_rule)
    minor_high, minor_low = _prev_high_low(df, minor_rule)
    recent = df.tail(20)

    return {
        f"Prev {major_label} High": major_high,
        f"Prev {major_label} Low": major_low,
        f"Prev {minor_label} High": minor_high,
        f"Prev {minor_label} Low": minor_low,
        "Swing High": float(recent["High"].max()),
        "Swing Low": float(recent["Low"].min()),
    }


def _trend_structure(df: pd.DataFrame) -> str:
    closes = df["Close"].tail(12)
    if len(closes) < 6:
        return "insufficient_data"
    slope = closes.iloc[-1] - closes.iloc[0]
    hh = closes.max() == closes.iloc[-1]
    ll = closes.min() == closes.iloc[-1]

    if slope > 0 and hh:
        return "higher_highs_higher_lows"
    if slope < 0 and ll:
        return "lower_lows_lower_highs"
    return "sideways_or_transition"


def _score_timeframe(df: pd.DataFrame, lvl: Dict[str, float]) -> Tuple[int, str]:
    row = df.iloc[-1]
    score = 0

    ma_bias = "bullish" if row["MA20"] > row["MA50"] else "bearish"
    xo_bias = "bullish" if row["XO_Fast"] > row["XO_Slow"] else "bearish"
    rsi_val = float(row["RSI"])

    score += 1 if ma_bias == "bullish" else -1
    score += 1 if xo_bias == "bullish" else -1

    if rsi_val < 30:
        score += 1
    elif rsi_val > 70:
        score -= 1

    prev_minor_low = next(v for k, v in lvl.items() if "Minor Low" in k or "Day Low" in k or "Week Low" in k)
    prev_minor_high = next(v for k, v in lvl.items() if "Minor High" in k or "Day High" in k or "Week High" in k)

    tol = 0.001
    if prev_minor_low * (1 - tol) <= row["Close"] <= prev_minor_low * (1 + tol):
        score += 1
    if prev_minor_high * (1 - tol) <= row["Close"] <= prev_minor_high * (1 + tol):
        score -= 1

    if score >= 2:
        stance = "BUY"
    elif score <= -2:
        stance = "SELL"
    else:
        stance = "HOLD"

    return score, stance


def _format_timeframe_report(interval: str, df: pd.DataFrame, lvl: Dict[str, float], score: int, stance: str) -> str:
    row = df.iloc[-1]
    xo_recent: List[str] = []
    recent_rows = df.tail(40)
    for ts, r in recent_rows.iterrows():
        if bool(r.get("XO_Bull", False)):
            xo_recent.append(f"XO_BULL @ {ts.strftime('%Y-%m-%d %H:%M')}")
        if bool(r.get("XO_Bear", False)):
            xo_recent.append(f"XO_BEAR @ {ts.strftime('%Y-%m-%d %H:%M')}")
        if bool(r.get("StochRSI_CrossUp", False)):
            xo_recent.append(f"SRSI_UP @ {ts.strftime('%Y-%m-%d %H:%M')}")
        if bool(r.get("StochRSI_CrossDown", False)):
            xo_recent.append(f"SRSI_DOWN @ {ts.strftime('%Y-%m-%d %H:%M')}")

    xo_recent = xo_recent[-6:]

    lines = [
        f"### Timeframe {interval.upper()}",
        f"- Close: {row['Close']:.3f}",
        f"- MA20: {row['MA20']:.3f}",
        f"- MA50: {row['MA50']:.3f}",
        f"- RSI14: {row['RSI']:.2f}",
        f"- XO Fast/Slow: {row['XO_Fast']:.3f} / {row['XO_Slow']:.3f}",
        f"- Stoch RSI K/D: {row['StochRSI_K']:.2f} / {row['StochRSI_D']:.2f}",
        f"- Trend structure: {_trend_structure(df)}",
        f"- Technical score: {score}",
        f"- Timeframe stance: {stance}",
        "- Key Levels:",
    ]

    for name, val in lvl.items():
        lines.append(f"  - {name}: {val:.3f}")

    if xo_recent:
        lines.append("- Recent crossover events:")
        for e in xo_recent:
            lines.append(f"  - {e}")
    else:
        lines.append("- Recent crossover events: none")

    return "\n".join(lines)


def get_technical_analysis(symbol: str, curr_date: str, look_back_days: int = 120) -> str:
    """Generate multi-timeframe technical context inspired by technical_analyst package.

    Returns markdown-like text that an LLM can use for chart-pattern interpretation.
    """
    symbol = symbol.upper()

    df_1h = _download_cached(symbol, interval="1h", period="30d")
    df_1d = _download_cached(symbol, interval="1d", period="180d")

    if df_1h.empty or df_1d.empty:
        return f"No technical data available for {symbol}."

    df_4h = _resample_4h(df_1h)

    frames = {
        "1h": _add_indicators(df_1h.dropna().copy()),
        "4h": _add_indicators(df_4h.dropna().copy()),
        "1d": _add_indicators(df_1d.dropna().copy()),
    }

    sections: List[str] = []
    votes: List[str] = []

    for interval, frame in frames.items():
        frame = frame.dropna().tail(200)
        if len(frame) < 60:
            continue

        lvl = _levels(frame, interval)
        score, stance = _score_timeframe(frame, lvl)
        votes.append(stance)
        sections.append(_format_timeframe_report(interval, frame, lvl, score, stance))

    if not sections:
        return f"Insufficient technical history to analyze {symbol}."

    buy_votes = votes.count("BUY")
    sell_votes = votes.count("SELL")

    if buy_votes > sell_votes:
        aggregate = "BUY"
    elif sell_votes > buy_votes:
        aggregate = "SELL"
    else:
        aggregate = "HOLD"

    summary = [
        f"## Technical Context for {symbol}",
        f"- Date anchor: {curr_date}",
        f"- Vote summary: BUY={buy_votes}, SELL={sell_votes}, HOLD={votes.count('HOLD')}",
        f"- Aggregate technical stance: {aggregate}",
        "",
    ]

    return "\n".join(summary + sections)
