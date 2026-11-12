import { api } from "@/shared/api/client";

export async function listAccounts({ includeArchived = false } = {}) {
  const qs = includeArchived ? "?include_archived=true" : "";
  const data = await api.get(`/accounts${qs}`);

  // Tương thích phòng hờ nếu backend trả về mảng trực tiếp thay vì AccountSummaryResponse
  if (Array.isArray(data)) {
    return {
      default_currency: "VND",
      total_assets_base: "0",
      total_liabilities_base: "0",
      net_worth_base: "0",
      accounts: data,
      warnings: [],
    };
  }
  return data;
}

export const getAccount = (accountId) => api.get(`/accounts/${accountId}`);

export const createAccount = (data) => api.post("/accounts", data);

export const updateAccount = (accountId, data) =>
  api.patch(`/accounts/${accountId}`, data);

export const deleteAccount = (accountId) => api.del(`/accounts/${accountId}`);

export const archiveAccount = (accountId) =>
  api.post(`/accounts/${accountId}/archive`);

export const unarchiveAccount = (accountId) =>
  api.post(`/accounts/${accountId}/unarchive`);

export function getAccountHistory(accountId, { startDate, endDate } = {}) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const qs = params.toString();
  return api.get(`/accounts/${accountId}/history${qs ? `?${qs}` : ""}`);
}

export const snapshotAccount = (accountId) =>
  api.post(`/accounts/${accountId}/snapshot`);
