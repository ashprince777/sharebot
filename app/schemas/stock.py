import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


# Stock Metadata
class StockMetadataBase(BaseModel):
    symbol: str
    series: str = "EQ"
    company_name: str
    isin: str
    industry: Optional[str] = None
    exchange: str = "NSE"
    lot_size: int = 1
    is_active: bool = True


class StockMetadataCreate(StockMetadataBase):
    pass


class StockMetadataResponse(StockMetadataBase):
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)


# OHLCV Data
class StockOHLCVBase(BaseModel):
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    open_interest: Optional[int] = 0


class StockOHLCVCreate(StockOHLCVBase):
    symbol: str
    resolution: str


class StockOHLCVResponse(StockOHLCVBase):
    symbol: str
    resolution: str

    model_config = ConfigDict(from_attributes=True)


# ML Models
class MLModelResponse(BaseModel):
    id: uuid.UUID
    model_name: str
    version: str
    framework: str
    metric_mae: Optional[float] = None
    metric_rmse: Optional[float] = None
    metric_accuracy: Optional[float] = None
    artifacts_path: str
    is_active: bool
    trained_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Model Predictions
class ModelPredictionBase(BaseModel):
    symbol: str
    target_time: datetime
    predicted_value: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    direction: str # 'UP', 'DOWN', 'NEUTRAL'
    confidence_score: float


class ModelPredictionResponse(ModelPredictionBase):
    id: uuid.UUID
    model_id: uuid.UUID
    actual_value: Optional[float] = None
    is_evaluated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Technical Indicators Schema
class IndicatorResponse(BaseModel):
    time: datetime
    close: float
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_diff: Optional[float] = None
    bb_high: Optional[float] = None
    bb_mid: Optional[float] = None
    bb_low: Optional[float] = None
    ema: Optional[float] = None
    sma: Optional[float] = None
    atr: Optional[float] = None


class StockWithIndicators(BaseModel):
    symbol: str
    resolution: str
    indicators: List[IndicatorResponse]


# Backtesting Simulator Schemas
class BacktestRequest(BaseModel):
    strategy: str # "RSI" | "MA_CROSSOVER" | "BOLLINGER_BANDS" | "AI_PREDICT"
    initial_capital: float = 100000.0
    rsi_oversold: float = 35.0
    rsi_overbought: float = 65.0
    ma_fast: int = 20
    ma_slow: int = 50
    confidence_cutoff: float = 70.0

class BacktestTrade(BaseModel):
    type: str # "BUY" | "SELL"
    time: str
    price: float
    shares: float
    capital_after: float

class BacktestEquityPoint(BaseModel):
    time: str
    equity: float

class BacktestResponse(BaseModel):
    symbol: str
    strategy: str
    initial_capital: float
    final_capital: float
    net_profit_pct: float
    total_trades: int
    win_rate_pct: float
    max_drawdown_pct: float
    trades: List[BacktestTrade]
    equity_curve: List[BacktestEquityPoint]

