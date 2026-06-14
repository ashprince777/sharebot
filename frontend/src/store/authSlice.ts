import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
}

interface AuthState {
  user: UserProfile | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
}

const getStoredAuth = (): AuthState => {
  try {
    const userStr = localStorage.getItem("sb_user");
    const token = localStorage.getItem("sb_token");
    const refreshToken = localStorage.getItem("sb_refresh_token");

    if (userStr && token && refreshToken) {
      return {
        user: JSON.parse(userStr),
        token,
        refreshToken,
        isAuthenticated: true,
      };
    }
  } catch (e) {
    console.error("Failed to parse stored auth", e);
  }

  return {
    user: null,
    token: null,
    refreshToken: null,
    isAuthenticated: false,
  };
};

const initialState: AuthState = getStoredAuth();

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setCredentials: (
      state,
      action: PayloadAction<{
        user: UserProfile;
        token: string;
        refreshToken: string;
      }>
    ) => {
      const { user, token, refreshToken } = action.payload;
      state.user = user;
      state.token = token;
      state.refreshToken = refreshToken;
      state.isAuthenticated = true;

      localStorage.setItem("sb_user", JSON.stringify(user));
      localStorage.setItem("sb_token", token);
      localStorage.setItem("sb_refresh_token", refreshToken);
    },
    logout: (state) => {
      state.user = null;
      state.token = null;
      state.refreshToken = null;
      state.isAuthenticated = false;

      localStorage.removeItem("sb_user");
      localStorage.removeItem("sb_token");
      localStorage.removeItem("sb_refresh_token");
    },
  },
});

export const { setCredentials, logout } = authSlice.actions;
export default authSlice.reducer;
