import pandas as pd
import numpy as np
from typing import List
from app.models.stock import StockOHLCV
from app.schemas.stock import IndicatorResponse

# Import indicators from the ta library
import ta.momentum
import ta.trend
import ta.volatility


def calculate_technical_indicators(candles: List[StockOHLCV]) -> List[IndicatorResponse]:
    """
    Calculate RSI, MACD, Bollinger Bands, EMA, SMA, and ATR using the 'ta' library.
    Expects candles in chronological order.
    """
    if len(candles) < 2:
        # Not enough data to compute indicators
        return [
            IndicatorResponse(
                time=c.time,
                close=float(c.close),
                rsi=None,
                macd=None,
                macd_signal=None,
                macd_diff=None,
                bb_high=None,
                bb_mid=None,
                bb_low=None,
                ema=None,
                sma=None,
                atr=None,
            )
            for c in candles
        ]

    # Convert list of StockOHLCV to DataFrame
    data = []
    for c in candles:
        data.append(
            {
                "time": c.time,
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": int(c.volume),
            }
        )

    df = pd.DataFrame(data)

    # Convert numeric columns explicitly
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["open"] = df["open"].astype(float)

    # 1. RSI
    try:
        df["rsi"] = ta.momentum.rsi(df["close"], window=14)
    except Exception:
        df["rsi"] = np.nan

    # 2. MACD
    try:
        df["macd"] = ta.trend.macd(df["close"])
        df["macd_signal"] = ta.trend.macd_signal(df["close"])
        df["macd_diff"] = ta.trend.macd_diff(df["close"])
    except Exception:
        df["macd"] = np.nan
        df["macd_signal"] = np.nan
        df["macd_diff"] = np.nan

    # 3. Bollinger Bands
    try:
        df["bb_high"] = ta.volatility.bollinger_hband(df["close"])
        df["bb_mid"] = ta.volatility.bollinger_mavg(df["close"])
        df["bb_low"] = ta.volatility.bollinger_lband(df["close"])
    except Exception:
        df["bb_high"] = np.nan
        df["bb_mid"] = np.nan
        df["bb_low"] = np.nan

    # 4. EMA (20) & SMA (50)
    try:
        df["ema"] = ta.trend.ema_indicator(df["close"], window=20)
    except Exception:
        df["ema"] = np.nan

    try:
        df["sma"] = ta.trend.sma_indicator(df["close"], window=50)
    except Exception:
        df["sma"] = np.nan

    # 5. ATR (14)
    try:
        df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
    except Exception:
        df["atr"] = np.nan

    # Clean NaNs by replacing with None
    df = df.replace({np.nan: None})

    results = []
    for _, row in df.iterrows():
        results.append(
            IndicatorResponse(
                time=row["time"],
                close=row["close"],
                rsi=row["rsi"],
                macd=row["macd"],
                macd_signal=row["macd_signal"],
                macd_diff=row["macd_diff"],
                bb_high=row["bb_high"],
                bb_mid=row["bb_mid"],
                bb_low=row["bb_low"],
                ema=row["ema"],
                sma=row["sma"],
                atr=row["atr"],
            )
        )

    return results
