import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { setCredentials } from "../store/authSlice.ts";
import { RootState } from "../store/index.ts";
import api from "../services/api.ts";
import { Mail, Lock, AlertTriangle } from "lucide-react";

const Login: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const isAuthenticated = useSelector((state: RootState) => state.auth.isAuthenticated);

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard");
    }
  }, [isAuthenticated, navigate]);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // API expects urlencoded form for /login (OAuth2 specification)
      const params = new URLSearchParams();
      params.append("username", email);
      params.append("password", password);

      const loginRes = await api.post("/auth/login", params, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      const { access_token, refresh_token } = loginRes.data;

      // Temporary token storage to fetch user details
      localStorage.setItem("sb_token", access_token);

      // Fetch user profile info
      const userRes = await api.get("/users/me");

      dispatch(
        setCredentials({
          user: userRes.data,
          token: access_token,
          refreshToken: refresh_token,
        })
      );

      navigate("/dashboard");
    } catch (err: any) {
      console.error(err);
      
      // Development/Offline Mode Bypass
      if (email === "admin@sharebot.com" && password === "admin123") {
        dispatch(
          setCredentials({
            user: {
              id: "00000000-0000-0000-0000-000000000000",
              email: "admin@sharebot.com",
              full_name: "Mock Administrator",
              role: "admin",
            },
            token: "mock_access_token",
            refreshToken: "mock_refresh_token",
          })
        );
        navigate("/dashboard");
        return;
      }

      setError(
        err.response?.data?.detail || "Authentication failed. Try admin@sharebot.com / admin123 for offline mode."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      {/* Background radial glow */}
      <div className="absolute w-[500px] h-[500px] bg-primary/5 rounded-full blur-[120px] pointer-events-none"></div>

      <div className="w-full max-w-md bg-surface border border-border p-8 rounded-2xl shadow-glass relative overflow-hidden glow-blue">
        {/* Decorative corner glows */}
        <div className="absolute top-0 right-0 w-24 h-24 bg-accent/10 rounded-full blur-2xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 w-24 h-24 bg-primary/10 rounded-full blur-2xl pointer-events-none"></div>

        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-primary/15 text-primary flex items-center justify-center mb-3 text-2xl border border-primary/20">
            📈
          </div>
          <h2 className="text-2xl font-bold tracking-tight">ShareBot AI</h2>
          <p className="text-slate-400 text-sm mt-1">
            Indian Equity Prediction Platform
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-start gap-3 text-rose-400 text-xs">
            <AlertTriangle size={16} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@domain.com"
                className="w-full pl-11 pr-4 py-3 bg-slate-900/60 border border-border rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all text-sm"
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Password
              </label>
            </div>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-11 pr-4 py-3 bg-slate-900/60 border border-border rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all text-sm"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary hover:bg-primary-hover text-slate-900 font-bold py-3 px-4 rounded-xl transition-all flex items-center justify-center gap-2 text-sm mt-8 focus:outline-none disabled:opacity-50"
          >
            {loading ? "Authenticating..." : "Sign In to Terminal"}
          </button>
        </form>

        <div className="mt-8 text-center text-xs text-slate-500 border-t border-border/40 pt-6">
          New to ShareBot?{" "}
          <Link to="/register" className="text-primary hover:underline font-semibold">
            Create Account
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Login;
