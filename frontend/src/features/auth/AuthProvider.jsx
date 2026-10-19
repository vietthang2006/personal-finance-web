import { useCallback, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { setUnauthorizedHandler } from "@/shared/api/client";
import { tokenStorage } from "@/shared/lib/tokenStorage";
import { AuthContext } from "./authContext";
import * as authApi from "./api";

export default function AuthProvider({ children }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState(null);
  // "loading": đang hỏi backend xem token còn dùng được không
  const [status, setStatus] = useState(() =>
    tokenStorage.get() ? "loading" : "anonymous"
  );

  // Xóa phiên: token, user, và cache dữ liệu của người cũ
  const reset = useCallback(() => {
    tokenStorage.clear();
    setUser(null);
    setStatus("anonymous");
    queryClient.clear();
  }, [queryClient]);

  // client.js gọi hàm này khi phiên hết hạn hẳn
  useEffect(() => {
    setUnauthorizedHandler(reset);
  }, [reset]);

  // Tải lại trang (F5): có token thì khôi phục user
  useEffect(() => {
    if (!tokenStorage.get()) return;
    let cancelled = false;
    authApi
      .getMe()
      .then((me) => {
        if (cancelled) return;
        setUser(me);
        setStatus("authenticated");
      })
      .catch(() => {
        if (!cancelled) reset();
      });
    return () => {
      cancelled = true;
    };
  }, [reset]);

  // Nhận cặp token -> lấy thông tin user -> bắt đầu phiên
  const startSession = useCallback(async (tokens) => {
    tokenStorage.set(tokens);
    try {
      const me = await authApi.getMe();
      setUser(me);
      setStatus("authenticated");
      return me;
    } catch (err) {
      tokenStorage.clear();
      throw err;
    }
  }, []);

  const login = useCallback(
    async (credentials) => startSession(await authApi.login(credentials)),
    [startSession]
  );

  // Backend trả token khi đăng ký => đăng ký xong là đã đăng nhập
  const register = useCallback(
    async (data) => startSession(await authApi.register(data)),
    [startSession]
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Dù gọi backend lỗi vẫn đăng xuất phía trình duyệt
    } finally {
      reset();
    }
  }, [reset]);

  const value = useMemo(
    () => ({
      user,
      status,
      isAuthenticated: status === "authenticated",
      login,
      logout,
      register,
      updateUser: setUser,
    }),
    [user, status, login, logout, register]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}