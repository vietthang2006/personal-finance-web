import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";

export const accountKeys = {
  all: ["accounts"],
  list: (includeArchived) => ["accounts", "list", { includeArchived }],
  detail: (id) => ["accounts", "detail", id],
  history: (id, filters) => ["accounts", "history", id, filters],
};

export function useAccounts({ includeArchived = false } = {}) {
  return useQuery({
    queryKey: accountKeys.list(includeArchived),
    queryFn: () => api.listAccounts({ includeArchived }),
  });
}

export function useAccountHistory(accountId, filters = {}, enabled = true) {
  return useQuery({
    queryKey: accountKeys.history(accountId, filters),
    queryFn: () => api.getAccountHistory(accountId, filters),
    enabled: Boolean(accountId) && enabled,
  });
}

export function useCreateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createAccount,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: accountKeys.all });
    },
  });
}

export function useUpdateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ accountId, data }) => api.updateAccount(accountId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: accountKeys.all });
    },
  });
}

export function useDeleteAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteAccount,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: accountKeys.all });
    },
  });
}

export function useArchiveAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.archiveAccount,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: accountKeys.all });
    },
  });
}

export function useUnarchiveAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.unarchiveAccount,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: accountKeys.all });
    },
  });
}

export function useSnapshotAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.snapshotAccount,
    onSuccess: (_data, accountId) => {
      qc.invalidateQueries({ queryKey: ["accounts", "history", accountId] });
      qc.invalidateQueries({ queryKey: accountKeys.all });
    },
  });
}
