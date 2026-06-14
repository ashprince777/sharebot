import os
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, mean_absolute_error, mean_squared_error

from app.models.stock import StockOHLCV
from app.ml_engine.features import (
    build_feature_dataframe,
    prepare_classification_data,
    prepare_regression_sequences,
)
from app.ml_engine.models import RandomForestWrapper, XGBoostWrapper, LSTMPredictor


# Define model store directory within ml_engine package
SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
os.makedirs(SAVED_MODELS_DIR, exist_ok=True)


def train_and_evaluate_all(candles: list) -> Dict[str, Any]:
    """
    Orchestrates building features, splitting datasets, training Random Forest, 
    XGBoost, and LSTM, calculating evaluation metrics, and saving state artifacts.
    """
    df = build_feature_dataframe(candles)
    if len(df) < 60:
        raise ValueError(f"Insufficient historical candles ({len(df)}) for model training. Minimum required: 60.")

    # Create Train/Test splits (temporal split to prevent leakages)
    split_idx = int(len(df) * 0.8)
    df_train = df.iloc[:split_idx].reset_index(drop=True)
    df_test = df.iloc[split_idx:].reset_index(drop=True)

    results = {}

    # ----------------------------------------------------
    # 1. Train Classification Models (RF & XGBoost)
    # ----------------------------------------------------
    X_train_c, y_train_c, _, scaler_c = prepare_classification_data(df_train)
    # Fit scaler on train, transform test
    X_test_raw_c, y_test_c, _, _ = prepare_classification_data(df_test)
    # Re-apply the classification scaler fit from train
    X_test_c = scaler_c.transform(df_test.dropna(subset=df_train.columns).reset_index(drop=True)[
        ["open", "high", "low", "close", "volume", "rsi", "macd", "macd_signal", "macd_diff", "bb_high", "bb_mid", "bb_low", "ema", "sma", "atr"]
    ].values)
    
    # Adjust arrays to match sizes if needed
    min_len = min(len(X_test_c), len(y_test_c))
    X_test_c = X_test_c[:min_len]
    y_test_c = y_test_c[:min_len]

    # Random Forest
    rf = RandomForestWrapper()
    rf.fit(X_train_c, y_train_c)
    y_pred_rf = rf.predict(X_test_c)
    
    results["random_forest"] = {
        "accuracy": float(accuracy_score(y_test_c, y_pred_rf)),
        "precision": float(precision_score(y_test_c, y_pred_rf, zero_division=0)),
        "recall": float(recall_score(y_test_c, y_pred_rf, zero_division=0)),
        "f1": float(f1_score(y_test_c, y_pred_rf, zero_division=0)),
    }

    # XGBoost
    xgb = XGBoostWrapper()
    xgb.fit(X_train_c, y_train_c)
    y_pred_xgb = xgb.predict(X_test_c)

    results["xgboost"] = {
        "accuracy": float(accuracy_score(y_test_c, y_pred_xgb)),
        "precision": float(precision_score(y_test_c, y_pred_xgb, zero_division=0)),
        "recall": float(recall_score(y_test_c, y_pred_xgb, zero_division=0)),
        "f1": float(f1_score(y_test_c, y_pred_xgb, zero_division=0)),
    }

    # ----------------------------------------------------
    # 2. Train LSTM Regression Model (TensorFlow)
    # ----------------------------------------------------
    seq_length = 15
    X_train_seq, y_train_seq, _, scaler_lstm_f, scaler_lstm_t = prepare_regression_sequences(df_train, seq_length)
    
    # Re-apply the LSTM feature/target scalers to test data
    df_test_cleaned = df_test.copy()
    df_test_cleaned["target"] = df_test_cleaned["close"].shift(-1)
    df_test_cleaned = df_test_cleaned.dropna(subset=df_train.columns.drop("time").tolist() + ["target"]).reset_index(drop=True)
    
    X_test_raw_seq = df_test_cleaned[
        ["open", "high", "low", "close", "volume", "rsi", "macd", "macd_signal", "macd_diff", "bb_high", "bb_mid", "bb_low", "ema", "sma", "atr"]
    ].values
    y_test_raw_seq = df_test_cleaned["target"].values.reshape(-1, 1)

    X_test_scaled_seq = scaler_lstm_f.transform(X_test_raw_seq)
    y_test_scaled_seq = scaler_lstm_t.transform(y_test_raw_seq).flatten()

    X_test_seq = []
    y_test_seq = []
    for i in range(len(df_test_cleaned) - seq_length):
        X_test_seq.append(X_test_scaled_seq[i : i + seq_length])
        y_test_seq.append(y_test_scaled_seq[i + seq_length])

    X_test_seq = np.array(X_test_seq)
    y_test_seq = np.array(y_test_seq)

    lstm = LSTMPredictor(input_shape=(seq_length, X_train_seq.shape[2]))
    lstm.fit(X_train_seq, y_train_seq, epochs=10, batch_size=16)
    
    y_pred_seq_scaled = lstm.predict(X_test_seq)
    y_pred_seq = scaler_lstm_t.inverse_transform(y_pred_seq_scaled.reshape(-1, 1)).flatten()
    
    # Target prices matching predictions
    y_actuals_seq = y_test_raw_seq[seq_length:].flatten()

    results["lstm"] = {
        "mae": float(mean_absolute_error(y_actuals_seq, y_pred_seq)),
        "rmse": float(np.sqrt(mean_squared_error(y_actuals_seq, y_pred_seq))),
    }

    # ----------------------------------------------------
    # 3. Save Artifacts & Persistent States
    # ----------------------------------------------------
    joblib.dump(rf.model, os.path.join(SAVED_MODELS_DIR, "model_rf.joblib"))
    joblib.dump(xgb.model, os.path.join(SAVED_MODELS_DIR, "model_xgb.joblib"))
    joblib.dump(scaler_c, os.path.join(SAVED_MODELS_DIR, "scaler_class.joblib"))
    
    lstm.model.save(os.path.join(SAVED_MODELS_DIR, "model_lstm.keras"))
    joblib.dump(scaler_lstm_f, os.path.join(SAVED_MODELS_DIR, "scaler_lstm_features.joblib"))
    joblib.dump(scaler_lstm_t, os.path.join(SAVED_MODELS_DIR, "scaler_lstm_target.joblib"))

    # Save metrics JSON
    with open(os.path.join(SAVED_MODELS_DIR, "model_metrics.json"), "w") as f:
        json.dump(results, f, indent=4)

    return results
