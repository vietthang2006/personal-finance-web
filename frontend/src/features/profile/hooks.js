import { useMutation } from "@tanstack/react-query";
import { useAuth } from "@/features/auth";
import * as api from "./api";

export function useUpdateProfile() {
  const { updateUser } = useAuth();
  return useMutation({
    mutationFn: api.updateProfile,
    onSuccess: (user) => updateUser(user),   // cập nhật tên trên thanh menu ngay
  });
}

export const useChangePassword = () =>
  useMutation({ mutationFn: api.changePassword });