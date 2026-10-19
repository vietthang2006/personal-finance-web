import { api, REFRESH_FIELD } from "@/shared/api/client";
import { tokenStorage } from "@/shared/lib/tokenStorage";

export const register = (data) =>
  api.post("/auth/register", data, { skipAuth: true });

export const login = (data) =>
  api.post("/auth/login", data, { skipAuth: true });

// Backend chỉ cần refresh token trong body
export const logout = () =>
  api.post(
    "/auth/logout",
    { [REFRESH_FIELD]: tokenStorage.get()?.[REFRESH_FIELD] },
    { skipAuth: true }
  );

export const getMe = () => api.get("/users/me");

export const forgotPassword = (email) =>
  api.post("/auth/forgot-password", { email }, { skipAuth: true });

export const resetPassword = (token, newPassword) =>
  api.post(
    "/auth/reset-password",
    { token, new_password: newPassword },
    { skipAuth: true }
  );