import React from "react";

interface CandleData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface IndicatorData {
  time: string;
  close: number;
  rsi: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_diff: number | null;
  bb_high: number | null;
  bb_mid: number | null;
  bb_low: number | null;
  ema: number | null;
  sma: number | null;
  atr: number | null;
}

interface ChartProps {
  candles: CandleData[];
  indicators: IndicatorData[];
  livePrice?: number | null;
}

const StockChart: React.FC<ChartProps> = ({ candles, indicators, livePrice }) => {
  const [hoverIndex, setHoverIndex] = React.useState<number | null>(null);

  const displayCandles = React.useMemo(() => {
    if (!candles || candles.length === 0) return [];
    if (!livePrice) return candles;

    const copy = [...candles];
    const last = { ...copy[copy.length - 1] };
    last.close = livePrice;
    if (livePrice > last.high) last.high = livePrice;
    if (livePrice < last.low) last.low = livePrice;
    copy[copy.length - 1] = last;
    return copy;
  }, [candles, livePrice]);

  if (!displayCandles || displayCandles.length === 0) {
    return (
      <div className="h-96 flex items-center justify-center bg-slate-900/50 border border-border rounded-xl">
        <p className="text-slate-500">No chart data available</p>
      </div>
    );
  }

  // Width & height settings
  const width = 800;
  const priceHeight = 260;
  const indicatorHeight = 100;
  const gap = 20;
  const totalHeight = priceHeight + gap + indicatorHeight;

  // Find price bounds
  const prices = displayCandles.flatMap((c) => [c.high, c.low]);
  
  // Include Bollinger Bands in price bounds if available
  const activeIndicators = indicators || [];
  const bbHighs = activeIndicators.map((ind) => ind.bb_high).filter((v): v is number => v !== null);
  const bbLows = activeIndicators.map((ind) => ind.bb_low).filter((v): v is number => v !== null);

  let maxPrice = Math.max(...prices);
  let minPrice = Math.min(...prices);

  if (bbHighs.length > 0) maxPrice = Math.max(maxPrice, ...bbHighs);
  if (bbLows.length > 0) minPrice = Math.min(minPrice, ...bbLows);

  const priceRange = maxPrice - minPrice;
  const padding = priceRange * 0.05; // 5% padding
  const priceMaxY = maxPrice + padding;
  const priceMinY = minPrice - padding;
  const priceScale = priceHeight / (priceMaxY - priceMinY);

  const getPriceY = (val: number) => {
    return priceHeight - (val - priceMinY) * priceScale;
  };

  // Bar spacing
  const barWidth = width / displayCandles.length;
  const barSpacing = Math.max(2, barWidth * 0.2);

  // Compute SVG paths for indicators
  const getLinePath = (getField: (ind: IndicatorData) => number | null | undefined) => {
    const points = activeIndicators
      .map((ind, idx) => {
        const val = getField(ind);
        if (val === null || val === undefined) return null;
        const x = idx * barWidth + barWidth / 2;
        const y = getPriceY(val);
        return `${x},${y}`;
      })
      .filter((p): p is string => p !== null);

    return points.length > 0 ? `M ${points.join(" L ")}` : "";
  };

  // Bollinger Bands Area Path
  const getBBAreaPath = () => {
    const topPoints: string[] = [];
    const bottomPoints: string[] = [];

    activeIndicators.forEach((ind, idx) => {
      const x = idx * barWidth + barWidth / 2;
      if (ind.bb_high !== null && ind.bb_low !== null) {
        topPoints.push(`${x},${getPriceY(ind.bb_high)}`);
        bottomPoints.unshift(`${x},${getPriceY(ind.bb_low)}`); // reverse order for bottom loop
      }
    });

    if (topPoints.length === 0) return "";
    return `M ${topPoints.join(" L ")} L ${bottomPoints.join(" L ")} Z`;
  };

  // RSI scale (0 to 100)
  const getRsiY = (val: number) => {
    const rsiMin = 0;
    const rsiMax = 100;
    return priceHeight + gap + indicatorHeight - ((val - rsiMin) / (rsiMax - rsiMin)) * indicatorHeight;
  };

  const getRsiPath = () => {
    const points = activeIndicators
      .map((ind, idx) => {
        if (ind.rsi === null || ind.rsi === undefined) return null;
        const x = idx * barWidth + barWidth / 2;
        const y = getRsiY(ind.rsi);
        return `${x},${y}`;
      })
      .filter((p): p is string => p !== null);

    return points.length > 0 ? `M ${points.join(" L ")}` : "";
  };

  // Active Candle hover detail
  const activeIndex = hoverIndex !== null ? hoverIndex : displayCandles.length - 1;
  const activeCandle = displayCandles[activeIndex];
  const activeIndicator = activeIndicators[activeIndex];

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="w-full bg-surface border border-border rounded-xl p-4 glow-blue">
      {/* Legend / Hover Metadata HUD */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 mb-4 text-xs bg-slate-900/40 p-3 rounded-lg border border-border">
        <div>
          <span className="text-slate-400 font-semibold mr-1">TIME:</span>
          <span className="text-slate-200">{formatDate(activeCandle.time)}</span>
        </div>
        <div className="flex gap-3">
          <div>
            <span className="text-slate-400 mr-1">O:</span>
            <span className="text-slate-100 font-semibold">{activeCandle.open.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-slate-400 mr-1">H:</span>
            <span className="text-slate-100 font-semibold text-bullish">{activeCandle.high.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-slate-400 mr-1">L:</span>
            <span className="text-slate-100 font-semibold text-bearish">{activeCandle.low.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-slate-400 mr-1">C:</span>
            <span className={`font-bold ${activeCandle.close >= activeCandle.open ? "text-bullish" : "text-bearish"}`}>
              {activeCandle.close.toFixed(2)}
            </span>
          </div>
        </div>
        
        {activeIndicator && (
          <div className="flex flex-wrap gap-x-4 border-l border-slate-700 pl-4">
            {activeIndicator.rsi && (
              <span className="text-purple-400 font-semibold">RSI(14): {activeIndicator.rsi.toFixed(1)}</span>
            )}
            {activeIndicator.ema && (
              <span className="text-amber-400 font-semibold">EMA(20): {activeIndicator.ema.toFixed(1)}</span>
            )}
            {activeIndicator.sma && (
              <span className="text-primary font-semibold">SMA(50): {activeIndicator.sma.toFixed(1)}</span>
            )}
          </div>
        )}
      </div>

      {/* SVG Canvas */}
      <div className="relative w-full">
        <svg
          viewBox={`0 0 ${width} ${totalHeight}`}
          className="w-full h-auto select-none"
          onMouseMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const percentage = x / rect.width;
            const index = Math.floor(percentage * displayCandles.length);
            if (index >= 0 && index < displayCandles.length) {
              setHoverIndex(index);
            }
          }}
          onMouseLeave={() => setHoverIndex(null)}
        >
          {/* Grids */}
          {/* Price grid lines */}
          {[0.25, 0.5, 0.75].map((p, i) => {
            const y = priceHeight * p;
            return (
              <line
                key={`p-grid-${i}`}
                x1={0}
                y1={y}
                x2={width}
                y2={y}
                stroke="#1e293b"
                strokeWidth={1}
                strokeDasharray="4,4"
              />
            );
          })}

          {/* Indicator grid lines */}
          <line
            x1={0}
            y1={getRsiY(30)}
            x2={width}
            y2={getRsiY(30)}
            stroke="rgba(244, 63, 94, 0.3)"
            strokeWidth={1}
            strokeDasharray="4,4"
          />
          <line
            x1={0}
            y1={getRsiY(70)}
            x2={width}
            y2={getRsiY(70)}
            stroke="rgba(16, 185, 129, 0.3)"
            strokeWidth={1}
            strokeDasharray="4,4"
          />

          {/* Bollinger Bands Shaded Area */}
          {getBBAreaPath() && (
            <path
              d={getBBAreaPath()}
              fill="rgba(14, 165, 233, 0.05)"
              stroke="none"
            />
          )}

          {/* BB upper, middle, lower lines */}
          {getLinePath((ind) => ind.bb_high) && (
            <path
              d={getLinePath((ind) => ind.bb_high)}
              fill="none"
              stroke="#0ea5e9"
              strokeWidth={1}
              strokeDasharray="2,2"
              opacity={0.6}
            />
          )}
          {getLinePath((ind) => ind.bb_low) && (
            <path
              d={getLinePath((ind) => ind.bb_low)}
              fill="none"
              stroke="#0ea5e9"
              strokeWidth={1}
              strokeDasharray="2,2"
              opacity={0.6}
            />
          )}

          {/* Moving Averages (EMA 20 - Amber, SMA 50 - Sky Blue) */}
          {getLinePath((ind) => ind.ema) && (
            <path
              d={getLinePath((ind) => ind.ema)}
              fill="none"
              stroke="#f59e0b"
              strokeWidth={1.5}
            />
          )}
          {getLinePath((ind) => ind.sma) && (
            <path
              d={getLinePath((ind) => ind.sma)}
              fill="none"
              stroke="#0ea5e9"
              strokeWidth={1.5}
            />
          )}

          {/* Candlesticks */}
          {displayCandles.map((candle, idx) => {
            const isBullish = candle.close >= candle.open;
            const x = idx * barWidth + barWidth / 2;
            const wickY1 = getPriceY(candle.high);
            const wickY2 = getPriceY(candle.low);
            
            const bodyY1 = getPriceY(Math.max(candle.open, candle.close));
            const bodyY2 = getPriceY(Math.min(candle.open, candle.close));
            const bodyHeight = Math.max(1, bodyY2 - bodyY1);

            return (
              <g key={`candle-${idx}`} opacity={hoverIndex === null || hoverIndex === idx ? 1 : 0.4}>
                {/* Wick */}
                <line
                  x1={x}
                  y1={wickY1}
                  x2={x}
                  y2={wickY2}
                  stroke={isBullish ? "#10b981" : "#f43f5e"}
                  strokeWidth={1.5}
                />
                {/* Body */}
                <rect
                  x={x - (barWidth - barSpacing) / 2}
                  y={bodyY1}
                  width={barWidth - barSpacing}
                  height={bodyHeight}
                  fill={isBullish ? "#10b981" : "#f43f5e"}
                  stroke={isBullish ? "#10b981" : "#f43f5e"}
                  rx={1}
                />
              </g>
            );
          })}

          {/* RSI Indicator chart */}
          {getRsiPath() && (
            <path
              d={getRsiPath()}
              fill="none"
              stroke="#a855f7"
              strokeWidth={1.5}
            />
          )}

          {/* Vertical Hover Line */}
          {hoverIndex !== null && (
            <line
              x1={hoverIndex * barWidth + barWidth / 2}
              y1={0}
              x2={hoverIndex * barWidth + barWidth / 2}
              y2={totalHeight}
              stroke="#475569"
              strokeWidth={1}
              strokeDasharray="3,3"
            />
          )}
        </svg>
      </div>
    </div>
  );
};

export default StockChart;
