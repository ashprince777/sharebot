import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "../services/api.ts";
import DashboardLayout from "../components/DashboardLayout.tsx";
import { 
  TrendingUp, 
  Briefcase, 
  RefreshCw,
  AlertCircle
} from "lucide-react";

interface Holding {
  symbol: string;
  qty: number;
  avgPrice: number;
  currentPrice: number;
}

interface PortfolioState {
  cash: number;
  holdings: Holding[];
}

const DEFAULT_PORTFOLIO_IN: PortfolioState = {
  cash: 1000000.0, // Start with 10 Lakhs INR paper cash
  holdings: [
    { symbol: "RELIANCE", qty: 50, avgPrice: 2380.0, currentPrice: 2450.0 },
    { symbol: "TCS", qty: 20, avgPrice: 3750.0, currentPrice: 3820.0 },
    { symbol: "HDFCBANK", qty: 100, avgPrice: 1480.0, currentPrice: 1520.0 },
  ],
};

const DEFAULT_PORTFOLIO_US: PortfolioState = {
  cash: 10000.0, // Start with $10,000 USD paper cash
  holdings: [
    { symbol: "AAPL", qty: 10, avgPrice: 175.0, currentPrice: 180.0 },
    { symbol: "TSLA", qty: 5, avgPrice: 240.0, currentPrice: 245.0 },
  ],
};

