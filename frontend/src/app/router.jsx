import { createBrowserRouter, Navigate } from "react-router-dom";
import AuthLayout from "@/app/layouts/AuthLayout";
import AppLayout from "@/app/layouts/AppLayout";
import { PlaceholderPage } from "@/shared/components";
import { authRoutes, passwordRoutes, GuestRoute, ProtectedRoute, RoleRoute } from "@/features/auth";
import { profileRoutes } from "@/features/profile";

export const router = createBrowserRouter([
  // 1. Chỉ dành cho người CHƯA đăng nhập (Đăng nhập, Đăng ký)
  {
    element: <GuestRoute />,
    children: [
      { element: <AuthLayout />, children: authRoutes }
    ],
  },

  // 2. Bất kỳ ai cũng truy cập được (Quên mật khẩu, Đặt lại mật khẩu)
  // Không nằm trong GuestRoute để người đang đăng nhập lỡ bấm vào link vẫn xem được
  {
    element: <AuthLayout />,
    children: passwordRoutes,
  },

  // 3. Chỉ dành cho người ĐÃ đăng nhập
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/", element: <Navigate to="/dashboard" replace /> },
          { path: "/dashboard", element: <PlaceholderPage title="Tổng quan" /> },
          { path: "/accounts", element: <PlaceholderPage title="Ví" /> },
          { path: "/transactions", element: <PlaceholderPage title="Giao dịch" /> },
          { path: "/budgets", element: <PlaceholderPage title="Ngân sách" /> },
          { path: "/goals", element: <PlaceholderPage title="Mục tiêu" /> },

          // Các trang hồ sơ, đổi mật khẩu
          ...profileRoutes,

          // Chỉ dành cho role admin
          {
            element: <RoleRoute role="admin" />,
            children: [{ path: "/admin", element: <PlaceholderPage title="Quản trị" /> }],
          },
        ],
      },
    ],
  },

  // 4. Trang 404
  { path: "*", element: <PlaceholderPage title="Không tìm thấy trang" /> },
]);