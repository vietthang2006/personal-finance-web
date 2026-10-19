import { Outlet } from "react-router-dom";

export default function AuthLayout() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow">
        <h1 className="mb-6 text-center text-xl font-semibold">
          Quản lý chi tiêu cá nhân
        </h1>
        <Outlet />
      </div>
    </div>
  );
}