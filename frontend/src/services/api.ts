import axios from "axios";

const isLocalhost = typeof window !== "undefined" && (
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1"
);

const getAPIUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) {
    if (envUrl.includes("localhost") && !isLocalhost) {
      return "https://sharebot-api.onrender.com/api/v1";
    }
    return envUrl;
  }
  return isLocalhost ? "http://localhost:8000/api/v1" : "https://sharebot-api.onrender.com/api/v1";
};

const api = axios.create({
  baseURL: getAPIUrl(),
  headers: {
    "Content-Type": "application/json",
  },
});

// Request Interceptor: Attach token if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("sb_token");
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Handle token expiry (401) and refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Check if error is 401 and request has not been retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem("sb_refresh_token");

      if (refreshToken) {
        try {
          // Attempt to refresh access token
          const res = await axios.post(`${getAPIUrl()}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          
          const { access_token } = res.data;
          
          // Store new token
          localStorage.setItem("sb_token", access_token);
          
          // Update original request headers and retry
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed - clean credentials and force logout
          localStorage.removeItem("sb_user");
          localStorage.removeItem("sb_token");
          localStorage.removeItem("sb_refresh_token");
          
          // Redirect to login if window is available
          if (typeof window !== "undefined") {
            window.location.href = "/login";
          }
        }
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;
