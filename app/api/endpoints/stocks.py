from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.core.database import get_db
from app.crud import stock as crud_stock
from app.models.user import User
from app.models.stock import ModelPrediction
from app.schemas.stock import (
    StockMetadataCreate,
    StockMetadataResponse,
    StockOHLCVCreate,
    StockOHLCVResponse,
    StockWithIndicators,
    ModelPredictionResponse,
    ModelPredictionBase,
    BacktestRequest,
    BacktestResponse,
)
from app.services.indicators import calculate_technical_indicators
from app.services.telegram import send_telegram_message

router = APIRouter()


@router.get("/", response_model=List[StockMetadataResponse])
async def read_stocks(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 1000,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Retrieve all active listed stocks."""
    stocks = await crud_stock.list_active_stocks(db, skip=skip, limit=limit)
    return stocks


@router.post("/", response_model=StockMetadataResponse, status_code=status.HTTP_201_CREATED)
async def create_stock(
    *,
    db: AsyncSession = Depends(get_db),
    stock_in: StockMetadataCreate,
    current_user: User = Depends(deps.get_current_admin_user),
) -> Any:
    """Register a new stock ticker (Admin only)."""
    stock = await crud_stock.get_stock_metadata(db, symbol=stock_in.symbol)
    if stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock with this symbol already registered",
        )
    new_stock = await crud_stock.create_stock_metadata(db, obj_in=stock_in)
    return new_stock


@router.post("/update-live", status_code=status.HTTP_200_OK)
async def update_live_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Fetch the latest actual stock candles from Yahoo Finance and update the database."""
    import yfinance as yf
    from datetime import timezone
    
    stocks = await crud_stock.list_active_stocks(db)
    if not stocks:
        return {"status": "success", "updated_count": 0, "message": "No active stocks found"}

    updated_symbols = []
    for stock in stocks:
        symbol = stock.symbol
        try:
            if getattr(stock, "exchange", "NSE") in ["NASDAQ", "NYSE"]:
                ticker_ns = symbol
            else:
                ticker_ns = "MSTCLTD.NS" if symbol == "MSTC" else f"{symbol}.NS"
            ticker = yf.Ticker(ticker_ns)
            hist = ticker.history(period="7d", interval="1d")
            hist = hist.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
            
            for timestamp, row in hist.iterrows():
                if timestamp.tzinfo is not None:
                    candle_time = timestamp.tz_convert(timezone.utc).to_pydatetime()
                else:
                    candle_time = timestamp.replace(tzinfo=timezone.utc).to_pydatetime()
                
                candle_in = StockOHLCVCreate(
                    time=candle_time,
                    symbol=symbol,
                    resolution="1d",
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                    open_interest=0
                )
                await crud_stock.insert_ohlcv(db, obj_in=candle_in)
            
            updated_symbols.append(symbol)
        except Exception as e:
            pass
            
    await db.commit()
    return {
        "status": "success", 
        "updated_count": len(updated_symbols), 
        "updated_symbols": updated_symbols
    }


@router.get("/{symbol}", response_model=StockMetadataResponse)
async def read_stock_detail(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Retrieve details for a specific stock."""
    stock = await crud_stock.get_stock_metadata(db, symbol=symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock symbol not found",
        )
    return stock


@router.get("/{symbol}/history", response_model=List[StockOHLCVResponse])
async def read_stock_history(
    symbol: str,
    resolution: str = "1d",
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Retrieve historical price candles (OHLCV)."""
    stock = await crud_stock.get_stock_metadata(db, symbol=symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock symbol not found",
        )
    history = await crud_stock.get_ohlcv_history(
        db, symbol=symbol, resolution=resolution, limit=limit
    )
    return history


@router.post("/{symbol}/history", response_model=StockOHLCVResponse)
async def add_stock_candle(
    symbol: str,
    *,
    db: AsyncSession = Depends(get_db),
    candle_in: StockOHLCVCreate,
    current_user: User = Depends(deps.get_current_admin_user),
) -> Any:
    """Insert or upsert a new candle bar (Admin only)."""
    if candle_in.symbol.upper() != symbol.upper():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Symbol path parameter does not match payload",
        )
    stock = await crud_stock.get_stock_metadata(db, symbol=symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock symbol not registered. Register stock metadata first.",
        )
    candle = await crud_stock.insert_ohlcv(db, obj_in=candle_in)
    return candle


@router.get("/{symbol}/indicators", response_model=StockWithIndicators)
async def read_technical_indicators(
    symbol: str,
    resolution: str = "1d",
    limit: int = Query(150, ge=50, le=500), # Need enough history for RSI (14) / MACD / Moving Averages
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Retrieve dynamic, pandas-calculated technical indicators (RSI, MACD, BB, etc.)."""
    stock = await crud_stock.get_stock_metadata(db, symbol=symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock symbol not found",
        )
    
    history = await crud_stock.get_ohlcv_history(
        db, symbol=symbol, resolution=resolution, limit=limit
    )
    
    indicators = calculate_technical_indicators(history)
    
    return StockWithIndicators(
        symbol=symbol.upper(),
        resolution=resolution,
        indicators=indicators
    )


@router.get("/{symbol}/predictions", response_model=List[ModelPredictionResponse])
async def read_stock_predictions(
    symbol: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Retrieve historical prediction outputs for a stock."""
    stock = await crud_stock.get_stock_metadata(db, symbol=symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock symbol not found",
        )
    
    predictions = await crud_stock.get_latest_predictions(db, symbol=symbol, limit=limit)
    return predictions


@router.post("/{symbol}/predictions", response_model=ModelPredictionResponse)
async def add_stock_prediction(
    symbol: str,
    *,
    db: AsyncSession = Depends(get_db),
    prediction_in: ModelPredictionBase,
    model_id: str = Query(...),
    current_user: User = Depends(deps.get_current_admin_user),
) -> Any:
    """Save model inference predictions to DB (Admin only)."""
    if prediction_in.symbol.upper() != symbol.upper():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Symbol path parameter does not match payload",
        )
    
    # Save the prediction
    db_obj = ModelPrediction(
        symbol=symbol.upper(),
        model_id=prediction_in.model_id if hasattr(prediction_in, 'model_id') else model_id,
        target_time=prediction_in.target_time,
        predicted_value=prediction_in.predicted_value,
        lower_bound=prediction_in.lower_bound,
        upper_bound=prediction_in.upper_bound,
        direction=prediction_in.direction.upper(),
        confidence_score=prediction_in.confidence_score,
    )
    saved = await crud_stock.save_prediction(db, pred_obj=db_obj)
    return saved


@router.get("/{symbol}/forecast")
async def get_stock_forecast(
    symbol: str,
    horizon: str = Query("1d", pattern="^(1d)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Run active ML models (XGBoost Classifier + TensorFlow LSTM sequence regressor)
    to compute target close prices and direction classifications.
    """
    stock = await crud_stock.get_stock_metadata(db, symbol=symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock symbol not found",
        )
    
    # Retrieve last 100 historical candles (needed for indicators & LSTM 15-day sequence)
    candles = await crud_stock.get_ohlcv_history(db, symbol=symbol, resolution="1d", limit=100)
    
    from app.ml_engine.predict import registry
    
    # Run predictions
    dir_res = registry.predict_direction(candles)
    price_res = registry.predict_price_regression(candles)
    
    return {
        "symbol": symbol.upper(),
        "direction": dir_res["direction"],
        "confidence_score": dir_res["confidence_score"],
        "predicted_value": price_res["predicted_value"],
        "lower_bound": price_res.get("lower_bound"),
        "upper_bound": price_res.get("upper_bound"),
        "classifier_model": dir_res["model_name"],
        "regressor_model": price_res["model_name"],
        "is_simulated": dir_res.get("is_simulated", False) or price_res.get("is_simulated", False)
    }


@router.post("/{symbol}/alert")
async def trigger_stock_alert(
    symbol: str,
    message: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Trigger a manual/automatic Telegram alert for a specific symbol."""
    stock = await crud_stock.get_stock_metadata(db, symbol=symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock symbol not found",
        )
    
    formatted_msg = (
        f"🚨 <b>ShareBot Stock Alert</b> 🚨\n"
        f"<b>Ticker:</b> #{stock.symbol} ({stock.company_name})\n"
        f"<b>Triggered By:</b> {current_user.full_name or current_user.email}\n"
        f"<b>Message:</b> {message}"
    )
    
    success = await send_telegram_message(formatted_msg)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to dispatch message to Telegram. Check credentials."
        )
        
    return {"status": "success", "detail": f"Alert successfully dispatched for {symbol}"}


@router.post("/{symbol}/backtest", response_model=BacktestResponse)
async def run_stock_backtest(
    symbol: str,
    backtest_in: BacktestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Run a technical indicators or AI prediction backtest simulation on historical daily candles."""
    import pandas as pd
    import numpy as np
    import ta.momentum
    import ta.trend
    import ta.volatility
    from app.ml_engine.predict import registry

    stock = await crud_stock.get_stock_metadata(db, symbol=symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock symbol not found",
        )

    # Fetch daily historical candles up to 500
    history = await crud_stock.get_ohlcv_history(
        db, symbol=symbol, resolution="1d", limit=500
    )
    if len(history) < 60:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient candles available for backtesting (found {len(history)}, need at least 60)",
        )

    # Sort historical data chronologically
    history_sorted = sorted(history, key=lambda x: x.time)

    # Convert to pandas DataFrame for quick indicator computation
    df = pd.DataFrame([{
        "time": c.time.strftime("%Y-%m-%d"),
        "open": float(c.open),
        "high": float(c.high),
        "low": float(c.low),
        "close": float(c.close),
        "volume": int(c.volume)
    } for c in history_sorted])

    # Compute technical indicators
    try:
        df["rsi"] = ta.momentum.rsi(df["close"], window=14)
    except Exception:
        df["rsi"] = np.nan

    try:
        df["ema_fast"] = ta.trend.ema_indicator(df["close"], window=backtest_in.ma_fast)
    except Exception:
        df["ema_fast"] = np.nan

    try:
        df["sma_slow"] = ta.trend.sma_indicator(df["close"], window=backtest_in.ma_slow)
    except Exception:
        df["sma_slow"] = np.nan

    try:
        df["bb_high"] = ta.volatility.bollinger_hband(df["close"])
        df["bb_low"] = ta.volatility.bollinger_lband(df["close"])
    except Exception:
        df["bb_high"] = np.nan
        df["bb_low"] = np.nan

    # Clean NaNs by replacing with None
    df = df.replace({np.nan: None})

    # Simulation engine parameters
    initial_capital = backtest_in.initial_capital
    capital = initial_capital
    position = 0.0
    entry_price = 0.0
    trades = []
    equity_curve = []

    # Trading starts from index 50 to allow indicators to populate
    start_idx = 50
    wins = 0
    losses = 0

    for i in range(start_idx, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        close_price = row["close"]
        time_str = row["time"]

        buy_signal = False
        sell_signal = False

        if backtest_in.strategy == "RSI":
            rsi = row["rsi"]
            prev_rsi = prev_row["rsi"]
            if rsi is not None and prev_rsi is not None:
                buy_signal = rsi < backtest_in.rsi_oversold
                sell_signal = rsi > backtest_in.rsi_overbought

        elif backtest_in.strategy == "MA_CROSSOVER":
            fast = row["ema_fast"]
            slow = row["sma_slow"]
            prev_fast = prev_row["ema_fast"]
            prev_slow = prev_row["sma_slow"]
            if fast is not None and slow is not None and prev_fast is not None and prev_slow is not None:
                buy_signal = prev_fast <= prev_slow and fast > slow
                sell_signal = prev_fast >= prev_slow and fast < slow

        elif backtest_in.strategy == "BOLLINGER_BANDS":
            bb_low = row["bb_low"]
            bb_high = row["bb_high"]
            if bb_low is not None and bb_high is not None:
                buy_signal = close_price < bb_low
                sell_signal = close_price > bb_high

        elif backtest_in.strategy == "AI_PREDICT":
            # Pass chronological subset of candles up to this index
            sub_candles = history_sorted[:i+1]
            pred = registry.predict_direction(sub_candles)
            direction = pred["direction"]
            confidence = pred["confidence_score"]
            if confidence >= backtest_in.confidence_cutoff:
                buy_signal = direction == "UP"
                sell_signal = direction == "DOWN"

        # Execute Buy/Sell Actions
        if position == 0.0 and buy_signal:
            # BUY (all-in)
            shares = capital / close_price
            position = shares
            entry_price = close_price
            capital = 0.0
            trades.append({
                "type": "BUY",
                "time": time_str,
                "price": close_price,
                "shares": shares,
                "capital_after": 0.0
            })
        elif position > 0.0 and sell_signal:
            # SELL (liquidate all)
            capital = position * close_price
            pnl = close_price - entry_price
            if pnl > 0:
                wins += 1
            else:
                losses += 1
            trades.append({
                "type": "SELL",
                "time": time_str,
                "price": close_price,
                "shares": position,
                "capital_after": capital
            })
            position = 0.0

        # Daily Equity Calculation
        daily_val = capital + (position * close_price)
        equity_curve.append({
            "time": time_str,
            "equity": daily_val
        })

    # Liquidate remaining position on the last day if still holding
    if position > 0.0:
        final_capital = position * df.iloc[-1]["close"]
        pnl = df.iloc[-1]["close"] - entry_price
        if pnl > 0:
            wins += 1
        else:
            losses += 1
        trades.append({
            "type": "LIQUIDATE",
            "time": df.iloc[-1]["time"],
            "price": df.iloc[-1]["close"],
            "shares": position,
            "capital_after": final_capital
        })
    else:
        final_capital = capital

    net_profit_pct = ((final_capital - initial_capital) / initial_capital) * 100.0
    total_trades = len(trades)
    
    total_closed = wins + losses
    win_rate_pct = (wins / total_closed) * 100.0 if total_closed > 0 else 0.0

    # Max Drawdown
    max_equity = initial_capital
    max_dd = 0.0
    for pt in equity_curve:
        eq = pt["equity"]
        if eq > max_equity:
            max_equity = eq
        dd = ((max_equity - eq) / max_equity) * 100.0
        if dd > max_dd:
            max_dd = dd

    return {
        "symbol": symbol.upper(),
        "strategy": backtest_in.strategy,
        "initial_capital": initial_capital,
        "final_capital": final_capital,
        "net_profit_pct": net_profit_pct,
        "total_trades": total_trades,
        "win_rate_pct": win_rate_pct,
        "max_drawdown_pct": max_dd,
        "trades": trades,
        "equity_curve": equity_curve,
    }

