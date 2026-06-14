import React, { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import api from "../services/api.ts";
import DashboardLayout from "../components/DashboardLayout.tsx";
import { 
  Play, 
  TrendingUp, 
  Percent, 
  Activity, 
  Briefcase, 
  AlertCircle,
  BarChart2
} from "lucide-react";

interface StockItem {
  symbol: string;
  company_name: string;
  isin: string;
  industry: string;
  exchange?: string;
}

interface Trade {
  type: string;
  time: string;
  price: number;
  shares: number;
  capital_after: number;
}

interface EquityPoint {
  time: string;
  equity: number;
}

interface BacktestResponse {
  symbol: string;
  strategy: string;
  initial_capital: number;
  final_capital: number;
  net_profit_pct: number;
  total_trades: number;
  win_rate_pct: number;
  max_drawdown_pct: number;
  trades: Trade[];
  equity_curve: EquityPoint[];
}

const Backtester: React.FC = () => {
  const activeMarket = localStorage.getItem("sb_active_market") || "IN";
  const currencySymbol = activeMarket === "US" ? "$" : "₹";
  const [activeSymbol, setActiveSymbol] = useState(activeMarket === "US" ? "AAPL" : "RELIANCE");
  const [strategy, setStrategy] = useState("RSI");
  const [initialCapital, setInitialCapital] = useState(activeMarket === "US" ? 10000 : 100000);
  const [rsiOversold, setRsiOversold] = useState(35);
  const [rsiOverbought, setRsiOverbought] = useState(65);
  const [maFast, setMaFast] = useState(20);
  const [maSlow, setMaSlow] = useState(50);
  const [confidenceCutoff, setConfidenceCutoff] = useState(70);

  // 1. Fetch available stocks
  const { data: stocksList, isLoading: stocksLoading } = useQuery<StockItem[]>({
    queryKey: ["stocks"],
    queryFn: async () => {
      const res = await api.get("/stocks/");
      return res.data;
    },
  });

  const filteredStocks = React.useMemo(() => {
    if (!stocksList) return [];
    if (activeMarket === "US") {
      return stocksList.filter(s => s.exchange === "NASDAQ" || s.exchange === "NYSE");
    } else {
      return stocksList.filter(s => s.exchange === "NSE" || !s.exchange);
    }
  }, [stocksList, activeMarket]);

  // 2. Backtest Mutation
  const backtestMutation = useMutation<BacktestResponse, any, any>({
    mutationFn: async () => {
      const payload = {
        strategy,
        initial_capital: initialCapital,
        rsi_oversold: rsiOversold,
        rsi_overbought: rsiOverbought,
        ma_fast: maFast,
        ma_slow: maSlow,
        confidence_cutoff: confidenceCutoff
      };
      const res = await api.post(`/stocks/${activeSymbol}/backtest`, payload);
      return res.data;
    }
  });

  const handleRunBacktest = (e: React.FormEvent) => {
    e.preventDefault();
    backtestMutation.mutate({});
  };

  const results = backtestMutation.data;

  // Custom SVG Equity Chart Logic
  const renderEquityChart = () => {
    if (!results || !results.equity_curve || results.equity_curve.length === 0) return null;

    const curve = results.equity_curve;
    const equities = curve.map((c) => c.equity);
    const maxEq = Math.max(...equities);
    const minEq = Math.min(...equities);
    const eqRange = maxEq - minEq || 1;

    // Dimensions
    const width = 800;
    const height = 220;
    const padding = 15;
    const scaleY = (height - padding * 2) / eqRange;
    const scaleX = (width - padding * 2) / (curve.length - 1 || 1);

    const getX = (idx: number) => padding + idx * scaleX;
    const getY = (val: number) => height - padding - (val - minEq) * scaleY;

    // Build SVG Path
    const points = curve.map((pt, idx) => `${getX(idx)},${getY(pt.equity)}`);
    const linePath = `M ${points.join(" L ")}`;
    
    // Gradient Path
    const areaPath = `${linePath} L ${getX(curve.length - 1)},${height - padding} L ${getX(0)},${height - padding} Z`;

    return (
      <div className="bg-slate-900/30 border border-border p-4 rounded-xl">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Equity Growth Curve</span>
          <span className="text-[10px] text-slate-500">
            {curve[0].time} to {curve[curve.length - 1].time}
          </span>
        </div>
        
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto select-none">
          <defs>
            <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0.25, 0.5, 0.75].map((p, idx) => {
            const y = height * p;
            return (
              <line
                key={idx}
                x1={padding}
                y1={y}
                x2={width - padding}
                y2={y}
                stroke="#1e293b"
                strokeWidth={1}
                strokeDasharray="4,4"
              />
            );
          })}

          {/* Filled Area */}
          <path d={areaPath} fill="url(#equityGrad)" stroke="none" />

          {/* Line */}
          <path d={linePath} fill="none" stroke="#3b82f6" strokeWidth={2.5} strokeLinecap="round" />

          {/* Start and End nodes */}
          <circle cx={getX(0)} cy={getY(equities[0])} r={4} fill="#1e293b" stroke="#3b82f6" strokeWidth={2} />
          <circle cx={getX(curve.length - 1)} cy={getY(equities[equities.length - 1])} r={4} fill="#1e293b" stroke="#3b82f6" strokeWidth={2} />
        </svg>
      </div>
    );
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        
        {/* Header Panel */}
        <div className="bg-surface border border-border p-6 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <BarChart2 className="text-primary" size={22} />
              AI Backtesting Simulator
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Test technical and machine learning strategies over 2 years of daily data.
            </p>
          </div>
        </div>

        <div className="flex flex-col lg:flex-row gap-6">
          
          {/* Settings Left Column */}
          <form onSubmit={handleRunBacktest} className="w-full lg:w-80 shrink-0 flex flex-col gap-6">
            <div className="bg-surface border border-border p-5 rounded-xl space-y-4">
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wide border-b border-border pb-3">
                Simulation Setup
              </h3>

              {/* Ticker Selector */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Select Stock</label>
                <select
                  value={activeSymbol}
                  onChange={(e) => setActiveSymbol(e.target.value)}
                  className="w-full bg-slate-900 border border-border rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-primary"
                >
                  {stocksLoading ? (
                    <option>Loading stocks...</option>
                  ) : (
                    filteredStocks?.map((s) => (
                      <option key={s.symbol} value={s.symbol}>
                        {s.symbol} - {s.company_name}
                      </option>
                    ))
                  )}
                </select>
              </div>

              {/* Strategy Type */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Trading Strategy</label>
                <select
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="w-full bg-slate-900 border border-border rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-primary"
                >
                  <option value="RSI">RSI Oversold / Overbought</option>
                  <option value="MA_CROSSOVER">Fast EMA / Slow SMA Crossover</option>
                  <option value="BOLLINGER_BANDS">Bollinger Bands Breakout</option>
                  <option value="AI_PREDICT">AI Directional Predictor Model</option>
                </select>
              </div>

              {/* Initial Capital */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Initial Capital ({currencySymbol})</label>
                <input
                  type="number"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-border rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-primary"
                />
              </div>

              {/* Dynamic Strategy Settings */}
              {strategy === "RSI" && (
                <div className="space-y-3 pt-2 border-t border-border/60">
                  <div className="flex justify-between text-[10px] uppercase font-bold text-slate-500">
                    <span>RSI Oversold Limit</span>
                    <span className="text-primary">{rsiOversold}</span>
                  </div>
                  <input
                    type="range"
                    min="15"
                    max="45"
                    value={rsiOversold}
                    onChange={(e) => setRsiOversold(Number(e.target.value))}
                    className="w-full accent-primary"
                  />
                  <div className="flex justify-between text-[10px] uppercase font-bold text-slate-500">
                    <span>RSI Overbought Limit</span>
                    <span className="text-primary">{rsiOverbought}</span>
                  </div>
                  <input
                    type="range"
                    min="55"
                    max="85"
                    value={rsiOverbought}
                    onChange={(e) => setRsiOverbought(Number(e.target.value))}
                    className="w-full accent-primary"
                  />
                </div>
              )}

              {strategy === "MA_CROSSOVER" && (
                <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border/60">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Fast EMA</label>
                    <input
                      type="number"
                      value={maFast}
                      onChange={(e) => setMaFast(Number(e.target.value))}
                      className="w-full bg-slate-900 border border-border rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-primary"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Slow SMA</label>
                    <input
                      type="number"
                      value={maSlow}
                      onChange={(e) => setMaSlow(Number(e.target.value))}
                      className="w-full bg-slate-900 border border-border rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-primary"
                    />
                  </div>
                </div>
              )}

              {strategy === "AI_PREDICT" && (
                <div className="space-y-3 pt-2 border-t border-border/60">
                  <div className="flex justify-between text-[10px] uppercase font-bold text-slate-500">
                    <span>Model Confidence Cutoff</span>
                    <span className="text-primary">{confidenceCutoff}%</span>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="90"
                    value={confidenceCutoff}
                    onChange={(e) => setConfidenceCutoff(Number(e.target.value))}
                    className="w-full accent-primary"
                  />
                  <p className="text-[10px] text-slate-500 leading-normal">
                    Filters trades to only execute when XGBoost Classifier confidence matches or exceeds this percentage.
                  </p>
                </div>
              )}

              <button
                type="submit"
                disabled={backtestMutation.isPending}
                className="w-full bg-primary hover:bg-primary/95 text-white font-bold py-3 px-4 rounded-xl text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50 mt-4 shadow-lg shadow-primary/10"
              >
                <Play size={14} fill="currentColor" />
                {backtestMutation.isPending ? "Simulating Trades..." : "Run Backtest Simulation"}
              </button>
            </div>
          </form>

          {/* Results Main Section */}
          <div className="flex-1 flex flex-col gap-6">
            
            {/* If no backtest run yet */}
            {!results && !backtestMutation.isPending && (
              <div className="h-full min-h-[350px] flex flex-col items-center justify-center bg-surface border border-border rounded-xl p-8 text-center">
                <BarChart2 size={36} className="text-slate-600 mb-3" />
                <h4 className="text-sm font-bold text-slate-300">Ready to Simulate</h4>
                <p className="text-xs text-slate-500 max-w-xs mt-1 leading-normal">
                  Configure strategy parameters on the left and trigger the simulation.
                </p>
              </div>
            )}

            {/* Loading Indicator */}
            {backtestMutation.isPending && (
              <div className="h-full min-h-[350px] flex flex-col items-center justify-center bg-surface border border-border rounded-xl p-8 text-center">
                <Activity size={32} className="text-primary animate-spin mb-3" />
                <h4 className="text-sm font-bold text-slate-300">Evaluating Historical Signals</h4>
                <p className="text-xs text-slate-500 max-w-xs mt-1 leading-normal">
                  Scanning over 500 candles and simulating trade executions step-by-step...
                </p>
              </div>
            )}

            {/* Simulation Results HUD */}
            {results && !backtestMutation.isPending && (
              <div className="space-y-6">
                
                {/* Metrics Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {/* PNL Badge */}
                  <div className="bg-surface border border-border p-4 rounded-xl relative overflow-hidden">
                    <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">Net P&amp;L %</span>
                    <span className={`text-xl font-black ${
                      results.net_profit_pct >= 0 ? "text-bullish" : "text-bearish"
                    }`}>
                      {results.net_profit_pct >= 0 ? "+" : ""}{results.net_profit_pct.toFixed(2)}%
                    </span>
                    <div className="absolute top-2 right-2 opacity-10">
                      <TrendingUp size={24} />
                    </div>
                  </div>

                  {/* Final Valuation */}
                  <div className="bg-surface border border-border p-4 rounded-xl relative overflow-hidden">
                    <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">Final Capital</span>
                    <span className="text-xl font-black text-slate-100">
                      {currencySymbol}{results.final_capital.toFixed(2)}
                    </span>
                    <div className="absolute top-2 right-2 opacity-10">
                      <Briefcase size={24} />
                    </div>
                  </div>

                  {/* Win Rate */}
                  <div className="bg-surface border border-border p-4 rounded-xl relative overflow-hidden">
                    <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">Win Rate</span>
                    <span className="text-xl font-black text-slate-100">
                      {results.win_rate_pct.toFixed(1)}%
                    </span>
                    <div className="absolute top-2 right-2 opacity-10">
                      <Percent size={22} />
                    </div>
                  </div>

                  {/* Drawdown */}
                  <div className="bg-surface border border-border p-4 rounded-xl relative overflow-hidden">
                    <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">Max Drawdown</span>
                    <span className="text-xl font-black text-bearish">
                      -{results.max_drawdown_pct.toFixed(1)}%
                    </span>
                    <div className="absolute top-2 right-2 opacity-10">
                      <AlertCircle size={22} />
                    </div>
                  </div>
                </div>

                {/* Equity Curve Component */}
                {renderEquityChart()}

                {/* Trade Log Panel */}
                <div className="bg-surface border border-border rounded-xl overflow-hidden">
                  <div className="p-4 border-b border-border flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                      Strategy Trades ({results.total_trades})
                    </h3>
                  </div>

                  <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-border bg-slate-900/30 text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                          <th className="py-3 px-5">Type</th>
                          <th className="py-3 px-5">Date</th>
                          <th className="py-3 px-5 text-right">Price</th>
                          <th className="py-3 px-5 text-right">Shares</th>
                          <th className="py-3 px-5 text-right">Remaining cash</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/60 text-xs">
                        {results.trades.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="py-8 text-center text-slate-500">
                              No trades executed by this strategy on this ticker.
                            </td>
                          </tr>
                        ) : (
                          results.trades.map((t, idx) => (
                            <tr key={idx} className="hover:bg-slate-800/10 transition-colors">
                              <td className="py-3.5 px-5">
                                <span className={`px-2 py-0.5 rounded-full font-black text-[9px] ${
                                  t.type === "BUY"
                                    ? "bg-emerald-500/10 text-bullish border border-emerald-500/20"
                                    : t.type === "SELL"
                                      ? "bg-rose-500/10 text-bearish border border-rose-500/20"
                                      : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                }`}>
                                  {t.type}
                                </span>
                              </td>
                              <td className="py-3.5 px-5 text-slate-300">{t.time}</td>
                              <td className="py-3.5 px-5 text-right font-semibold text-slate-200">
                                {currencySymbol}{t.price.toFixed(2)}
                              </td>
                              <td className="py-3.5 px-5 text-right text-slate-400">
                                {t.shares.toFixed(1)}
                              </td>
                              <td className="py-3.5 px-5 text-right font-semibold text-slate-200">
                                {currencySymbol}{t.capital_after.toFixed(2)}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>
            )}

          </div>

        </div>

      </div>
    </DashboardLayout>
  );
};

export default Backtester;
