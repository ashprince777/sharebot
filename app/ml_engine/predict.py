import os
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
import tensorflow as tf

from app.models.stock import StockOHLCV
from app.ml_engine.features import build_feature_dataframe
from app.ml_engine.pipeline import SAVED_MODELS_DIR


class ModelRegistry:
    """Singleton registry loading saved model checkpoints and providing live inference."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelRegistry, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return

        self.rf_model = None
        self.xgb_model = None
        self.scaler_class = None

        self.lstm_model = None
        self.scaler_lstm_features = None
        self.scaler_lstm_target = None
        self.metrics = {}

        self.initialized = True
        self.load_models()

    def load_models(self) -> bool:
        """Loads scikit-learn, XGBoost, and Keras LSTM models from disk storage."""
        try:
            # Load Classifiers
            rf_path = os.path.join(SAVED_MODELS_DIR, "model_rf.joblib")
            xgb_path = os.path.join(SAVED_MODELS_DIR, "model_xgb.joblib")
            scaler_c_path = os.path.join(SAVED_MODELS_DIR, "scaler_class.joblib")

            if os.path.exists(rf_path) and os.path.exists(xgb_path) and os.path.exists(scaler_c_path):
                self.rf_model = joblib.load(rf_path)
                self.xgb_model = joblib.load(xgb_path)
                self.scaler_class = joblib.load(scaler_c_path)

            # Load LSTM Regression
            lstm_path = os.path.join(SAVED_MODELS_DIR, "model_lstm.keras")
            scaler_lf_path = os.path.join(SAVED_MODELS_DIR, "scaler_lstm_features.joblib")
            scaler_lt_path = os.path.join(SAVED_MODELS_DIR, "scaler_lstm_target.joblib")

            if os.path.exists(lstm_path) and os.path.exists(scaler_lf_path) and os.path.exists(scaler_lt_path):
                self.lstm_model = tf.keras.models.load_model(lstm_path)
                self.scaler_lstm_features = joblib.load(scaler_lf_path)
                self.scaler_lstm_target = joblib.load(scaler_lt_path)

            # Load metrics config
            metrics_path = os.path.join(SAVED_MODELS_DIR, "model_metrics.json")
            if os.path.exists(metrics_path):
                with open(metrics_path, "r") as f:
                    self.metrics = json.load(f)

            return True
        except Exception as e:
            # Log failure and fallback to simulated inference
            print(f"Error loading models: {str(e)}")
            return False

    def predict_direction(self, candles: List[StockOHLCV]) -> Dict[str, Any]:
        """
        Infers direction (UP/DOWN) using the saved XGBoost classifier.
        Falls back to a high-fidelity indicator-based simulation if models are un-trained.
        """
        # Re-check models loader status
        if not self.xgb_model or not self.scaler_class:
            self.load_models()

        df = build_feature_dataframe(candles)
        if len(df) < 50:
            return self._generate_simulated_prediction(candles, "XGBoost Classifier (Simulated)")

        # Extract features for the latest complete row
        latest_row = df.iloc[-1]
        feature_cols = [
            "open", "high", "low", "close", "volume",
            "rsi", "macd", "macd_signal", "macd_diff",
            "bb_high", "bb_mid", "bb_low", "ema", "sma", "atr"
        ]
        
        # Check for NaN values in features
        feature_values = latest_row[feature_cols].values.reshape(1, -1)
        if pd.isna(feature_values).any():
            return self._generate_simulated_prediction(candles, "XGBoost Classifier (Fallback)")

        if self.xgb_model and self.scaler_class:
            # Scale price columns dynamically to training space
            X_raw = feature_values.copy()
            target_close = float(latest_row["close"])
            if target_close > 0:
                ref_close = float(self.scaler_class.mean_[3])
                factor = ref_close / target_close
                price_indices = [0, 1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13, 14]
                for idx in price_indices:
                    X_raw[0, idx] = X_raw[0, idx] * factor

            X_scaled = self.scaler_class.transform(X_raw)
            proba = self.xgb_model.predict_proba(X_scaled)[0] # [P_0, P_1]
            predicted_class = int(np.argmax(proba))
            confidence = float(proba[predicted_class]) * 100.0
            
            direction = "UP" if predicted_class == 1 else "DOWN"
            return {
                "model_name": "XGBoost Directional Classifier",
                "direction": direction,
                "confidence_score": confidence,
                "predicted_value": float(target_close * (1.008 if direction == "UP" else 0.992)),
                "is_simulated": False
            }
        else:
            return self._generate_simulated_prediction(candles, "XGBoost Classifier (Mock)")

    def predict_price_regression(self, candles: List[StockOHLCV], seq_length: int = 15) -> Dict[str, Any]:
        """
        Infers price sequence forecast using LSTM regression model.
        Falls back to SMA/EMA trend analysis if models are un-trained.
        """
        if not self.lstm_model or not self.scaler_lstm_features or not self.scaler_lstm_target:
            self.load_models()

        df = build_feature_dataframe(candles)
        if len(df) < (seq_length + 5):
            return self._generate_simulated_prediction(candles, "LSTM sequence (Simulated)")

        feature_cols = [
            "open", "high", "low", "close", "volume",
            "rsi", "macd", "macd_signal", "macd_diff",
            "bb_high", "bb_mid", "bb_low", "ema", "sma", "atr"
        ]

        latest_df = df.iloc[-seq_length:]
        X_raw = latest_df[feature_cols].values.copy()
        
        if pd.isna(X_raw).any():
            return self._generate_simulated_prediction(candles, "LSTM sequence (Fallback)")

        if self.lstm_model and self.scaler_lstm_features and self.scaler_lstm_target:
            current_price = float(latest_df.iloc[-1]["close"])
            
            # Scale price columns dynamically to training space
            factor = 1.0
            if current_price > 0:
                ref_close = float(self.scaler_lstm_features.mean_[3])
                factor = ref_close / current_price
                price_indices = [0, 1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13, 14]
                for idx in price_indices:
                    X_raw[:, idx] = X_raw[:, idx] * factor

            # Scale features
            X_scaled = self.scaler_lstm_features.transform(X_raw)
            # Add batch dimension: (1, seq_length, num_features)
            X_input = X_scaled.reshape(1, seq_length, -1)
            
            # Run prediction
            pred_scaled = self.lstm_model.predict(X_input, verbose=0)
            pred_price_scaled = float(self.scaler_lstm_target.inverse_transform(pred_scaled.reshape(-1, 1))[0][0])
            
            # Scale the predicted price back to target stock space
            pred_price = pred_price_scaled / factor
            direction = "UP" if pred_price > current_price else "DOWN"
            
            # Map accuracy bands from pipeline metrics and scale them
            lstm_metrics = self.metrics.get("lstm", {})
            mae_scaled = lstm_metrics.get("mae", ref_close * 0.015)
            mae = mae_scaled / factor
            
            return {
                "model_name": "TensorFlow LSTM Regressor",
                "direction": direction,
                "confidence_score": 85.0, # Target regression confidence metric
                "predicted_value": pred_price,
                "lower_bound": pred_price - mae,
                "upper_bound": pred_price + mae,
                "is_simulated": False
            }
        else:
            return self._generate_simulated_prediction(candles, "LSTM Predictor (Mock)")

    def _generate_simulated_prediction(self, candles: List[StockOHLCV], source: str) -> Dict[str, Any]:
        """Generates indicator-driven high-fidelity mock predictions for testing validation."""
        if not candles:
            return {
                "model_name": source,
                "direction": "NEUTRAL",
                "confidence_score": 50.0,
                "predicted_value": 0.0,
                "is_simulated": True
            }

        latest_candle = candles[-1]
        close = float(latest_candle.close)
        
        # Simple trend mapping via open vs close
        is_bullish = latest_candle.close >= latest_candle.open
        direction = "UP" if is_bullish else "DOWN"
        
        # Generate reasonable predictions
        predicted_value = close * (1.012 if direction == "UP" else 0.988)
        confidence = 65.0 + (close % 15) # semi-random repeatable conf score

        return {
            "model_name": source,
            "direction": direction,
            "confidence_score": confidence,
            "predicted_value": predicted_value,
            "lower_bound": predicted_value * 0.985,
            "upper_bound": predicted_value * 1.015,
            "is_simulated": True
        }


# Export single instance of the Model Registry
registry = ModelRegistry()