const Portfolio: React.FC = () => {
  const activeMarket = localStorage.getItem("sb_active_market") || "IN";
  const currencySymbol = activeMarket === "US" ? "$" : "₹";
  const portfolioStorageKey = activeMarket === "US" ? "sb_portfolio_us" : "sb_portfolio_in";
  const defaultPortfolio = activeMarket === "US" ? DEFAULT_PORTFOLIO_US : DEFAULT_PORTFOLIO_IN;

  const [portfolio, setPortfolio] = useState<PortfolioState>(() => {
    try {
      const stored = localStorage.getItem(portfolioStorageKey);
      return stored ? JSON.parse(stored) : defaultPortfolio;
    } catch {
      return defaultPortfolio;
    }
  });

  const [tradeSymbol, setTradeSymbol] = useState(activeMarket === "US" ? "AAPL" : "RELIANCE");
  const [tradeQty, setTradeQty] = useState(10);
  const [tradeAction, setTradeAction] = useState<"BUY" | "SELL">("BUY");
  const [tradeError, setTradeError] = useState<string | null>(null);

  // Sync with localStorage
  const savePortfolio = (updated: PortfolioState) => {
    setPortfolio(updated);
    localStorage.setItem(portfolioStorageKey, JSON.stringify(updated));
  };

  // 1. Fetch available stocks dynamically
  const { data: stocksList } = useQuery<any[]>({
    queryKey: ["stocks"],
    queryFn: async () => {
      const res = await api.get("/stocks/");
      return res.data;
    }
  });

  const filteredStocks = React.useMemo(() => {
    if (!stocksList) return [];
    if (activeMarket === "US") {
      return stocksList.filter(s => s.exchange === "NASDAQ" || s.exchange === "NYSE");
    } else {
      return stocksList.filter(s => s.exchange === "NSE" || !s.exchange);
    }
  }, [stocksList, activeMarket]);

  // 2. Fetch prices for the active trade symbol and holdings
  const symbolsToFetch = Array.from(new Set([tradeSymbol, ...portfolio.holdings.map((h) => h.symbol)]));

  const { data: pricesMap } = useQuery<Record<string, number>>({
    queryKey: ["portfolioPrices", symbolsToFetch],
    queryFn: async () => {
      const map: Record<string, number> = {};
      await Promise.all(
        symbolsToFetch.map(async (sym) => {
          try {
            const res = await api.get(`/stocks/${sym}/history?resolution=1d&limit=1`);
            if (res.data && res.data.length > 0) {
              map[sym] = res.data[res.data.length - 1].close;
            } else {
              map[sym] = 100.0;
            }
          } catch {
            map[sym] = 100.0;
          }
        })
      );
      return map;
    },
    refetchInterval: 15000,
  });

  const getTickerPrice = (sym: string) => {
    return pricesMap?.[sym] || 100.0;
  };

  const handleExecuteTrade = (e: React.FormEvent) => {
    e.preventDefault();
    setTradeError(null);

    const price = getTickerPrice(tradeSymbol);
    const cost = price * tradeQty;

    if (tradeAction === "BUY") {
      if (portfolio.cash < cost) {
        setTradeError("Insufficient cash balance for this purchase.");
        return;
      }

      // Add or update holding
      const holdings = [...portfolio.holdings];
      const index = holdings.findIndex((h) => h.symbol === tradeSymbol);

      if (index >= 0) {
        const h = holdings[index];
        const newQty = h.qty + tradeQty;
        const newAvg = (h.qty * h.avgPrice + cost) / newQty;
        holdings[index] = { ...h, qty: newQty, avgPrice: newAvg, currentPrice: price };
      } else {
        holdings.push({ symbol: tradeSymbol, qty: tradeQty, avgPrice: price, currentPrice: price });
      }

      savePortfolio({
        cash: portfolio.cash - cost,
        holdings,
      });
    } else {
      // SELL Action
      const holdings = [...portfolio.holdings];
      const index = holdings.findIndex((h) => h.symbol === tradeSymbol);

      if (index < 0 || holdings[index].qty < tradeQty) {
        setTradeError("You do not hold enough shares to execute this sale.");
        return;
      }

      const h = holdings[index];
      const newQty = h.qty - tradeQty;
      const credit = price * tradeQty;

      if (newQty === 0) {
        holdings.splice(index, 1);
      } else {
        holdings[index] = { ...h, qty: newQty, currentPrice: price };
      }

      savePortfolio({
        cash: portfolio.cash + credit,
        holdings,
      });
    }
  };

  // Calculate stats
  const updatedHoldings = portfolio.holdings.map((h) => ({
    ...h,
    currentPrice: getTickerPrice(h.symbol),
  }));

  const holdingsValue = updatedHoldings.reduce((sum, h) => sum + h.qty * h.currentPrice, 0);
  const totalValue = portfolio.cash + holdingsValue;
  const initialCostValue = portfolio.holdings.reduce((sum, h) => sum + h.qty * h.avgPrice, 0);
  const totalPnl = holdingsValue - initialCostValue;
  const pnlPercent = initialCostValue > 0 ? (totalPnl / initialCostValue) * 100 : 0;

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        
        {/* Header HUD */}
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-100">Virtual Paper Trading</h2>
          <p className="text-xs text-slate-400 mt-1">
            Simulate {activeMarket === "US" ? "US" : "Indian"} equity trades to validate model prediction accuracy with zero capital risk.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-surface border border-border p-4 rounded-xl flex items-center justify-between">
            <div>
              <span className="block text-[10px] text-slate-500 font-bold uppercase tracking-wider">Total Net Worth</span>
              <span className="text-lg font-black tracking-tight mt-1 block">{currencySymbol}{totalValue.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
            </div>
            <Briefcase className="text-primary opacity-60" size={24} />
          </div>

          <div className="bg-surface border border-border p-4 rounded-xl flex items-center justify-between">
            <div>
              <span className="block text-[10px] text-slate-500 font-bold uppercase tracking-wider">Holding Value</span>
              <span className="text-lg font-black tracking-tight mt-1 block">{currencySymbol}{holdingsValue.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
            </div>
            <TrendingUp className="text-purple-400 opacity-60" size={24} />
          </div>

          <div className="bg-surface border border-border p-4 rounded-xl flex items-center justify-between">
            <div>
              <span className="block text-[10px] text-slate-500 font-bold uppercase tracking-wider">Available Cash</span>
              <span className="text-lg font-black tracking-tight mt-1 block">{currencySymbol}{portfolio.cash.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
            </div>
            <span className="text-xl opacity-60">💰</span>
          </div>

          <div className="bg-surface border border-border p-4 rounded-xl flex items-center justify-between">
            <div>
              <span className="block text-[10px] text-slate-500 font-bold uppercase tracking-wider">Unrealized P&L</span>
              <span className={`text-lg font-black tracking-tight mt-1 block ${totalPnl >= 0 ? "text-bullish" : "text-bearish"}`}>
                {totalPnl >= 0 ? "+" : ""}{currencySymbol}{totalPnl.toFixed(2)} ({pnlPercent.toFixed(2)}%)
              </span>
            </div>
            <span className="text-xl opacity-60">{totalPnl >= 0 ? "🟢" : "🔴"}</span>
          </div>
        </div>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Holdings List */}
          <div className="flex-1 bg-surface border border-border rounded-xl overflow-hidden">
            <div className="p-4 border-b border-border flex justify-between items-center bg-slate-900/10">
              <h3 className="text-sm font-bold text-slate-200">Current Stock Positions</h3>
              <button 
                onClick={() => savePortfolio(defaultPortfolio)}
                className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1.5"
              >
                <RefreshCw size={12} />
                Reset Portfolio
              </button>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border bg-slate-900/30 text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                    <th className="py-3.5 px-6">Ticker</th>
                    <th className="py-3.5 px-6 text-right">Shares</th>
                    <th className="py-3.5 px-6 text-right">Avg. Buy Price</th>
                    <th className="py-3.5 px-6 text-right">Current Price</th>
                    <th className="py-3.5 px-6 text-right">Position Value</th>
                    <th className="py-3.5 px-6 text-right">Profit / Loss</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60 text-xs">
                  {updatedHoldings.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-slate-500">
                        No active stock holdings. Use the trade ticket to purchase shares.
                      </td>
                    </tr>
                  ) : (
                    updatedHoldings.map((h) => {
                      const cost = h.qty * h.avgPrice;
                      const value = h.qty * h.currentPrice;
                      const pnl = value - cost;
                      const pct = cost > 0 ? (pnl / cost) * 100 : 0;
                      return (
                        <tr key={h.symbol} className="hover:bg-slate-800/10 transition-colors">
                          <td className="py-4 px-6 font-extrabold text-slate-200">{h.symbol}</td>
                          <td className="py-4 px-6 text-right font-medium">{h.qty}</td>
                          <td className="py-4 px-6 text-right text-slate-400">{currencySymbol}{h.avgPrice.toFixed(2)}</td>
                          <td className="py-4 px-6 text-right text-slate-200">{currencySymbol}{h.currentPrice.toFixed(2)}</td>
                          <td className="py-4 px-6 text-right font-bold text-slate-200">{currencySymbol}{value.toFixed(2)}</td>
                          <td className={`py-4 px-6 text-right font-bold ${pnl >= 0 ? "text-bullish" : "text-bearish"}`}>
                            {pnl >= 0 ? "+" : ""}{currencySymbol}{pnl.toFixed(2)} ({pct.toFixed(2)}%)
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Trade Ticket Form */}
          <div className="w-full lg:w-80 shrink-0 bg-surface border border-border p-5 rounded-xl self-start glow-blue">
            <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2">
              🎫 Order Ticket
            </h3>

            {tradeError && (
              <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/30 text-rose-400 rounded-lg text-xs flex gap-2">
                <AlertCircle size={15} className="shrink-0" />
                <span>{tradeError}</span>
              </div>
            )}

            <form onSubmit={handleExecuteTrade} className="space-y-4">
              {/* Action Toggle */}
              <div className="grid grid-cols-2 gap-2 p-1 bg-slate-900 border border-border rounded-xl">
                <button
                  type="button"
                  onClick={() => setTradeAction("BUY")}
                  className={`py-2 px-3 rounded-lg text-xs font-extrabold transition-all ${
                    tradeAction === "BUY"
                      ? "bg-emerald-500 text-slate-950 font-black glow-green"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  BUY
                </button>
                <button
                  type="button"
                  onClick={() => setTradeAction("SELL")}
                  className={`py-2 px-3 rounded-lg text-xs font-extrabold transition-all ${
                    tradeAction === "SELL"
                      ? "bg-rose-500 text-slate-950 font-black glow-red"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  SELL
                </button>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                  Select Stock
                </label>
                <select
                  value={tradeSymbol}
                  onChange={(e) => setTradeSymbol(e.target.value)}
                  className="w-full p-3 bg-slate-900/60 border border-border rounded-xl text-slate-200 focus:outline-none focus:border-primary text-xs"
                >
                  {filteredStocks?.map((s) => {
                    const price = getTickerPrice(s.symbol);
                    return (
                      <option key={s.symbol} value={s.symbol}>
                        {s.symbol} ({currencySymbol}{price.toFixed(2)}) - {s.company_name}
                      </option>
                    );
                  })}
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                  Quantity (Shares)
                </label>
                <input
                  type="number"
                  required
                  min={1}
                  value={tradeQty}
                  onChange={(e) => setTradeQty(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-full p-3 bg-slate-900/60 border border-border rounded-xl text-slate-200 focus:outline-none focus:border-primary text-xs"
                />
              </div>

              <div className="bg-slate-900/40 p-4 rounded-xl border border-border/60 text-xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-500">Order Type:</span>
                  <span className="font-semibold text-slate-300">Market Price</span>
                </div>
                <div className="flex justify-between border-t border-border/40 pt-2 font-bold text-sm">
                  <span className="text-slate-400">Estimated cost:</span>
                  <span className={tradeAction === "BUY" ? "text-slate-100" : "text-slate-100"}>
                    {currencySymbol}{(getTickerPrice(tradeSymbol) * tradeQty).toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                  </span>
                </div>
              </div>

              <button
                type="submit"
                className={`w-full py-3 px-4 rounded-xl text-xs font-black transition-all flex items-center justify-center gap-2 ${
                  tradeAction === "BUY"
                    ? "bg-emerald-500 text-slate-950 hover:bg-emerald-600"
                    : "bg-rose-500 text-slate-950 hover:bg-rose-600"
                }`}
              >
                Execute {tradeAction} Order
              </button>
            </form>
          </div>
        </div>

      </div>
    </DashboardLayout>
  );
};

export default Portfolio;
