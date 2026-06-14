import numpy as np
from typing import Tuple

# Standard sklearn & xgboost models
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb

# TensorFlow / Keras imports
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout


class RandomForestWrapper:
    """Wrapper around scikit-learn RandomForestClassifier."""

    def __init__(self, n_estimators: int = 100, max_depth: int = 6):
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=-1
        )

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)


class XGBoostWrapper:
    """Wrapper around XGBoost Classifier."""

    def __init__(self, n_estimators: int = 100, max_depth: int = 5, learning_rate: float = 0.05):
        self.model = xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=42,
            n_jobs=-1,
            eval_metric="logloss"
        )

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)


class LSTMPredictor:
    """Sequence model wrapping TensorFlow Keras Sequential architecture for close price regression."""

    def __init__(self, input_shape: Tuple[int, int]):
        self.model = Sequential([
            LSTM(64, input_shape=input_shape, return_sequences=True),
            Dropout(0.2),
            LSTM(32, return_sequences=False),
            Dropout(0.2),
            Dense(16, activation="relu"),
            Dense(1)
        ])
        
        # Compile with Adam optimizer and Mean Squared Error loss
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss="mse",
            metrics=["mae"]
        )

    def fit(self, X: np.ndarray, y: np.ndarray, epochs: int = 15, batch_size: int = 32, validation_split: float = 0.1):
        return self.model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            verbose=0 # Quiet training run
        )

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X, verbose=0)
