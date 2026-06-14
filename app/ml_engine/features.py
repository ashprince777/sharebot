import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Any
from sklearn.preprocessing import StandardScaler
from app.models.stock import StockOHLCV
from app.services.indicators import calculate_technical_indicators


def build_feature_dataframe(candles: List[StockOHLCV]) -> pd.DataFrame:
    """
    Consolidates raw candles and calculated indicators into a single pandas DataFrame.
    """
    if not candles:
        return pd.DataFrame()

    # Calculate indicators
    indicator_results = calculate_technical_indicators(candles)

    # Convert to DataFrames
    candles_data = [
        {
            "time": c.time,
            "open": float(c.open),
            "high": float(c.high),
            "low": float(c.low),
            "close": float(c.close),
            "volume": int(c.volume),
        }
        for c in candles
    ]
    df_candles = pd.DataFrame(candles_data)

    indicators_data = [
        {
            "time": ind.time,
            "rsi": ind.rsi,
            "macd": ind.macd,
            "macd_signal": ind.macd_signal,
            "macd_diff": ind.macd_diff,
            "bb_high": ind.bb_high,
            "bb_mid": ind.bb_mid,
            "bb_low": ind.bb_low,
            "ema": ind.ema,
            "sma": ind.sma,
            "atr": ind.atr,
        }
        for ind in indicator_results
    ]
    df_inds = pd.DataFrame(indicators_data)

    # Merge on time
    df = pd.merge(df_candles, df_inds, on="time")
    df = df.sort_values("time").reset_index(drop=True)
    return df


def prepare_classification_data(
    df: pd.DataFrame, return_threshold: float = 0.002
) -> Tuple[np.ndarray, np.ndarray, List[str], StandardScaler]:
    """
    Prepares features (X) and binary labels (y) for XGBoost and Random Forest.
    Target: 1 if close price increases by >= return_threshold on the next bar, else 0.
    """
    if len(df) < 50:
        raise ValueError("Insufficient data points to build feature matrices.")

    df = df.copy()

    # Define features
    feature_cols = [
        "open", "high", "low", "close", "volume",
        "rsi", "macd", "macd_signal", "macd_diff",
        "bb_high", "bb_mid", "bb_low", "ema", "sma", "atr"
    ]

    # Target: 1 if next close > current close * (1 + return_threshold), else 0
    df["target"] = (df["close"].shift(-1) > df["close"] * (1.0 + return_threshold)).astype(int)

    # Drop rows with NaNs (due to MA lookback or target shift)
    df_cleaned = df.dropna(subset=feature_cols + ["target"]).reset_index(drop=True)

    X = df_cleaned[feature_cols].values
    y = df_cleaned["target"].values

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return X_scaled, y, feature_cols, scaler


def prepare_regression_sequences(
    df: pd.DataFrame, seq_length: int = 15
) -> Tuple[np.ndarray, np.ndarray, List[str], StandardScaler, StandardScaler]:
    """
    Prepares sequential inputs (X) and numeric price targets (y) for LSTM.
    X shape: (num_samples, seq_length, num_features)
    y shape: (num_samples,)
    """
    if len(df) < (seq_length + 50):
        raise ValueError("Insufficient data points to build sequential LSTM matrices.")

    df = df.copy()

    # Define features
    feature_cols = [
        "open", "high", "low", "close", "volume",
        "rsi", "macd", "macd_signal", "macd_diff",
        "bb_high", "bb_mid", "bb_low", "ema", "sma", "atr"
    ]

    # Target: Next closing price
    df["target"] = df["close"].shift(-1)

    # Drop NaNs
    df_cleaned = df.dropna(subset=feature_cols + ["target"]).reset_index(drop=True)

    X_raw = df_cleaned[feature_cols].values
    y_raw = df_cleaned["target"].values.reshape(-1, 1)

    # Scale features and targets independently
    feature_scaler = StandardScaler()
    X_scaled = feature_scaler.fit_transform(X_raw)

    target_scaler = StandardScaler()
    y_scaled = target_scaler.fit_transform(y_raw).flatten()

    # Construct sequences
    X_seq = []
    y_seq = []

    for i in range(len(df_cleaned) - seq_length):
        X_seq.append(X_scaled[i : i + seq_length])
        y_seq.append(y_scaled[i + seq_length])

    return np.array(X_seq), np.array(y_seq), feature_cols, feature_scaler, target_scaler
