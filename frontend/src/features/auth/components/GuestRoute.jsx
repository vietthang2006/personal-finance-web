import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Spinner } from "@/shared/components";
import { useAuth } from "../authContext";

export default function GuestRoute() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") return <Spinner />;
  if (status === "authenticated") {
    return <Navigate to={location.state?.from?.pathname ?? "/dashboard"} replace />;
  }
  return <Outlet />;
}