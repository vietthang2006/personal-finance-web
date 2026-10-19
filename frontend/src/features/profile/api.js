import { api } from "@/shared/api/client";

export const updateProfile = (data) => api.patch("/users/me", data);
export const changePassword = (data) => api.put("/users/me/password", data);