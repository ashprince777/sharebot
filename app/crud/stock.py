from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.stock import StockMetadata, StockOHLCV, MLModel, ModelPrediction
from app.schemas.stock import StockMetadataCreate, StockOHLCVCreate


async def get_stock_metadata(db: AsyncSession, symbol: str) -> Optional[StockMetadata]:
    """Retrieve metadata details for a stock symbol."""
    result = await db.execute(
        select(StockMetadata).where(StockMetadata.symbol == symbol)
    )
    return result.scalars().first()


async def list_active_stocks(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[StockMetadata]:
    """List all active listed stock tickers."""
    result = await db.execute(
        select(StockMetadata)
        .where(StockMetadata.is_active == True)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_stock_metadata(
    db: AsyncSession, obj_in: StockMetadataCreate
) -> StockMetadata:
    """Create a new stock definition."""
    db_obj = StockMetadata(
        symbol=obj_in.symbol.upper(),
        series=obj_in.series,
        company_name=obj_in.company_name,
        isin=obj_in.isin,
        industry=obj_in.industry,
        exchange=obj_in.exchange,
        lot_size=obj_in.lot_size,
        is_active=obj_in.is_active,
    )
    db.add(db_obj)
    await db.flush()
    return db_obj


async def get_ohlcv_history(
    db: AsyncSession,
    symbol: str,
    resolution: str = "1d",
    limit: int = 100,
) -> List[StockOHLCV]:
    """Retrieve historical candle bars sorted chronologically."""
    result = await db.execute(
        select(StockOHLCV)
        .where(
            and_(
                StockOHLCV.symbol == symbol.upper(),
                StockOHLCV.resolution == resolution,
            )
        )
        .order_by(StockOHLCV.time.desc())
        .limit(limit)
    )
    # Return in chronological order
    candles = list(result.scalars().all())
    candles.reverse()
    return candles


async def insert_ohlcv(db: AsyncSession, obj_in: StockOHLCVCreate) -> StockOHLCV:
    """Insert or update (upsert) a single candle bar."""
    # Check if exists
    stmt = select(StockOHLCV).where(
        and_(
            StockOHLCV.symbol == obj_in.symbol,
            StockOHLCV.time == obj_in.time,
            StockOHLCV.resolution == obj_in.resolution,
        )
    )
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        existing.open = obj_in.open
        existing.high = obj_in.high
        existing.low = obj_in.low
        existing.close = obj_in.close
        existing.volume = obj_in.volume
        existing.open_interest = obj_in.open_interest
        db.add(existing)
        await db.flush()
        return existing

    db_obj = StockOHLCV(
        time=obj_in.time,
        symbol=obj_in.symbol,
        resolution=obj_in.resolution,
        open=obj_in.open,
        high=obj_in.high,
        low=obj_in.low,
        close=obj_in.close,
        volume=obj_in.volume,
        open_interest=obj_in.open_interest,
    )
    db.add(db_obj)
    await db.flush()
    return db_obj


# ML Model queries
async def get_active_model(db: AsyncSession, model_name: str) -> Optional[MLModel]:
    """Get active model binary metadata by model type name."""
    result = await db.execute(
        select(MLModel).where(
            and_(MLModel.model_name == model_name, MLModel.is_active == True)
        )
    )
    return result.scalars().first()


# Predictions
async def get_latest_predictions(
    db: AsyncSession, symbol: str, limit: int = 10
) -> List[ModelPrediction]:
    """Get recent model forecasts for a ticker."""
    result = await db.execute(
        select(ModelPrediction)
        .where(ModelPrediction.symbol == symbol.upper())
        .order_by(ModelPrediction.target_time.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def save_prediction(db: AsyncSession, pred_obj: ModelPrediction) -> ModelPrediction:
    """Save an AI inference prediction output."""
    db.add(pred_obj)
    await db.flush()
    return pred_obj
