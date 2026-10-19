import { NavLink, Outlet, Link } from "react-router-dom";
import { navItems } from "@/app/navigation";
import { Button } from "@/shared/components";
import { useAuth } from "@/features/auth";

const linkClass = ({ isActive }) =>
  [
    "whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-blue-600 text-white"
      : "text-gray-700 hover:bg-gray-100",
  ].join(" ");

export default function AppLayout() {
  const { user, logout } = useAuth();
  
  return (
    <div className="min-h-screen">
      {/* Thanh menu ngang, dính ở đầu trang khi cuộn */}
      <header className="sticky top-0 z-10 border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
          {/* Logo / tên ứng dụng */}
          <div className="shrink-0 text-lg font-semibold">Chi tiêu cá nhân</div>

          {/* Menu: nằm ngang, cuộn ngang được nếu màn hình hẹp */}
          <nav className="flex flex-1 gap-1 overflow-x-auto">
            {navItems.map((item) => (
              <NavLink key={item.to} to={item.to} className={linkClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex shrink-0 items-center gap-3">
            {/* Link dẫn đến trang Profile */}
            <Link to="/profile" className="hidden text-sm text-gray-700 hover:underline sm:block">
              {user?.full_name || user?.username}
            </Link>
            <Button variant="secondary" onClick={logout}>
              Đăng xuất
            </Button>
          </div>
        </div>
      </header>

      {/* Nội dung trang, căn giữa và giới hạn chiều rộng */}
      <main className="mx-auto max-w-6xl p-4 md:p-6">
        <Outlet />
      </main>
    </div>
  );
}