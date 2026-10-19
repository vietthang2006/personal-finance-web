import { Outlet } from "react-router-dom";
import { ErrorState } from "@/shared/components";
import { useAuth } from "../authContext";

export default function RoleRoute({ role }) {
  const { user } = useAuth();
  if (!user?.roles?.includes(role)) {
    return <ErrorState message="Bạn không có quyền truy cập trang này" />;
  }
  return <Outlet />;
}