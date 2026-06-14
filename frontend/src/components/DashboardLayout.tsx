import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { 
  TrendingUp, 
  Search, 
  Briefcase, 
  LogOut, 
  User as UserIcon, 
  Menu, 
  X, 
  Bell,
  Play 
} from "lucide-react";
import { logout } from "../store/authSlice.ts";
import { RootState } from "../store/index.ts";

interface LayoutProps {
  children: React.ReactNode;
}

const DashboardLayout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { user } = useSelector((state: RootState) => state.auth);
  
  const [sidebarOpen, setSidebarOpen] = React.useState(false);

  const navigation = [
    { name: "Trading Terminal", href: "/dashboard", icon: TrendingUp },
    { name: "AI Scanner", href: "/scanner", icon: Search },
    { name: "Virtual Portfolio", href: "/portfolio", icon: Briefcase },
    { name: "AI Backtester", href: "/backtester", icon: Play },
  ];

  const handleLogout = () => {
    dispatch(logout());
    navigate("/login");
  };

  const activeMarket = localStorage.getItem("sb_active_market") || "IN";

  const isMarketOpen = () => {
    const now = new Date();
    if (activeMarket === "US") {
      // US Market: Mon-Fri 9:30 AM to 4:00 PM EST (UTC-5 / UTC-4)
      const estTime = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }));
      const day = estTime.getDay();
      const hours = estTime.getHours();
      const minutes = estTime.getMinutes();
      const timeVal = hours * 100 + minutes;
      return day >= 1 && day <= 5 && timeVal >= 930 && timeVal <= 1600;
    } else {
      // Convert to IST
      const istOffset = 330; // 5 hours 30 mins
      const utc = now.getTime() + now.getTimezoneOffset() * 60000;
      const istTime = new Date(utc + istOffset * 60000);
      
      const day = istTime.getDay();
      const hours = istTime.getHours();
      const minutes = istTime.getMinutes();
      const timeVal = hours * 100 + minutes;

      // NSE hours: Mon-Fri 9:15 AM (915) to 3:30 PM (1530)
      return day >= 1 && day <= 5 && timeVal >= 915 && timeVal <= 1530;
    }
  };

  return (
    <div className="min-h-screen bg-background flex text-slate-100">
      {/* Sidebar for Desktop */}
      <aside className="hidden md:flex flex-col w-64 bg-surface border-r border-border shrink-0">
        <div className="h-16 flex items-center px-6 border-b border-border">
          <Link to="/" className="flex items-center gap-2 font-bold text-lg text-primary">
            <span className="text-2xl">📈</span>
            <span>ShareBot <span className="text-xs text-accent">{activeMarket === "US" ? "US" : "AI"}</span></span>
          </Link>
        </div>
        
        <nav className="flex-1 px-4 py-6 space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon;
            const active = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                  active 
                    ? "bg-primary/10 text-primary border-l-2 border-primary" 
                    : "text-slate-400 hover:bg-slate-800/40 hover:text-slate-200"
                }`}
              >
                <Icon size={18} />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* User profile / Logout */}
        <div className="p-4 border-t border-border flex flex-col gap-3">
          <div className="flex items-center gap-3 px-2">
            <div className="w-9 h-9 rounded-full bg-slate-800 flex items-center justify-center border border-border text-primary font-bold">
              {user?.full_name?.charAt(0).toUpperCase() || <UserIcon size={16} />}
            </div>
            <div className="overflow-hidden">
              <p className="text-sm font-medium truncate">{user?.full_name || "User Account"}</p>
              <p className="text-xs text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:bg-rose-500/10 hover:text-rose-400 transition-all"
          >
            <LogOut size={16} />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Mobile Drawer */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden bg-background/80 backdrop-blur-sm">
          <div className="w-64 bg-surface border-r border-border flex flex-col p-4">
            <div className="flex items-center justify-between pb-6 border-b border-border">
              <Link to="/" className="flex items-center gap-2 font-bold text-lg text-primary">
                <span className="text-2xl">📈</span>
                <span>ShareBot</span>
              </Link>
              <button onClick={() => setSidebarOpen(false)} className="text-slate-400">
                <X size={20} />
              </button>
            </div>
            <nav className="flex-1 py-6 space-y-1">
              {navigation.map((item) => {
                const Icon = item.icon;
                const active = location.pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                      active 
                        ? "bg-primary/10 text-primary" 
                        : "text-slate-400 hover:bg-slate-800/40"
                    }`}
                  >
                    <Icon size={18} />
                    {item.name}
                  </Link>
                );
              })}
            </nav>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 w-full px-4 py-2 mt-auto rounded-lg text-sm font-medium text-slate-400 hover:bg-rose-500/10 hover:text-rose-400"
            >
              <LogOut size={16} />
              Sign Out
            </button>
          </div>
        </div>
      )}

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-16 border-b border-border bg-surface/50 backdrop-blur px-6 flex items-center justify-between z-10 shrink-0">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setSidebarOpen(true)}
              className="md:hidden text-slate-400 hover:text-slate-200"
            >
              <Menu size={20} />
            </button>
            
            <div className="flex items-center gap-2 text-xs font-semibold px-2.5 py-1 rounded-full border bg-slate-900 border-border">
              <span className={`w-2 h-2 rounded-full ${isMarketOpen() ? "bg-emerald-500 animate-pulse" : "bg-slate-500"}`}></span>
              <span className="text-slate-400">
                {activeMarket === "US" ? "US MARKET" : "NSE/BSE"}: {isMarketOpen() ? "LIVE MARKET" : "MARKET CLOSED"}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <select
              value={activeMarket}
              onChange={(e) => {
                localStorage.setItem("sb_active_market", e.target.value);
                window.location.reload();
              }}
              className="bg-slate-900 border border-border rounded-lg px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-primary cursor-pointer font-bold"
            >
              <option value="IN">🇮🇳 India (INR)</option>
              <option value="US">🇺🇸 USA (USD)</option>
            </select>

            <button className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 rounded-lg">
              <Bell size={18} />
            </button>
            <div className="h-8 w-px bg-border"></div>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold text-xs">
                {user?.full_name?.substring(0,2).toUpperCase() || "ME"}
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;
