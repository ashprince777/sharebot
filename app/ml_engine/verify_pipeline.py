import os
import sys
from datetime import datetime, timedelta

# Set parent path so imports resolve cleanly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.models.stock import StockOHLCV
from app.ml_engine.pipeline import train_and_evaluate_all
from app.ml_engine.predict import registry


def generate_mock_candles(count: int = 150) -> list:
    """Helper creating a series of dummy candle models for testing pipeline execution."""
    candles = []
    base_time = datetime.now() - timedelta(days=count)
    
    # Generate simple sine wave trends with random volume noise
    price = 1000.0
    for i in range(count):
        time = base_time + timedelta(days=i)
        change = (i % 20 - 10) * 0.5 + (np_noise := (i % 3 - 1) * 0.2)
        open_p = price
        close_p = price + change
        high_p = max(open_p, close_p) + 0.5
        low_p = min(open_p, close_p) - 0.5
        volume = 10000 + (i % 10) * 1000
        
        # Keep tracking absolute price
        price = close_p

        candle = StockOHLCV(
            time=time,
            symbol="MOCKTICK",
            resolution="1d",
            open=open_p,
            high=high_p,
            low=low_p,
            close=close_p,
            volume=volume,
            open_interest=0,
        )
        candles.append(candle)
    return candles


def run_verification():
    print("[AI ENGINE] ShareBot AI Engine: Starting verification pipeline...")
    candles = generate_mock_candles(500)
    print(f"Generated {len(candles)} mock historical candles.")

    print("\n1. Running training and evaluation pipeline...")
    try:
        metrics = train_and_evaluate_all(candles)
        print("Training succeeded!")
        print("Model metrics output:")
        print(metrics)
    except Exception as e:
        print(f"[ERROR] Pipeline training failed: {str(e)}")
        sys.exit(1)

    print("\n2. Loading models into prediction registry...")
    success = registry.load_models()
    if success:
        print("Registry reloaded model checkpoints successfully.")
    else:
        print("[ERROR] Registry load failed.")
        sys.exit(1)

    print("\n3. Testing prediction functions...")
    try:
        direction_res = registry.predict_direction(candles)
        price_res = registry.predict_price_regression(candles)

        print("\nDirection Classifier Output:")
        print(f"  Model: {direction_res['model_name']}")
        print(f"  Direction: {direction_res['direction']}")
        print(f"  Confidence: {direction_res['confidence_score']:.2f}%")
        print(f"  Is Simulated: {direction_res.get('is_simulated')}")

        print("\nPrice Regression Output:")
        print(f"  Model: {price_res['model_name']}")
        print(f"  Predicted Value: {price_res['predicted_value']:.4f}")
        print(f"  Lower Bound: {price_res.get('lower_bound'):.4f}")
        print(f"  Upper Bound: {price_res.get('upper_bound'):.4f}")
        print(f"  Is Simulated: {price_res.get('is_simulated')}")
        
        print("\n[SUCCESS] Verification pipeline completed successfully with zero errors!")
    except Exception as e:
        print(f"[ERROR] Prediction testing failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run_verification()
