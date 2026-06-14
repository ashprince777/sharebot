import uuid
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class StockMetadata(Base):
    __tablename__ = "stock_metadata"

    symbol: Mapped[str] = mapped_column(String(50), primary_key=True)
    series: Mapped[str] = mapped_column(String(10), nullable=False, default="EQ")
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    isin: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    industry: Mapped[str] = mapped_column(String(100), nullable=True)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False, default="NSE")
    lot_size: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_updated: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    ohlcv_data: Mapped[list["StockOHLCV"]] = relationship(
        "StockOHLCV", back_populates="stock", cascade="all, delete-orphan"
    )
    predictions: Mapped[list["ModelPrediction"]] = relationship(
        "ModelPrediction", back_populates="stock", cascade="all, delete-orphan"
    )


class StockOHLCV(Base):
    __tablename__ = "stock_ohlcv"

    time: Mapped[DateTime] = mapped_column(DateTime(timezone=True), primary_key=True)
    symbol: Mapped[str] = mapped_column(
        String(50), ForeignKey("stock_metadata.symbol", ondelete="CASCADE"), primary_key=True
    )
    resolution: Mapped[str] = mapped_column(String(10), primary_key=True) # '1m', '5m', '15m', '1d'
    open: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    open_interest: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    stock: Mapped["StockMetadata"] = relationship("StockMetadata", back_populates="ohlcv_data")


class MLModel(Base):
    __tablename__ = "ml_models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    framework: Mapped[str] = mapped_column(String(50), nullable=False) # 'XGBoost', 'TensorFlow'
    metric_mae: Mapped[float] = mapped_column(Numeric(10, 6), nullable=True)
    metric_rmse: Mapped[float] = mapped_column(Numeric(10, 6), nullable=True)
    metric_accuracy: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)
    artifacts_path: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    trained_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    predictions: Mapped[list["ModelPrediction"]] = relationship(
        "ModelPrediction", back_populates="model", cascade="all, delete-orphan"
    )


class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol: Mapped[str] = mapped_column(
        String(50), ForeignKey("stock_metadata.symbol", ondelete="CASCADE"), nullable=False
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ml_models.id", ondelete="CASCADE"), nullable=False
    )
    target_time: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    predicted_value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    lower_bound: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True)
    upper_bound: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False) # 'UP', 'DOWN', 'NEUTRAL'
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    actual_value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True)
    is_evaluated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    stock: Mapped["StockMetadata"] = relationship("StockMetadata", back_populates="predictions")
    model: Mapped["MLModel"] = relationship("MLModel", back_populates="predictions")
